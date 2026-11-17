"""Check KiCad's exported connectivity against intended pin assignments and requirements.

Run after kicad-cli sch export netlist --format kicadxml and sch erc.
This does not simulate parts, certify fault survival, or replace bench measurements.
"""
from pathlib import Path
import json, math, xml.etree.ElementTree as ET
import re

P=Path(__file__).resolve().parent
intent=json.loads((P/'design_intent.json').read_text())
xml=ET.parse(P/'checks/netlist.xml').getroot()
nets={}
for net in xml.find('nets'):
    for pin in net.findall('node'): nets[(pin.get('ref'),pin.get('pin'))]=net.get('name')
def n(ref,pin):return nets[(ref,str(pin))]
errors=[]
expected_groups={}; actual_groups={}
for (ref,pin),net in nets.items(): actual_groups.setdefault(net,set()).add((ref,pin))
for ref,c in intent.items():
    if not ref.startswith('#'):
        for pin,p in c['pins'].items():
            if p['net']:expected_groups.setdefault(p['net'],set()).add((ref,pin))
for ref,c in intent.items():
    if ref.startswith('#'):continue
    for pin,p in c['pins'].items():
        got=nets.get((ref,pin)); want=p['net']
        if want:
            internal=want.startswith(('OUT_D','OUT_G','PULL'))
            if not internal and got!=want:errors.append([ref,pin,want,got])
            if actual_groups.get(got)!=expected_groups[want]:errors.append([ref,pin,'wrong connectivity group',got])
        if want is None and got and not got.startswith('unconnected-'):errors.append([ref,pin,'NC',got])
assert not errors,errors

# Independent requirements: five physical branches and verified XIAO GPIO assignments.
for i,module_pin,resistor_value,branch in [
    (1,7,'47R','BR_47R'),(3,8,'191R','BR_191R'),(5,9,'390R','BR_390R'),
    (6,10,'1.00k','BR_1K'),(7,11,'2.00k','BR_2K')]:
    assert intent[f'R{10+i}']['value']==resistor_value
    assert n('A1',module_pin)==n(f'R{20+i}',1)==branch
    assert n(f'R{20+i}',2)==n(f'Q{i}',1)==n(f'R{30+i}',1)
    assert n(f'Q{i}',2)==n(f'R{30+i}',2)=='SWRC_GND'
    assert n(f'R{10+i}',1)==n(f'Q{i}',3)
    assert n(f'R{10+i}',2)=='SWRC_PLUS'
assert not any(r in intent for r in ['Q2','Q4','R12','R14','R22','R24','R32','R34'])
assert intent['A1']['mpn']=='102010428'
for r in ['C1','C2','C3','C4','C5','C6','C7','C8','C10','C11']:
    assert r in intent and intent[r]['fit'] # User elected to retain all capacitors.
assert n('C11',1)=='SWRC_PLUS' and n('C11',2)=='SWRC_GND'
assert intent['C11']['value']=='10nF 50V X7R'
assert n('J1','9')=='SWRC_PLUS' and n('J1','10')=='SWRC_GND'
assert n('J1','4')=='SW1_RAW' and n('J1','8')=='SW2_RAW'
assert n('J1','12')=='ACC' and n('J1','6')=='GND'
for p in ['7','11','1','2','3','5','MP1','MP2']:assert intent['J1']['pins'][p]['net'] is None

# SWC-only scope: no remaining Kenwood circuitry or reserved UART connections.
for p in ['3','4','5','6']:
    assert intent['A1']['pins'][p]['net'] is None
assert all(c['sheet'] in ('01_interface','02_power','03_inputs','04_outputs') for c in intent.values())
assert all(c['fit'] for c in intent.values())
assert not any(net.startswith(('K_', 'MCU_RX', 'MCU_TX', 'BODY_', 'HEAD_', 'PROXY', 'DRIVE_')) for net in expected_groups)

