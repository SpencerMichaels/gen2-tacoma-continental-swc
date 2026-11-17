#include "swc_logic.h"
#include <cassert>
#include <iostream>
#include <limits>
using namespace swc;
void arm(Wheel& w,uint32_t t=0){assert(w.update(3900,3900,t)==Command::Release);assert(w.update(3900,3900,t+100)==Command::Release);}
int main(){
 const uint16_t values[]={0,30,60,61,339,340,485,630,631,929,930,1160,1390,1391,1829,1830,2180,2530,2531,3159,3160,3900,4095,4096,65535};
 unsigned pairs=0;
 for(auto a:values)for(auto b:values){
  Command expected=Command::Release;
  if(b>=3160&&b<=4095){
   if(a<=60)expected=Command::SeekUp;
   else if(a>=340&&a<=630)expected=Command::SeekDown;
   else if(a>=930&&a<=1390)expected=Command::VolumeUp;
   else if(a>=1830&&a<=2530)expected=Command::VolumeDown;
  }
  if(a>=3160&&a<=4095){
   if(b<=60)expected=Command::Source;
   else if(b>=340&&b<=630)expected=Command::Mute;
   else if(b>=930&&b<=1390)expected=Command::Phone;
  }
  assert(decode(a,b)==expected);pairs++;
 }
 for(unsigned n=0;n<=65535;n++){
  bool legal=n<=60||(n>=340&&n<=630)||(n>=930&&n<=1390)||(n>=1830&&n<=2530)||(n>=3160&&n<=4095);
  assert((classify(n)!=Band::Invalid)==legal);
 }
 const uint16_t inputs[][2]={{3900,3900},{2180,3900},{1160,3900},{3900,30},{30,3900},{485,3900},{3900,1160},{3900,485}};
 for(unsigned i=1;i<8;i++){
  Wheel w;auto c=static_cast<Command>(i);auto a=inputs[i][0],b=inputs[i][1];
  assert(w.update(a,b,0)==Command::Release);assert(w.update(a,b,200)==Command::Release);
  arm(w,300);assert(w.update(a,b,401)==Command::Release);assert(w.update(a,b,420)==Command::Release);
  assert(w.update(a,b,421)==c);assert(w.update(a,b,10420)==c);assert(w.update(a,b,10421)==Command::Release);
  assert(w.update(a,b,11000)==Command::Release);arm(w,12000);
  assert(w.update(a,b,12101)==Command::Release);assert(w.update(a,b,12121)==c);
  assert(w.update(800,800,12123)==Command::Release);
  assert(w.update(a,b,12500)==Command::Release);
 }
 Wheel bounce;arm(bounce);bounce.update(30,3900,102);bounce.update(3900,3900,110);
 assert(bounce.update(30,3900,112)==Command::Release);assert(bounce.update(30,3900,131)==Command::Release);assert(bounce.update(30,3900,132)==Command::SeekUp);
 assert(bounce.update(485,3900,134)==Command::Release);assert(bounce.update(485,3900,1000)==Command::Release);
 Wheel wrap;arm(wrap,UINT32_MAX-150);assert(wrap.update(30,3900,UINT32_MAX-10)==Command::Release);assert(wrap.update(30,3900,10)==Command::SeekUp);
 Pulse p;assert(p.start(Command::Phone,UINT32_MAX-100));assert(!p.start(Command::Mute,0));assert(p.update(198,true)==Command::Phone);assert(p.update(199,true)==Command::Release);
 assert(p.start(Command::Mute,500));assert(p.update(501,false)==Command::Release);
 for(unsigned i=0;i<8;i++){Command c;assert(parse(names[i],c));assert(unsigned(c)==i);assert((mask(c)&~outputMask)==0);}
 Command c;assert(!parse("invalid",c));
 // RC settling gaps must not swallow an otherwise valid press.
 for(auto gap:{118,795,1408,1448,2651}){
  Wheel w;arm(w);assert(w.update(gap,3900,152)==Command::Release);
  assert(w.update(30,3900,154)==Command::Release);
  assert(w.update(30,3900,174)==Command::SeekUp);
  // Once active, the very same gap releases and requires idle rearming.
  assert(w.update(gap,3900,176)==Command::Release);
  assert(w.update(30,3900,300)==Command::Release);
 }
 Wheel persistent;arm(persistent);
 for(unsigned t=102;t<=108;t+=2)assert(persistent.update(800,3900,t)==Command::Release);
 assert(persistent.update(30,3900,110)==Command::Release);
 assert(persistent.update(30,3900,300)==Command::Release);
 Wheel simultaneous;arm(simultaneous);simultaneous.update(30,30,102);
 assert(simultaneous.update(30,3900,200)==Command::Release);
 Wheel gapWrap;arm(gapWrap,UINT32_MAX-200);
 gapWrap.update(800,3900,UINT32_MAX-3);gapWrap.update(800,3900,2);
 assert(gapWrap.update(30,3900,4)==Command::Release);
 assert(gapWrap.update(30,3900,30)==Command::Release);
 std::cout<<"PASS: "<<pairs<<" boundary pairs, 65536 classifications, all seven timed commands, debounce, lockout, disconnect, rollover\n";
}
