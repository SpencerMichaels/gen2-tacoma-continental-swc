#include <Arduino.h>
#include <hardware/gpio.h>
#include <hardware/structs/sio.h>
#include <hardware/sync.h>
#include <hardware/watchdog.h>
#include <hardware/timer.h>
#include <hardware/structs/vreg_and_chip_reset.h>
#include "swc_logic.h"

// RP2040 GPIO numbers, NOT XIAO D-number labels.
constexpr uint8_t sw1Pin=26,sw2Pin=27;
bool bench=SWC_BENCH_DEFAULT;
swc::Wheel wheel;swc::Pulse pulse;
swc::Command applied=swc::Command::Release;
uint16_t adc1=4095,adc2=4095;
uint32_t sampled=0;
const char* resetCause="?";uint32_t boots=0;
char line[40];uint8_t used=0;bool overflow=false;

void output(swc::Command c) {
 if(c==applied)return;
 // Break before make; assert paired branches in ONE register write.
 uint32_t irq=save_and_disable_interrupts();
 sio_hw->gpio_clr=swc::outputMask;
 busy_wait_us_32(20); // Pure timer poll: sleep_us()/delayMicroseconds() hang with IRQs off.
 sio_hw->gpio_set=swc::mask(c);
 restore_interrupts(irq);
 applied=c;
}
// Replies are best-effort; an absent/slow USB host must not hold an output on.
void reply(const char* s) {
 size_t n=strlen(s);
 if(Serial&&Serial.availableForWrite()>=int(n+2)){Serial.write(s,n);Serial.write("\r\n");}
}
void resetOutput(){pulse.stop();wheel.reset();output(swc::Command::Release);}
void command(const char* s) {
 if(!strcmp(s,"release")||!strcmp(s,"stop")){resetOutput();reply("released");return;}
 if(!strcmp(s,"bench")){resetOutput();bench=true;reply("bench mode: one 300 ms pulse per command");return;}
 if(!strcmp(s,"vehicle")){resetOutput();bench=false;reply("vehicle mode: waiting for 100 ms idle");return;}
 if(!strcmp(s,"status")){
  char msg[160];snprintf(msg,sizeof(msg),"mode=%s SW1=%u SW2=%u output=%s up=%lums boots=%lu reset=%s",bench?"bench":"vehicle",adc1,adc2,swc::name(applied),(unsigned long)millis(),(unsigned long)boots,resetCause);reply(msg);return;
 }
 if(!strcmp(s,"help")){
  reply("bench vehicle status stop");
  reply("volume_down volume_up source seek_up seek_down phone mute");return;
 }
 swc::Command c;
 if(swc::parse(s,c)&&bench){reply(pulse.start(c,millis())?"pulse accepted":"busy: wait for release");return;}
 resetOutput();reply("unknown command or not in bench mode; released");
}
void setup() {
 // Bring-up diagnostics: why did we last reset, and how many boots since power-on.
 uint32_t cr=vreg_and_chip_reset_hw->chip_reset;
 if(watchdog_enable_caused_reboot())resetCause="watchdog";
 else if(watchdog_caused_reboot())resetCause="watchdog-force";
 else if(cr&VREG_AND_CHIP_RESET_CHIP_RESET_HAD_POR_BITS)resetCause="power-on/brownout";
 else if(cr&VREG_AND_CHIP_RESET_CHIP_RESET_HAD_RUN_BITS)resetCause="reset-button";
 else if(cr&VREG_AND_CHIP_RESET_CHIP_RESET_HAD_PSM_RESTART_BITS)resetCause="debug";
 if(watchdog_hw->scratch[1]!=0x5743u||(cr&VREG_AND_CHIP_RESET_CHIP_RESET_HAD_POR_BITS)){watchdog_hw->scratch[1]=0x5743u;watchdog_hw->scratch[0]=0;}
 boots=++watchdog_hw->scratch[0];
 // Load low output latches before enabling drivers; external pulldowns cover reset.
 gpio_init_mask(swc::outputMask);
 sio_hw->gpio_clr=swc::outputMask;
 gpio_set_dir_out_masked(swc::outputMask);
 // XIAO RGB indicator channels are active-low; power down the separate NeoPixel.
 digitalWrite(PIN_LED_R,HIGH);pinMode(PIN_LED_R,OUTPUT);
 digitalWrite(PIN_LED_G,HIGH);pinMode(PIN_LED_G,OUTPUT);
 digitalWrite(PIN_LED_B,HIGH);pinMode(PIN_LED_B,OUTPUT);
 digitalWrite(NEOPIXEL_POWER,LOW);pinMode(NEOPIXEL_POWER,OUTPUT);
 pinMode(sw1Pin,INPUT);pinMode(sw2Pin,INPUT);
 analogReadResolution(12);
 Serial.begin(115200); // Never wait for a USB connection.
 watchdog_enable(1000,true);
}
void loop() {
 uint32_t now=millis();
 if(uint32_t(now-sampled)>=2){
  sampled=now;
  // Discard first conversion after switching ADC channels.
  analogRead(sw1Pin);adc1=analogRead(sw1Pin);
  analogRead(sw2Pin);adc2=analogRead(sw2Pin);
  if(!bench)output(wheel.update(adc1,adc2,now));
 }
 if(bench)output(pulse.update(now,bool(Serial)));
 // Bound serial work per iteration so input flooding cannot starve release logic.
 for(unsigned i=0;i<32&&Serial.available();i++) {
  int ch=Serial.read();
  if(ch=='\n'||ch=='\r'){
   if(overflow){resetOutput();reply("line too long; released");}
   else if(used){line[used]=0;command(line);}
   used=0;overflow=false;
  }else if(!overflow){
   if(used<sizeof(line)-1)line[used++]=char(ch);
   else {overflow=true;resetOutput();}
  }
 }
 if(!Serial){used=0;overflow=false;}
 watchdog_update();
 delay(1); // Arduino-Pico sleep/yield; keep the second core unused.
}