# Independent checks of new supply, diode polarity and retained ADC protection.
assert n('A1',12)==n('C10',1)==n('TP9',1)=='+3V3_SENSE'
assert intent['A1']['pins']['12']['name']=='3V3'
assert n('A1',14)=='+5V_MODULE' and n('C10',2)=='GND'
assert not any(ref in intent for ref in ['U2','C9','R9'])
assert n('A1',1)=='ADC_SW1' and n('A1',2)=='ADC_SW2'
assert n('A1',13)=='GND'
for i in [1,2]:
    assert n('D'+str(4+i),1)=='+3V3_SENSE'
    assert n('D'+str(4+i),3)==n('R'+str(4+i),1)
    assert intent['D'+str(4+i)]['mpn']=='BAS70,215'
    assert n('D'+str(6+i),2)=='+3V3_SENSE'
    assert n('D'+str(6+i),1)=='GND'
assert n('R4',1)=='+3V3_SENSE' and n('R4',2)=='GND'

# Independent datasheet pin map, regulator setpoint and polarized capacitor check.
assert intent['U1']['mpn']=='LT3012EDE#WPBF'
for pin in ['10','11','8']: assert n('U1',pin)=='ACC_CLAMP'
for pin in ['2','3']: assert n('U1',pin)==n('C3',1)=='REG5'
for pin in ['5','13']: assert n('U1',pin)==n('C3',2)=='GND'
assert n('U1',4)=='REG_FB'
for pin in ['1','6','7','9','12']:assert intent['U1']['pins'][pin]['net'] is None
assert intent['C3']['symbol']=='Device_C_Polarized'
assert intent['C3']['mpn']=='TCJB226M025R0100E'
assert intent['R2']['value']=='30.1k 0.1%'
assert intent['R2']['mpn']=='RT0805BRD0730K1L'
# Procurement reconciliation: exported schematic fields must match the accepted BOM.
components={c.get('ref'):c for c in xml.find('components')}
for ref in ('R2','U1'):
    component=components[ref]
    fields={f.get('name'):f.text for f in component.findall('fields/field')}
    assert component.findtext('value')==intent[ref]['value'],ref
    assert fields['MPN']==intent[ref]['mpn'],ref
assert n('R2',1)=='REG5' and n('R2',2)==n('R3',1)=='REG_FB'
assert 'D3' not in intent
assert n('JP1',1)=='REG5' and n('JP1',2)==n('A1',14)=='+5V_MODULE'
assert n('C4',1)=='+5V_MODULE'
assert n('C7',1)==n('C8',1)=='+3V3_SENSE'

# Provisional envelope; VF and aggregate errors require bench/temperature validation.
adc=[]
bands=[('zero',0,2.5,0,60),('330R',313,345,340,630),('1k',950,1050,930,1390),('3.1k',2955,3265,1830,2530),('released',95000,105000,3160,4095)]
for label,lo,hi,accept_lo,accept_hi in bands:
    values=[]
    for rw in [lo,hi]:
        for rp in [2178,2222]:
            # Sensing and ADC share3V3: ratiometric except diode drop. +/-1% reference mismatch screen.
            for vsense in [3.201,3.399]:
                for ratio in [.99,1.01]:
                    for vf in [0,0.6]: values.append(4095*(1-vf/vsense)*ratio*rw/(rp+rw))
    lower=max(0,math.floor(min(values)-32)); upper=min(4095,math.ceil(max(values)+32))
    assert accept_lo<=lower<=upper<=accept_hi,(label,lower,upper)
    adc.append({'state':label,'assumed_envelope_counts':[lower,upper],'provisional_acceptance':[accept_lo,accept_hi]})
for a,b in zip(bands,bands[1:]):assert a[4]<b[3]
# Firmware contract is checked independently against expected commands, ports and real nets.
contract=json.loads((P/'output_commands.json').read_text())
branches={b['id']:b for b in contract['branches']}
assert set(branches)=={'47R','191R','390R','1K','2K'}
for key,pad,gpio,port,bit,ohms in [('47R',7,6,'SIO',0,47),('191R',8,7,'SIO',1,191),('390R',9,8,'SIO',2,390),('1K',10,9,'SIO',4,1000),('2K',11,10,'SIO',3,2000)]:
    b=branches[key]
    assert (b['module_pad'],b['arduino_pin'],b['port'],b['bit'],b['ohms'])==(pad,gpio,port,bit,ohms)
    assert n('A1',pad)=='BR_'+key
    assert n(b['resistor'],1)==n(b['q'],3)
