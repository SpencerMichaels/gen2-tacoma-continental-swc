#!/usr/bin/env python3
"""Build placed carrier PCB from verified netlist. Requires KiCad's pcbnew Python.
Writes placement draft; optional --session checks/routing.ses imports the local routing session.
After import, run KiCad DRC; prune reported stubs with clean_route_stubs.py and recheck.
Do not run over manual PCB edits without a backup.
"""
from pathlib import Path
import json, argparse, xml.etree.ElementTree as ET, shutil
import pcbnew as p
BASE=Path(__file__).resolve().parent
args=argparse.ArgumentParser();args.add_argument('--session');opt=args.parse_args()
intent=json.loads((BASE/'design_intent.json').read_text());xml=ET.parse(BASE/'checks/netlist.xml')
b=p.BOARD();b.SetCopperLayerCount(2);b.SetFileName(str(BASE/'tacoma_swc_only.kicad_pcb'))
mm=p.FromMM
v=lambda x,y:p.VECTOR2I(mm(x),mm(y))
ds=b.GetDesignSettings();ds.m_MinClearance=mm(.2);ds.m_CopperEdgeClearance=mm(.5);ds.m_TrackMinWidth=mm(.2)
nc=ds.m_NetSettings.GetDefaultNetclass();nc.SetClearance(mm(.2));nc.SetTrackWidth(mm(.3));nc.SetViaDiameter(mm(.7));nc.SetViaDrill(mm(.3))
nets={}
for n in xml.findall('./nets/net'):
 name=n.attrib['name'].replace('/','{slash}');net=p.NETINFO_ITEM(b,name);b.Add(net);nets[name]=net
padnets={(nd.attrib['ref'],nd.attrib['pin']):n.attrib['name'].replace('/','{slash}') for n in xml.findall('./nets/net') for nd in n.findall('node')}
# Positions are footprint origins, in millimetres. Zero is upper-left board corner.
pos={
'A1':(6.5,13,0),'J1':(42,12.58,0),'NT1':(40,19,0),
'F1':(57,18.5,180),'D1':(57,24,0),'R1':(61,31,180),
'D2':(45,23,0),'C1':(34,24,0),'C2':(56,35.6,0),'U1':(51,37,0),
'C3':(46,35.6,180),'R2':(44,39,0),'R3':(50,42,0),'JP1':(29,34,90),'C4':(24,34,90),
'C11':(23,52,0),'C7':(3,37,90),'C8':(3,42,90),'R4':(36,43,0),'C10':(3,32,90),
'D5':(8,35,180),'R5':(13,35,0),'R7':(18,35,0),'C5':(22,39,90),'D7':(8,40,180),
'D6':(13,40,180),'R6':(18,40,0),'R8':(25,40,0),'C6':(28.5,39,90),'D8':(33,39,180),
'TP1':(3,46,0),'TP2':(61,42.5,0),'TP3':(61,45,0),'TP4':(57,46,0),
'TP5':(61,40,0),'TP6':(36,34,0),'TP7':(22,43,0),'TP8':(29,43,0),'TP9':(26,18,0)}
for i,x in zip([1,3,5,6,7],[13,23,33,43,53]):
 pos['Q'+str(i)]=(x,49,0);pos['R'+str(10+i)]=(x+3,49,90)
 pos['R'+str(20+i)]=(x-2,46,0);pos['R'+str(30+i)]=(x-3,50,90)
