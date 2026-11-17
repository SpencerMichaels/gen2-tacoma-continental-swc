#pragma once
#include <stdint.h>
#include <string.h>
namespace swc {
enum class Command : uint8_t { Release, VolumeDown, VolumeUp, Source, SeekUp, SeekDown, Phone, Mute };
constexpr uint32_t masks[] = {0,1,6,2,20,4,16,8};
constexpr const char* names[] = {"release","volume_down","volume_up","source","seek_up","seek_down","phone","mute"};
constexpr uint32_t outputMask = 0x1f;
constexpr uint32_t debounceMs=20, idleMs=100, maxHoldMs=10000, pulseMs=300;
constexpr uint32_t inputSettleMs=6;
inline uint32_t mask(Command c) { return masks[static_cast<unsigned>(c)]; }
inline const char* name(Command c) { return names[static_cast<unsigned>(c)]; }
inline bool parse(const char* s, Command& c) {
 for(unsigned i=0;i<8;i++) if(!strcmp(s,names[i])) {c=static_cast<Command>(i);return true;}
 return false;
}
enum class Band { Zero, R330, R1k, R3k1, Idle, Invalid };
// 12-bit ADC windows from the current BAS70/2.2k input SPICE model.
// Gaps deliberately decode as invalid. Bench verification is still required.
inline Band classify(uint16_t n) {
 if(n<=60)return Band::Zero;
 if(n>=340&&n<=630)return Band::R330;
 if(n>=930&&n<=1390)return Band::R1k;
 if(n>=1830&&n<=2530)return Band::R3k1;
 if(n>=3160&&n<=4095)return Band::Idle;
 return Band::Invalid;
}
inline Command decode(uint16_t a,uint16_t b) {
 const auto x=classify(a),y=classify(b);
 if(y==Band::Idle) {
  switch(x) {case Band::Zero:return Command::SeekUp;case Band::R330:return Command::SeekDown;
   case Band::R1k:return Command::VolumeUp;case Band::R3k1:return Command::VolumeDown;default:break;}
 }
 if(x==Band::Idle) {
  switch(y) {case Band::Zero:return Command::Source;case Band::R330:return Command::Mute;
   case Band::R1k:return Command::Phone;default:break;}
 }
 return Command::Release;
}
class Wheel {
 bool armed=false, idleTracking=false, settling=false;
 uint32_t idleSince=0,candidateSince=0,pressedSince=0,settlingSince=0;
 Command candidate=Command::Release,active=Command::Release;
 public:
 void reset(){armed=false;idleTracking=false;settling=false;candidate=active=Command::Release;}
 Command update(uint16_t a,uint16_t b,uint32_t now) {
  bool idle=classify(a)==Band::Idle&&classify(b)==Band::Idle;
  Command desired=decode(a,b);
  if(idle) {
   settling=false;
   active=candidate=Command::Release;
   if(!idleTracking){idleTracking=true;idleSince=now;}
   if(uint32_t(now-idleSince)>=idleMs)armed=true;
   return active;
  }
  idleTracking=false;
  if(desired==Command::Release){
   // An RC-filtered press crosses gaps between valid ADC bands. Allow a
   // bounded settling interval only before activation and with one line idle.
   // Active-command faults and simultaneous inputs still release and lock out.
   bool oneIdle=(classify(a)==Band::Idle)!=(classify(b)==Band::Idle);
   if(armed&&active==Command::Release&&oneIdle){
    candidate=Command::Release;
    if(!settling){settling=true;settlingSince=now;}
    if(uint32_t(now-settlingSince)<inputSettleMs)return Command::Release;
   }
   reset();return active;
  }
  settling=false;
  if(!armed)return Command::Release;
  if(active!=Command::Release) {
   if(desired!=active||uint32_t(now-pressedSince)>=maxHoldMs)reset();
   return active;
  }
  if(candidate!=desired){candidate=desired;candidateSince=now;}
  if(uint32_t(now-candidateSince)>=debounceMs){active=desired;pressedSince=now;}
  return active;
 }
};
class Pulse {
 Command active=Command::Release;uint32_t started=0;
 public:
 bool start(Command c,uint32_t now){if(active!=Command::Release)return false;active=c;started=now;return true;}
 void stop(){active=Command::Release;}
 Command update(uint32_t now,bool connected){if(!connected||uint32_t(now-started)>=pulseMs)stop();return active;}
};
}
