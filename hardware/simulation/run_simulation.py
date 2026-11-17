#!/usr/bin/env python3
"""Reproducible ngspice behavioral verification of the exported SWC netlist.
Not transistor-accurate device qualification or an emulator of deployed MCU firmware.
"""
from pathlib import Path
import itertools, json, math, hashlib, bisect, xml.etree.ElementTree as ET
from spice_engine import Spice

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'checks/simulation';OUT.mkdir(exist_ok=True)
xml=ET.parse(BASE/'checks/netlist.xml').getroot()
intent=json.loads((BASE/'design_intent.json').read_text())
contract=json.loads((BASE/'output_commands.json').read_text())
N={(nd.attrib['ref'],nd.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for nd in net.findall('node')}
def net(r,p):return N[r,str(p)]
net_ids={v:('0' if v=='GND' else f'n{i}') for i,v in enumerate(sorted(set(N.values())))}
def node(r,p):return net_ids[net(r,p)]
def val(r):
    s=intent[r]['value'].split()[0].lower().replace('ohm','')
    if s.endswith('uf'):return float(s[:-2])*1e-6
    if s.endswith('nf'):return float(s[:-2])*1e-9
    if s.endswith('k'):return float(s[:-1])*1e3
    if s.endswith('r'):return float(s[:-1])
    return float(s)
branches=[(1,0),(3,1),(5,2),(6,4),(7,3)]
windows={'volume_down':[0,100],'volume_up':[100,160],'source':[160,220],
         'seek_up':[220,320],'seek_down':[320,470],'phone':[720,1300],'mute':[1300,3000]}
command_masks={'release':0,'volume_down':1,'volume_up':6,'source':2,'seek_up':20,'seek_down':4,'phone':16,'mute':8}
for c in contract['commands']:assert c['port_set_masks']=={'SIO':command_masks[c['command']]}
# Independent mapping of physical wheel state to desired radio action.
left={'zero':'seek_up','330':'seek_down','1k':'volume_up','3k1':'volume_down'}
right={'zero':'source','330':'mute','1k':'phone'}
bands=[('zero',0,60),('330',340,630),('1k',930,1390),('3k1',1830,2530),('idle',3160,4095)]
def classify(c):
    return next((k for k,lo,hi in bands if lo<=c<=hi),'invalid')
def decode(a,b):
    a,b=classify(a),classify(b)
    if b=='idle' and a in left:return left[a]
    if a=='idle' and b in right:return right[b]
    return 'release'
def expected(a,b):
    if b in ['idle','open'] and a in left:return left[a]
    if a in ['idle','open'] and b in right:return right[b]
    return 'release'

# Physical R/C topology comes from KiCad, including protection diode polarity.
def deck(vdd=3.3,pullscale=1.,rscale=1.,ron=.048,vradio=3.3,rpull=2200,cradio=1e-9,mask=0,transient=False,fault=None,mcu_hiz=False):
    lines=['SWC behavioral test from exported KiCad netlist',
      '* Regulators and MCU are STUBS; no automotive surge/thermal certification.',
      '* Schottky and MOS switch models below are engineering approximations, NOT vendor SPICE models.',
      f'Vlogic {node("A1",12)} 0 DC {vdd}',
      'Vacc acc_stub 0 DC 12',
      f'Vradio radio_internal 0 DC {vradio}',
      f'Rradio radio_internal {node("J1",9)} {rpull}',
      f'Cradio {node("J1",9)} {node("J1",10)} {cradio}',
      f'Rnt1 {node("NT1",1)} {node("NT1",2)} 1u',
      f'Rwheel1 {node("J1",4)} 0 100k',f'Rwheel2 {node("J1",8)} 0 100k']
    for r in ['R4','R5','R6','R7','R8']:
        scale=pullscale if r in ['R5','R6'] else 1
        lines.append(f'{r} {node(r,1)} {node(r,2)} {val(r)*scale}')
    for r in ['C5','C6','C7','C8','C10','C11']:
        lines.append(f'{r} {node(r,1)} {node(r,2)} {val(r)}')
    for r in ['D5','D6']:lines.append(f'{r} {node(r,1)} {node(r,3)} DBAS')
    for r in ['D7','D8']:
        lines.extend([f'{r}lo {node(r,1)} {node(r,3)} DBAS',f'{r}hi {node(r,3)} {node(r,2)} DBAS'])
    for i,bit in branches:
        q=f'Q{i}';r=f'R{10+i}';rg=f'R{20+i}';pd=f'R{30+i}'
        gpio=node(rg,1);g=node(q,1);d=node(q,3);src=node(q,2)
        if transient:
            # Step the requested mask on at2ms then off at4ms; actively hold low thereafter.
            high=vdd if mask&(1<<bit) else 0
            drive=f'PWL(0 0 1.999m 0 2m {high} 3.999m {high} 4m 0 8m 0)'
        else:drive=f'DC {vdd if mask&(1<<bit) else 0}'
        lines.extend([f'Vmcu{i} drive{i} 0 {drive}',f'Rmcu{i} drive{i} {gpio} {1e12 if mcu_hiz else 40}',
           f'{rg} {gpio} {g} {val(rg)}',f'{pd} {g} {src} {val(pd)}',
           f'{r} {node(r,1)} {node(r,2)} {val(r)*rscale}',
           f'Bq{i} {d} {src} I=V({d},{src})*(1e-12+(1/{ron}-1e-12)*0.5*(1+tanh((V({g},{src})-1.05)/.05)))',
           f'Dbody{i} {src} {d} DBODY',f'Cgs{i} {g} {src} 580p',
           f'Cgd{i} {g} {d} 50p',f'Cds{i} {d} {src} 25p'])
    if fault=='acc_bridge':lines.append(f'Rfault acc_stub {node("J1",9)} .1')
    if fault=='drain_source_short':lines.append(f'Rfault {node("Q1",3)} {node("Q1",2)} .001')
    lines.extend([
      '.model DBAS D(Is=1n N=1.05 Rs=10 Cjo=2p Eg=.69 Bv=70 Ibv=10u)',
      '.model DBODY D(Is=1p N=1.3 Rs=.1 Cjo=1p)',
      '.options method=gear reltol=1e-6 abstol=1e-12 vntol=1e-8', '.end'])
    return '\n'.join(lines)+'\n'

def scalar(s,r,p):return s.value(node(r,p))
def set_mask(s,mask,vdd=3.3):
    for i,bit in branches:s.command(f'alter Vmcu{i} {vdd if mask&(1<<bit) else 0}')

def states():
    ranges={'zero':[.001,1.25,2.5],'330':[313,329,345],'1k':[950,1000,1050],
            '3k1':[2955,3110,3265],'idle':[95000,100000,105000],
            'open':[1e12],'invalid100':[100],'invalid600':[600],'invalid1800':[1800]}
    return [(k,r) for k,rs in ranges.items() for r in rs]

s=Spice();s.command('version');version='\n'.join(s.messages[-12:])
(OUT/'nominal.cir').write_text(deck())
(OUT/'node_map.json').write_text(json.dumps(net_ids,indent=2)+'\n')
failures=[];input_runs=0;decode_runs=0;nominal=[]
for vdd,scale in itertools.product([3.201,3.3,3.399],[.99,1.,1.01]):
    s.load(deck(vdd=vdd,pullscale=scale))
    for (a,ra),(b,rb) in itertools.product(states(),repeat=2):
        s.command(f'alter Rwheel1 {ra}');s.command(f'alter Rwheel2 {rb}');s.op();input_runs+=1
        counts=[4095*scalar(s,'A1',p)/vdd for p in [1,2]]
        want=expected(a,b)
        # Include independent +/-32 ADC count errors on both channels.
        for ea,eb in itertools.product([-32,0,32],repeat=2):
            got=decode(*[max(0,min(4095,round(v+e))) for v,e in zip(counts,[ea,eb])]);decode_runs+=1
            if got!=want:failures.append({'kind':'decode','states':[a,b],'resistance':[ra,rb],'vdd':vdd,'pull_scale':scale,'adc':counts,'error':[ea,eb],'expected':want,'actual':got})
        # End-to-end: behavioral MCU reads simulated ADC, then drives physical gate network.
        cmd=decode(*map(round,counts));set_mask(s,command_masks[cmd],vdd);s.op()
        vo=scalar(s,'J1',9)-scalar(s,'J1',10);ir=(3.3-scalar(s,'J1',9))/2200
        req=vo/ir if ir>1e-10 else None
        if cmd=='release':
            if vo<3.299:failures.append({'kind':'release','vout':vo})
        elif not windows[cmd][0]<=req<=windows[cmd][1]:failures.append({'kind':'output','command':cmd,'ohms':req})
        set_mask(s,0,vdd)
        if vdd==3.3 and scale==1. and b=='idle' and rb==100000 and ra in [1.25,329,1000,3110]:
            nominal.append({'line':'SW1','button':a,'command':cmd,'adc':round(counts[0],2),'ohms':req})
        if vdd==3.3 and scale==1. and a=='idle' and ra==100000 and rb in [1.25,329,1000]:
            nominal.append({'line':'SW2','button':b,'command':cmd,'adc':round(counts[1],2),'ohms':req})

# Exhaustive digital mask/DC domain check, including invalid masks and radio off.
mask_runs=0;output_limits={c:[math.inf,0] for c in windows};max_radio_off=0
for vr,rp,rs,ron in itertools.product([0,3.3,5],[470,1000,2200,10000],[.99,1.01],[.01,.048,.1]):
    s.load(deck(vradio=vr,rpull=rp,rscale=rs,ron=ron))
    for mask in range(32):
        set_mask(s,mask);s.op();mask_runs+=1
        vo=scalar(s,'J1',9)-scalar(s,'J1',10)
        if not -.000001<=vo<=vr+.000001:failures.append({'kind':'rail_bound','v_radio':vr,'mask':mask,'vout':vo})
        if vr==0:max_radio_off=max(max_radio_off,abs(vo))
        ir=(vr-scalar(s,'J1',9))/rp
        cmd=next((c for c,m in command_masks.items() if m==mask),'invalid_mask')
        if vr>0 and cmd in windows:
            req=vo/ir;lo,hi=output_limits[cmd];output_limits[cmd]=[min(lo,req),max(hi,req)]
            if not windows[cmd][0]<=req<=windows[cmd][1]:failures.append({'kind':'resistance_corner','command':cmd,'ohms':req})

# Transient turn-on/off: assumed radio input impedance/capacitance sweep.
transients=[]
for cmd,rp,cap in itertools.product(windows,[470,1000,10000],[100e-12,1e-9,10e-9]):
    cir=deck(rpull=rp,cradio=cap,mask=command_masks[cmd],transient=True)
    s.load(cir);s.command('tran 100n 8m');t=s.vector('time');v=s.vector(node('J1',9))
    # Check only settled windows against DC command windows; peak values are recorded, not assumed safe.
    vals=[x for tt,x in zip(t,v) if .003<=tt<=.0039]
    reqs=[x/((3.3-x)/rp) for x in vals]
    good=min(reqs)>=windows[cmd][0] and max(reqs)<=windows[cmd][1]
    if not good:failures.append({'kind':'transient_settled','command':cmd,'range':[min(reqs),max(reqs)]})
    transients.append({'command':cmd,'radio_pullup_ohms':rp,'radio_cap_f':cap,'min_v':min(v),'max_v':max(v),'settled_ohms':[min(reqs),max(reqs)],'final_v':v[-1]})
    if cmd=='volume_up' and rp==10000 and cap==1e-9:
        (OUT/'transition.cir').write_text(cir)
        # Decimate only the displayed waveform, retaining all samples near switching edges.
        rows=['time_s,swrc_plus_v']+[f'{tt:.9g},{vv:.9g}' for i,(tt,vv) in enumerate(zip(t,v)) if i%100==0 or abs(tt-.002)<.00002 or abs(tt-.004)<.00002]
        (OUT/'transition.csv').write_text('\n'.join(rows)+'\n')

# RC input transients -> sampled20ms debounce stub -> gate-driven output transient.
# This exercises the proposed behavior, not unimplemented firmware.
debounce_cases=[]
for line,rwheel,cmd in [(1,.001,'seek_up'),(1,329,'seek_down'),(1,1000,'volume_up'),(1,3110,'volume_down'),(2,.001,'source'),(2,329,'mute'),(2,1000,'phone')]:
    raw=node('J1',4 if line==1 else 8)
    cir=deck().replace(f'Rwheel{line} {raw} 0 100k',f'Bwheel{line} {raw} 0 I=V({raw})/(V(press)>.5 ? {rwheel} : 100000)')
    cir=cir.replace('.end','Vpress press 0 PWL(0 0 1m 0 1.001m 1 2m 1 2.001m 0 3m 0 3.001m 1 60m 1 60.001m 0 100m 0)\n.end')
    s.load(cir);s.command('tran 50u 100m 0 50u')
    t=s.vector('time');a0=s.vector(node('A1',1));a1=s.vector(node('A1',2))
    candidate='release';since=0;out='release';events=[(0,'release')];samples=[]
    for tick in range(101):
        tm=tick*.001;k=min(bisect.bisect_left(t,tm),len(t)-1)
        wanted=decode(round(4095*a0[k]/3.3),round(4095*a1[k]/3.3))
        if wanted=='release':candidate='release';since=tm;new='release'
        else:
            if wanted!=candidate:candidate=wanted;since=tm
            new=wanted if tm-since>=.020-1e-9 else 'release'
        if new!=out:events.append((tm,new));out=new
        samples.append((tm,out))
    active=[tm for tm,c in events if c==cmd];releases=[tm for tm,c in events if c=='release' and tm>.01]
    if not active or not .023<=active[0]<=.028 or not releases or not .060<=releases[0]<=.063 or any(c not in ['release',cmd] for _,c in events):
        failures.append({'kind':'debounce','command':cmd,'events':events})
    # Feed resulting GPIO events back into the output circuit as ideal MCU voltage sources.
    output=deck()
    for i,bit in branches:
        pwl=[(0,0)];last=0
        for tm,c in events[1:]:
            high=3.3 if command_masks[c]&(1<<bit) else 0
            pwl.extend([(tm,last),(tm+1e-6,high)]);last=high
        pwl.append((.100,last))
        source='PWL('+' '.join(f'{tt:.9g} {vv}' for tt,vv in pwl)+')'
        output=output.replace(f'Vmcu{i} drive{i} 0 DC 0',f'Vmcu{i} drive{i} 0 {source}')
    s.load(output);s.command('tran 10u 100m 0 10u');tv=s.vector('time');ov=s.vector(node('J1',9))
    assert tv and tv[-1]>=.099, ('incomplete transient',cmd,tv[-1] if tv else None)
    plateau=[v/((3.3-v)/2200) for tt,v in zip(tv,ov) if .035<=tt<=.055]
    if not windows[cmd][0]<=min(plateau)<=max(plateau)<=windows[cmd][1]:failures.append({'kind':'debounced_output','command':cmd})
    debounce_cases.append({'line':line,'wheel_ohms':rwheel,'command':cmd,'events_s':events,'settled_ohms':[min(plateau),max(plateau)]})
    if cmd=='volume_up':
        (OUT/'input_bounce.cir').write_text(cir);(OUT/'debounced_output.cir').write_text(output)

# Reset/high-impedance MCU, including carrier off while the radio remains powered.
reset_cases=[]
for vdd,vr in itertools.product([0,3.3],[0,3.3,5]):
    s.load(deck(vdd=vdd,vradio=vr,mcu_hiz=True));s.op()
    vo=scalar(s,'J1',9)-scalar(s,'J1',10)
    gates=[scalar(s,f'Q{i}',1)-scalar(s,f'Q{i}',2) for i,_ in branches]
    if abs(vo-vr)>.001 or max(map(abs,gates))>.01:failures.append({'kind':'reset','vout':vo,'gates':gates})
    reset_cases.append({'logic_supply_v':vdd,'radio_supply_v':vr,'output_v':vo,'gate_voltages_v':gates})

faults=[]
for fault in ['drain_source_short','acc_bridge']:
    cir=deck(fault=fault);s.load(cir);s.op()
    faults.append({'fault':fault,'swrc_plus_v':scalar(s,'J1',9),'radio_pullup_current_a':(3.3-scalar(s,'J1',9))/2200})
    (OUT/(fault+'.cir')).write_text(cir)

# Exact radio-output pin inventory, checked independently of the authoring intent.
plus_pins=sorted([list(k) for k,v in N.items() if v=='SWRC_PLUS'])
want=sorted([['J1','9'],['TP3','1'],['C11','1']]+[[f'R{10+i}','2'] for i,_ in branches])
assert plus_pins==want,(plus_pins,want)
for i,_ in branches:
    assert net(f'Q{i}',2)=='SWRC_GND'
    assert set(k for k,v in N.items() if v==net(f'Q{i}',3))=={(f'Q{i}','3'),(f'R{10+i}','1')}
# A silicon gate is not a certified galvanic isolation barrier; graph inventory proves topology only.
report={'status':'PASS_WITH_MODEL_LIMITATIONS' if not failures else 'FAIL',
 'engine':version,'netlist_sha256':hashlib.sha256((BASE/'checks/netlist.xml').read_bytes()).hexdigest(),
 'input_spice_operating_points':input_runs,'adc_decode_checks':decode_runs,
 'end_to_end_output_operating_points':input_runs,'all_mask_dc_operating_points':mask_runs,
 'transient_cases':len(transients),'explicit_fault_cases':len(faults),'failures':failures,'reset_cases':reset_cases,'debounce_cases':debounce_cases,
 'safety_claim_12v_impossible':'REFUTED_BY_ACC_TO_SWRC_BRIDGE_COUNTEREXAMPLE',
 'nominal_command_examples':nominal,'output_ohm_ranges':output_limits,
 'radio_off_max_dc_voltage_v':max_radio_off,'transient_results':transients,'fault_results':faults,
 'swrc_plus_pin_inventory':plus_pins,
 'limitations':['MCU is a Python behavioral decoder, not real firmware or instruction-level emulator.',
 'Regulators/ACC protection omitted from analog model;3V3 supply is an ideal source. No load-dump/thermal/failure prediction.',
 'Diode and switched MOSFET models are approximations, not manufacturer fitted SPICE models.',
 'Cgs/Cgd/Cds fixed from one datasheet operating point; actual low-voltage capacitance and gate dynamics vary.',
 'Radio3.3V/5V pull-up and100pF–10nF input capacitance are assumed fixtures; actual radio impedance/absolute limits unknown.',
 'DC resistor ranges and transient timing need bench verification; simulations cannot prove arbitrary-fault immunity.']}
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'ngspice.log').write_text('\n'.join(s.messages[-100:])+'\n')
print(json.dumps({k:report[k] for k in ['status','input_spice_operating_points','adc_decode_checks','all_mask_dc_operating_points','transient_cases','fault_results','output_ohm_ranges']},indent=2))
if failures:print('FAILURES',failures[:8]);raise SystemExit(1)