fps={}
root='68ed67a0-dd7d-5697-9865-21f458060be0'
for el in xml.findall('./components/comp'):
 ref=el.attrib['ref'];c=intent.get(ref,{})
 if not c.get('footprint'):continue
 lib,name=c['footprint'].split(':');fp=p.FootprintLoad(str(BASE/'footprints'/(lib+'.pretty')),name)
 if fp is None:raise RuntimeError(c['footprint'])
 fp.SetFPID(p.LIB_ID(lib,name));fp.SetReference(ref);fp.SetValue(c['value'])
 fp.SetExcludedFromBOM(False)
 for field in el.findall('./fields/field'):
  if field.attrib['name'] not in ['Reference','Value','Footprint']:
   fp.SetField(field.attrib['name'],field.text or '');fp.GetField(field.attrib['name']).SetVisible(False)
 path=p.KIID_PATH()
 for s in (root+el.find('sheetpath').attrib['tstamps']+el.findtext('tstamps')).split('/'):
  if s:path.push_back(p.KIID(s))
 fp.SetPath(path);fp.SetSheetname(el.find('sheetpath').attrib['names']);fp.SetSheetfile(c['sheet']+'.kicad_sch')
 b.Add(fp);x,y,a=pos[ref];fp.SetOrientationDegrees(a);fp.SetPosition(v(x,y));fps[ref]=fp
 for pad in fp.Pads():
  name=padnets.get((ref,pad.GetNumber()))
  if name:pad.SetNet(nets[name])
  pin=c['pins'].get(pad.GetNumber(),{})
  pad.SetPinFunction(pin.get('name',''));pad.SetPinType('no_connect' if pin.get('net') is None else pin.get('type','passive'))
  if ref=='A1':pad.SetLocalZoneConnection(p.ZONE_CONNECTION_THERMAL)
 fp.Value().SetVisible(False);r=fp.Reference();r.SetTextSize(v(.9,.9));r.SetTextThickness(mm(.13));r.SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T));r.SetVisible(True)
 # References below/above with deliberate space for hand assembly.
 r.SetPosition(v(x,y-(3.3 if a in (90,270) else 2.4) if ref[0] in 'RCDQU' else y+3))
 if ref=='C3':
  for graphic in fp.GraphicalItems():
   if graphic.GetLayer()==p.F_SilkS:graphic.SetLayer(p.F_Fab)
 r.SetLayer(p.F_Fab)
 if ref in ['A1','J1','U1','R1','F1','C1','JP1'] or ref.startswith('TP'):
  r.SetLayer(p.F_SilkS)
 if ref=='A1':r.SetPosition(v(14,29))
 if ref=='J1':r.SetPosition(v(42,5))
 if ref=='JP1':r.SetPosition(v(30,36.5))
 if ref=='R1':r.SetPosition(v(51,31))
 if ref=='U1':r.SetPosition(v(55,40))
 if ref=='F1':r.SetPosition(v(57,16))
 if ref=='C1':r.SetPosition(v(34,18.5))
 if ref.startswith('TP'):r.SetPosition(v(x,y-1.8));r.SetTextSize(v(.8,.8))
 if ref in ['TP2','TP3','TP5']:r.SetPosition(v(63.3,y))
# Short regulator connections and adjacent (not in-pad) ground thermal vias.
def trace(net, points, width=.3):
 for a,z in zip(points,points[1:]):
  t=p.PCB_TRACK(b);t.SetStart(v(*a));t.SetEnd(v(*z));t.SetWidth(mm(width));t.SetLayer(p.F_Cu);t.SetNet(nets[net]);t.SetLocked(True);b.Add(t)
trace('REG5',[(47.54,35.6),(48.19,36.25),(49.55,36.25),(49.55,36.75)],.25)
trace('GND',[(49.55,37.75),(51,37.75)],.25)
for y in [34.45,39.55]:
 trace('GND',[(51,37),(51,y),(50.4,y)],.5)
 trace('GND',[(51,y),(51.6,y)],.5)
 for x in [50.4,51.6]:
  via=p.PCB_VIA(b);via.SetPosition(v(x,y));via.SetWidth(mm(.6));via.SetDrill(mm(.3));via.SetViaType(p.VIATYPE_THROUGH);via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetNet(nets['GND']);via.SetLocked(True);b.Add(via)
# Board edge and corner M3 clearance holes (3.2 mm, no plated barrel).
for a,z in [((0,0),(65,0)),((65,0),(65,55)),((65,55),(0,55)),((0,55),(0,0))]:
 s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(v(*a));s.SetEnd(v(*z));s.SetLayer(p.Edge_Cuts);s.SetWidth(mm(.05));b.Add(s)
hlib=BASE/'footprints/MountingHole.pretty';hlib.mkdir(exist_ok=True)
source=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/MountingHole.pretty/MountingHole_3.2mm_M3.kicad_mod')
shutil.copyfile(source,hlib/source.name)
for i,(x,y) in enumerate([(4.5,4.5),(60.5,4.5),(60.5,50.5),(4.5,50.5)],1):
 f=p.FootprintLoad(str(hlib),'MountingHole_3.2mm_M3');f.SetFPID(p.LIB_ID('MountingHole','MountingHole_3.2mm_M3'));f.SetAttributes(f.GetAttributes() | p.FP_BOARD_ONLY);f.SetReference('H'+str(i));f.SetValue('M3');f.SetPosition(v(x,y));b.Add(f);f.Value().SetVisible(False);f.Reference().SetVisible(False)
 # Clear all copper around screw heads on both layers.
 for layer in [p.F_Cu,p.B_Cu]:
  zone=p.ZONE(b);zone.SetLayer(layer);zone.SetIsRuleArea(True);zone.SetDoNotAllowPads(False)
  for method in ['SetDoNotAllowTracks','SetDoNotAllowVias','SetDoNotAllowZoneFills']:getattr(zone,method)(True)
  out=zone.Outline();out.NewOutline()
  for xx,yy in [(x-3.5,y-3.5),(x+3.5,y-3.5),(x+3.5,y+3.5),(x-3.5,y+3.5)]:out.Append(mm(xx),mm(yy))
  b.Add(zone)