expected_commands={'release':([],None),'volume_down':(['47R'],[0,100]),'volume_up':(['191R','390R'],[100,160]),'source':(['191R'],[160,220]),'seek_up':(['390R','1K'],[220,320]),'seek_down':(['390R'],[320,470]),'phone':(['1K'],[720,1300]),'mute':(['2K'],[1300,3000])}
assert contract['port_clear_masks']=={'SIO':31}
assert len(contract['commands'])==len(expected_commands)
assert {c['command'] for c in contract['commands']}==set(expected_commands)
outputs=[]
for cmd in contract['commands']:
    ids,window=expected_commands[cmd['command']]
    assert cmd['branches']==ids and cmd['acceptance_ohms']==window
    masks={port:sum(1<<branches[k]['bit'] for k in ids if branches[k]['port']==port) for port in ['SIO']}
    assert cmd['port_set_masks']==masks
    if not ids: continue
    assert len({branches[k]['port'] for k in ids})==1 # Every command can be asserted in one port write.
    rs=[branches[k]['ohms'] for k in ids]
    parallel=lambda xs:1/sum(1/x for x in xs)
    low=parallel([r*.99 for r in rs]); high=parallel([r*1.01+.1 for r in rs])
    assert window[0]<=low<high<=window[1]
    outputs.append({'command':cmd['command'],'branches':ids,'nominal_ohms':parallel(rs),'calculated_ohms':[low,high],'user_window_ohms':window})
erc=json.loads((P/'checks/erc.json').read_text())
violations=[v for s in erc['sheets'] for v in s['violations']]
assert not violations,violations
# Verify selected parts, bundled files, and symbol-to-footprint pad coverage.
# All symbol pins now use numbered footprint pads (plus isolated retention MP).
selection=json.loads((P/'parts_selection.json').read_text())['parts']
footprints_checked=[]
for ref,c in intent.items():
    if ref.startswith('#'): continue
    if not ref.startswith(('TP','NT')):
        assert ref in selection and c['mpn']==selection[ref]['mpn'],ref
        assert c['manufacturer'] and c['assembly'],ref
    fp=c['footprint']
    assert fp,(ref,'missing footprint')
    lib,name=fp.split(':')
    path=P/'footprints'/(lib+'.pretty')/(name+'.kicad_mod')
    assert path.is_file(),str(path)
    pads=set(re.findall(r'\(pad\s+"([^"]+)"',path.read_text()))
    assert set(c['pins']).issubset(pads),(ref,'symbol pins missing from footprint',set(c['pins'])-pads)
    footprints_checked.append(ref)
report={'status':'PASS','kicad_version':erc['kicad_version'],'erc_violations':0,
        'connected_component_pins_checked':sum(p['net'] is not None for r,c in intent.items() if not r.startswith('#') for p in c['pins'].values()),
        'checks':['KiCad netlist equals pin intent','five branches and seven resistance commands','simultaneous-pair GPIO port masks','all capacitors retained','J1 assignments and NC contacts','SWC-only scope and unused D2-D5 disconnected','3.3V supply and ADC clamps; USB power disconnect verified','nonoverlapping provisional ADC bands','output tolerance envelopes inside user windows'],
        'adc_calculation_assumptions':'12-bit4095 fullscale; VSENSE=ADC3V3=3.201-3.399V, +/-1% mismatch screen; BAS70 VF0-0.6V; pullups +/-1%; extra +/-32 counts. Bench/temperature validation still required.',
        'adc':adc,'outputs':outputs,'regulator_nominal_v':1.24*(1+30.1/10)+30e-9*30100,
        'schematic_references_with_selected_mpn':len(selection),
        'mpn_count_scope':'Schematic reference count includes removable A1 module; carrier purchasing replaces A1 with two socket strips. See package-check.json for the 50 fitted carrier parts.','footprints_checked':footprints_checked,
        'pending_footprints':[r for r,c in intent.items() if not r.startswith('#') and not c['footprint']]}
(P/'checks/design_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
