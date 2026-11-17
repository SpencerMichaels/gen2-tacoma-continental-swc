"""Use native KiCad copper shapes to audit raw-ACC/radio-signal spacing.
Run with KiCad's bundled Python. Ground is intentionally shared and excluded from
positive-signal separation; this is not an isolation/creepage certification.
"""
from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET
import pcbnew as p
B=Path(__file__).resolve().parent.parent
b=p.LoadBoard(str(B/'tacoma_swc_only.kicad_pcb'))
x=ET.parse(B/'checks/netlist.xml')
net={(nd.attrib['ref'],nd.attrib['pin']):n.attrib['name'] for n in x.findall('./nets/net') for nd in n.findall('node')}
raw={'ACC','ACC_FUSED','ACC_DIODE','ACC_CLAMP'}
radio={'SWRC_PLUS'}|{net[f'Q{i}','3'] for i in [1,3,5,6,7]}
items=list(b.GetTracks())+[pad for fp in b.GetFootprints() for pad in fp.Pads()]
def name(item):
    if isinstance(item,p.PAD):return item.GetParentFootprint().GetReference()+'.'+item.GetNumber()
    return ('via' if isinstance(item,p.PCB_VIA) else 'track')+':'+str(item.m_Uuid.AsString())
def clearance(a,b):
    # Native shape collision includes pad geometry/rotation and trace width.
    if a.Collide(b,0):return 0
    lo,hi=0,p.FromMM(100)
    while hi-lo>100: #0.0001mm resolution, report only0.001mm
        mid=(lo+hi)//2
        if a.Collide(b,mid):hi=mid
        else:lo=mid
    return p.ToMM(lo)
closest=None;count=0
for layer in [p.F_Cu,p.B_Cu]:
    ra=[i for i in items if i.GetNetname() in raw and i.IsOnLayer(layer)]
    rb=[i for i in items if i.GetNetname() in radio and i.IsOnLayer(layer)]
    for a in ra:
        sa=a.GetEffectiveShape(layer)
        for z in rb:
            sz=z.GetEffectiveShape(layer);d=clearance(sa,sz);count+=1
            if closest is None or d<closest['clearance_mm']:
                closest={'clearance_mm':d,'layer':'F.Cu' if layer==p.F_Cu else 'B.Cu',
                         'raw_net':a.GetNetname(),'raw_item':name(a),'radio_net':z.GetNetname(),'radio_item':name(z)}
# No power or radio-signal zone is silently missed by pad/track analysis.
zones=[]
for zone in b.Zones():
    if zone.GetIsRuleArea() if hasattr(zone,'GetIsRuleArea') else zone.IsRuleArea():continue
    zones.append(zone.GetNetname());assert zone.GetNetname()=='GND'
r={'board_sha256':hashlib.sha256((B/'tacoma_swc_only.kicad_pcb').read_bytes()).hexdigest(),
   'comparisons':count,'raw_acc_nets':sorted(raw),'radio_positive_nets':sorted(radio),
   'closest_same_layer_copper_pair':closest,'copper_zone_nets':zones,
   'interpretation':'Positive rail separation only. GND and SWRC_GND are intentionally bonded by NT1. Ordinary clearances are not a fault-proof isolation barrier.'}
assert closest['clearance_mm']>=1.999 # 2 mm intentional ACC-to-output rule
(B/'checks/simulation/layout_audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