# Conservative top-side metal-tang keepouts, beside J1 signal row. No exposed or buried top copper here.
for x in [30.615,53.385]:
 zone=p.ZONE(b);zone.SetLayer(p.F_Cu);zone.SetIsRuleArea(True);zone.SetDoNotAllowTracks(True);zone.SetDoNotAllowVias(True);zone.SetDoNotAllowZoneFills(True);zone.SetDoNotAllowPads(False)
 out=zone.Outline();out.NewOutline()
 for xx,yy in [(x-1.8,6.8),(x+1.8,6.8),(x+1.8,12),(x-1.8,12)]:out.Append(mm(xx),mm(yy))
 b.Add(zone)
def label(t,x,y,size=1):
 q=p.PCB_TEXT(b);q.SetText(t);q.SetPosition(v(x,y));q.SetTextSize(v(size,size));q.SetTextThickness(mm(.15));q.SetLayer(p.F_SilkS);b.Add(q)
label('TACOMA SWC / RP2040',33,53.5,.8)
label('USB',14,6,.85)
label('REMOVE JP1 FOR USB',16,3,.8)
label('+',47.3,38,.85) # C3 positive; full outline retained on assembly layer
if opt.session:
 assert p.ImportSpecctraSES(b,str(Path(opt.session).resolve()))
 # Continuous return copper on the back plus local top thermal spreading.
 for layer in [p.F_Cu,p.B_Cu]:
  zone=p.ZONE(b);zone.SetLayer(layer);zone.SetNet(nets['GND']);zone.SetLocalClearance(mm(.25));zone.SetMinThickness(mm(.2));zone.SetThermalReliefGap(mm(.3));zone.SetThermalReliefSpokeWidth(mm(.3));zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
  out=zone.Outline();out.NewOutline()
  coords=[(25,.6),(64.4,.6),(64.4,54.4),(.6,54.4),(.6,32),(25,32)] if layer==p.F_Cu else [(0.6,.6),(64.4,.6),(64.4,54.4),(.6,54.4)]
  for x,y in coords:out.Append(mm(x),mm(y))
  b.Add(zone)
p.SaveBoard(str(BASE/'tacoma_swc_only.kicad_pcb'),b)
if not opt.session:
 assert p.ExportSpecctraDSN(b,str(BASE/'checks/placement.dsn'))
 # Separate wide protected supply and return routes from signal traces.
 import re
 dsn=BASE/'checks/placement.dsn';text=dsn.read_text();start=text.index('(class kicad_default');end=text.index('(circuit',start)
 power=['ACC','ACC_FUSED','ACC_DIODE','SWRC_GND']
 block=text[start:end]
 for name in power:block=re.sub(r'(?<![A-Za-z0-9_])'+name+r'(?![A-Za-z0-9_])','',block)
 text=text[:start]+block+text[end:]
 insertion='(class power '+' '.join(power)+' (circuit (use_via "Via[0-1]_700:300_um")) (rule (width 600) (clearance 200)))\n    '
 text=text.replace('(class kicad_default',insertion+'(class kicad_default')
 text=text.replace('(pins J1-MP J1-MP@1)','(pins J1-MP)')
 text=text.replace('(structure','(structure\n    (keepout "net-tie-copper" (rect F.Cu 38800 -20200 41200 -17800))',1)
 dsn.write_text(text)
print('Placed',len(fps),'schematic footprints and four mounting holes.')

# SaveBoard creates default project settings; preserve explicit manufacturing constraints.
project=BASE/'tacoma_swc_only.kicad_pro';settings=json.loads(project.read_text())
settings['board']['design_settings']['rules'].update({'min_clearance':.15,'min_through_hole_diameter':.2,'min_track_width':.2,'min_copper_edge_clearance':.5})
settings['net_settings']['classes'][0]['clearance']=.15
settings['text_variables']={'REVISION':'A-DRAFT'}
project.write_text(json.dumps(settings,indent=2)+'\n')
