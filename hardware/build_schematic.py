"""Native KiCad schematic authoring helper. KiCad owns rendering, ERC and BOM export.

Re-running regenerates the draft; preserve GUI edits before running this again.
Uses installed official symbol artwork plus datasheet-derived local symbols.
"""
from pathlib import Path
import copy, json, re, uuid, math

HERE = Path(__file__).resolve().parent
PARTS = json.loads((HERE/'parts_selection.json').read_text())['parts']
LIBROOT = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols')
PROJECT = 'tacoma_swc_only'
ROOT_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, 'tacoma-swc-only-root'))
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'tacoma-swc-only/' + s))
class Atom(str): pass
def parse(s):
    toks = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', s)
    stack=[]; root=None
    for t in toks:
        if t=='(':
            a=[]
            if stack: stack[-1].append(a)
            else: root=a
            stack.append(a)
        elif t==')': stack.pop()
        else: stack[-1].append(json.loads(t) if t.startswith('"') else Atom(t))
    assert not stack
    return root
def dump(x):
    if isinstance(x,list): return '('+' '.join(dump(y) for y in x)+')'
    if isinstance(x,Atom): return str(x)
    if isinstance(x,str): return json.dumps(x, ensure_ascii=False)
    return str(x)
def node(tag,*args): return [Atom(tag),*args]
def first(x,k): return next((z for z in x if isinstance(z,list) and z and z[0]==k),None)
def allof(x,k): return [z for z in x if isinstance(z,list) and z and z[0]==k]
def fx(size=1.27,justify=None,hide=False):
    r=node('effects',node('font',node('size',size,size)))
    if justify:r.append(node('justify',*[Atom(i) for i in justify.split()]))
    if hide:r.append(node('hide',Atom('yes')))
    return r
def prop(k,v,x=0,y=0,hidden=True): return node('property',k,v,node('at',x,y,0),fx(hide=hidden))
LIBS={}; SYMBOLS={}
def standard(lib,name):
    if lib not in LIBS:
        LIBS[lib]={s[1]:s for s in allof(parse((LIBROOT/(lib+'.kicad_sym')).read_text()),'symbol')}
    def expand(n):
        c=copy.deepcopy(LIBS[lib][n]); e=first(c,'extends')
        if e:
            p=expand(e[1]); old=p[1]; p[1]=n
            for z in allof(p,'symbol'): z[1]=z[1].replace(old+'_',n+'_',1)
            for z in c[2:]:
                if not isinstance(z,list) or z[0]=='extends': continue
                if z[0]=='property': p=[a for a in p if not (isinstance(a,list) and a[:2]==z[:2])]
                elif z[0] not in ('symbol',): p=[a for a in p if not(isinstance(a,list) and a[0]==z[0])]
                p.append(z)
            return p
        return c
    s=expand(name); new=lib+'_'+name; old=s[1]; s[1]=new
    for z in allof(s,'symbol'): z[1]=z[1].replace(old+'_',new+'_',1)
    SYMBOLS[new]=s
    return new
def custom(name,ref,pins,w=15.24,h=12.7,desc='',footprint=''):
    # pins: number, name, electrical type, x, y, angle
    s=node('symbol',name,node('pin_names',node('offset',0.508)),node('in_bom',Atom('yes')),node('on_board',Atom('yes')),
           prop('Reference',ref,0,h+3,False),prop('Value',name,0,h+1,False),prop('Footprint',footprint),prop('Datasheet',''),prop('Description',desc))
    art=node('symbol',name+'_0_1',node('rectangle',node('start',-w,h),node('end',w,-h),node('stroke',node('width',0.254),node('type',Atom('default'))),node('fill',node('type',Atom('background')))))
    body=node('symbol',name+'_1_1')
    for num,pn,ty,x,y,a in pins:
        body.append(node('pin',Atom(ty),Atom('line'),node('at',x,y,a),node('length',2.54),node('name',pn,fx(1.016)),node('number',str(num),fx(1.016))))
    s += [art,body]; SYMBOLS[name]=s
    return name
def pins_for(sym,unit=1):
    out={}
    for u in allof(SYMBOLS[sym],'symbol'):
        m=re.search(r'_(\d+)_(\d+)$',u[1]); un,style=map(int,m.groups())
        if un not in (0,unit) or style not in (0,1): continue
        for p in allof(u,'pin'):
            a=first(p,'at'); no=first(p,'number')[1]
            out[no]={'name':first(p,'name')[1],'type':p[1],'x':float(a[1]),'y':float(a[2]),'a':float(a[3])}
    return out

R=standard('Device','R'); C=standard('Device','C'); CP=standard('Device','C_Polarized')
D=standard('Device','D_Schottky'); TVS=standard('Device','D_TVS'); FUSE=standard('Device','Fuse')
MOS=standard('Transistor_FET','AO3400A'); BAS=custom('BAS70','D',[(1,'A','passive',-5.08,0,0),(2,'NC','no_connect',0,-5.08,90),(3,'K','passive',5.08,0,180)],w=2.54,h=2.54,desc='Nexperia BAS70 single Schottky; pins 1 A, 2 NC, 3 K',footprint='Package_TO_SOT_SMD:SOT-23')
basart=standard('Device','D_Schottky')
base=copy.deepcopy(SYMBOLS[basart]); base[1]='BAS70'
for unit in allof(base,'symbol'):
    unit[1]=unit[1].replace(basart+'_','BAS70_',1)
    for pin in allof(unit,'pin'):
        num=first(pin,'number'); num[1]='3' if num[1]=='1' else '1'
body=allof(base,'symbol')[-1]
body.append(node('pin',Atom('no_connect'),Atom('line'),node('at',0,-5.08,90),node('length',2.54),node('name','NC',fx(1.016)),node('number','2',fx(1.016))))
for field in allof(base,'property'):
    if field[1]=='Value':field[2]='BAS70'
    if field[1]=='Datasheet':field[2]='https://assets.nexperia.com/documents/data-sheet/BAS70.pdf'
SYMBOLS['BAS70']=base
CLAMP=standard('Diode','BAT54S') # identical series-diode pin topology; value explicitly BAS70-04
NANO=standard('MCU_Module','Arduino_Nano_Every'); BUF=standard('74xGxx','74LVC2G125')
XIAO=custom('XIAO_RP2040_Socket','A',[
 *[(str(i+1),name,'bidirectional',-25.4,15.24-i*5.08,0) for i,name in enumerate(['D0/GP26/ADC0','D1/GP27/ADC1','D2/GP28','D3/GP29','D4/GP6','D5/GP7','D6/GP0'])],
 *[(str(14-i),name,ty,25.4,15.24-i*5.08,180) for i,(name,ty) in enumerate([('5V/VBUS','power_in'),('GND','power_in'),('3V3','power_out'),('D10/GP3','bidirectional'),('D9/GP4','bidirectional'),('D8/GP2','bidirectional'),('D7/GP1','bidirectional')])]
 ],w=22.86,h=17.78,desc='Standard XIAO RP2040; USB up. Local DIP numbering, not MCU pin numbers.')
JUMPER=standard('Connector_Generic','Conn_01x02')
REG5=standard('Regulator_Linear','L78L05_SOT89'); ZENER=standard('Device','D_Zener')
CON3=standard('Connector_Generic','Conn_01x03'); TP=standard('Connector','TestPoint')
FLAG=standard('power','PWR_FLAG'); TIE=standard('Device','NetTie_2')
TPS=custom('LT3012EDE','U',[
 ('10','IN','power_in',-17.78,10.16,0),('11','IN','power_in',-17.78,5.08,0),
 ('8','SHDN','input',-17.78,0,0),('1','NC','no_connect',-17.78,-5.08,0),
 ('6','NC','no_connect',-17.78,-10.16,0),('7','NC','no_connect',-17.78,-15.24,0),
 ('2','OUT','power_out',17.78,10.16,180),('3','OUT','passive',17.78,5.08,180),
 ('4','ADJ','input',17.78,0,180),('9','NC','no_connect',17.78,-5.08,180),
 ('12','NC','no_connect',17.78,-10.16,180),
 ('5','GND','power_in',-5.08,-20.32,90),('13','EP','power_in',5.08,-20.32,90)
 ],h=17.78,desc='ADI LT3012EDE adjustable 80V 250mA reverse-protected LDO; DE exposed pad is13',footprint='')
J1SYM=custom('Molex_43045_12_SMT','J',[
 *[(str(i+6),n,'passive',-22.86,17.78-(i-1)*5.08,0) for i,n in enumerate(['EMPTY','SW2','SWRC_RED','SWRC_WHITE','UNUSED_24','ACC'],1)],
 *[(str(i),n,'passive',22.86,17.78-(i-1)*5.08,180) for i,n in enumerate(['EMPTY','EMPTY','EMPTY','SW1','EMPTY','GND'],1)],
 ('MP1','RETENTION_L','passive',-5.08,-22.86,90),
 ('MP2','RETENTION_R','passive',5.08,-22.86,90)
 ],w=20.32,h=20.32,desc='Molex circuit numbers: confirmed loose cable mating face, latch up, top 7-12 and bottom 1-6 left to right; retention pads isolated.')

SHEETS=[]; COMPONENTS={}; EXPECTED={}; SHARED={}
class Sheet:
    def __init__(self,name,title,summary):
        self.name=name; self.uuid=uid(name); self.title=title; self.items=[]; self.used=set(); self.instances=[]; self.counter=0
        self.text(15.24,15.24,title,2.54)
        self.text(15.24,22.86,summary,1.27)
        SHEETS.append(self)
    def newid(self): self.counter+=1; return uid(self.name+'/'+str(self.counter))
    def text(self,x,y,t,size=1.27):
        self.items.append(node('text',t,node('at',x,y,0),fx(size,'left top'),node('uuid',self.newid())))
    def wire(self,a,b):
        if a==b:return
        self.items.append(node('wire',node('pts',node('xy',*a),node('xy',*b)),node('stroke',node('width',0),node('type',Atom('default'))),node('uuid',self.newid())))
    def label(self,p,net,angle=0):
        self.items.append(node('global_label',net,node('shape',Atom('bidirectional')),node('at',*p,angle),fx(1.016,'left' if angle==0 else 'right'),node('uuid',self.newid()),prop('Intersheetrefs','${INTERSHEET_REFS}',p[0],p[1])))
    def nc(self,p): self.items.append(node('no_connect',node('at',*p),node('uuid',self.newid())))
    def junction(self,p): self.items.append(node('junction',node('at',*p),node('diameter',0),node('color',0,0,0,0),node('uuid',self.newid())))
    def comp(self,ref,sym,x,y,nets,value=None,angle=0,unit=1,footprint=None,mpn='',fit=True,note='',autolabel=True,fields=None):
        selected = PARTS.get(ref,{})
        value = selected.get('value',value)
        footprint = selected.get('footprint',footprint)
        mpn = selected.get('mpn',mpn)
        note = selected.get('note',note)
        self.used.add(sym); defs=SYMBOLS[sym]; pinmap=pins_for(sym,unit)
        assert set(nets)==set(pinmap),(ref,set(nets),set(pinmap))
        if ref not in COMPONENTS:
            props={p[1]:p[2] for p in allof(defs,'property')}
            COMPONENTS[ref]={'symbol':sym,'value':value or props.get('Value',sym),'footprint':footprint if footprint is not None else props.get('Footprint',''),'mpn':mpn,'fit':fit,'note':note,'sheet':self.name,'pins':{}}
        c=COMPONENTS[ref]
        sid=self.newid()
        inst=node('symbol',node('lib_id','Tacoma:'+sym),node('at',x,y,angle),node('unit',unit),node('in_bom',Atom('no' if ref.startswith('#') else 'yes')),node('on_board',Atom('no' if ref.startswith('#') else 'yes')),node('dnp',Atom('no' if fit else 'yes')),node('uuid',sid))
        # Visible properties intentionally independent of original library orientations.
        if fields is None:
            if sym==BUF: fields=[(x-7.62,y-20.32),(x-7.62,y-17.78)]
            elif sym==REG5: fields=[(x,y-12.7),(x,y-10.16)]
            elif sym==MOS: fields=[(x+12.7,y),(x+12.7,y+2.54)]
            elif sym==CLAMP: fields=[(x,y-10.16),(x,y-7.62)]
            else: fields=[(x+5.08,y-5.08),(x+5.08,y-2.54)]
        c['manufacturer'] = selected.get('manufacturer','')
        c['assembly'] = selected.get('assembly','PCB_FEATURE' if ref.startswith(('TP','NT','#')) else 'FIT')
        c['datasheet'] = selected.get('source',next((p[2] for p in allof(defs,'property') if p[1]=='Datasheet'),''))
        inst += [prop('Reference',ref,*fields[0],False),prop('Value',c['value'],*fields[1],False),prop('Footprint',c['footprint']),prop('Datasheet',c['datasheet']),prop('MPN',mpn),prop('Manufacturer',c['manufacturer']),prop('Assembly',c['assembly'] if fit else 'DNP'),prop('DesignNote',note)]
        for f in allof(inst,'property')[:2]: first(f,'at')[3]=angle % 180
        positions={}; rad=math.radians(angle)
        for no,p in pinmap.items():
            px=round(x+p['x']*math.cos(rad)-p['y']*math.sin(rad),6)
            py=round(y-p['x']*math.sin(rad)-p['y']*math.cos(rad),6)
            positions[no]=(px,py)
            inst.append(node('pin',no,node('uuid',uid(sid+'/'+no))))
            net=nets[no]; c['pins'][no]={'name':p['name'],'net':net,'type':p['type']}
            EXPECTED[(ref,no)]=net
            if net is None:self.nc((px,py))
            elif autolabel:
                a=(p['a']+angle)%360
                vx=-math.cos(math.radians(a)); vy=math.sin(math.radians(a))
                stub=({'30':15.24,'17':10.16}.get(no,5.08) if sym==NANO else 5.08)
                end=(round(px+vx*stub,6),round(py+vy*stub,6))
                self.wire((px,py),end)
                if abs(vy)>0.5:
                    elbow=(round(end[0]+5.08,6),end[1]); self.wire(end,elbow); end=elbow; la=0
                else: la=0 if vx>0 else 180
                self.label(end,net,la)
        inst.append(node('instances',node('project',PROJECT,node('path','/'+ROOT_ID+'/'+self.uuid,node('reference',ref),node('unit',unit)))))
        self.items.append(inst); self.instances.append(ref)
        return positions
    def save(self):
        libs=[]
        for k in sorted(self.used):
            a=copy.deepcopy(SYMBOLS[k]); a[1]='Tacoma:'+k; libs.append(a)
        root=node('kicad_sch',node('version',20250114),node('generator',Atom('eeschema')),node('generator_version','10.0'),node('uuid',self.uuid),node('paper','A3'),
                  node('title_block',node('title',self.title),node('date','2026-09-26'),node('rev','A-DRAFT'),node('comment',1,'Electrical draft - not released for fabrication')),
                  node('lib_symbols',*libs),*self.items,node('embedded_fonts',Atom('no')))
        (HERE/(self.name+'.kicad_sch')).write_text(dump(root)+'\n')

if __name__=='__main__' and '--pins' in __import__('sys').argv:
    for s in [NANO,REG5,MOS,BAS,CLAMP,BUF,TIE,D]:print(s,json.dumps(pins_for(s),indent=1))
    raise SystemExit

RES0805='Resistor_SMD:R_0805_2012Metric'
RES1206='Resistor_SMD:R_1206_3216Metric'
CAP0805='Capacitor_SMD:C_0805_2012Metric'
SOT23='Package_TO_SOT_SMD:SOT-23'
def resistor(s,ref,x,y,value,a,b,fit=True,angle=90,fp=RES0805,note='1%, >=0.125W'):
    return s.comp(ref,R,x,y,{'1':a,'2':b},value,angle,footprint=fp,fit=fit,note=note)
def cap(s,ref,x,y,value,a,b='GND',fit=True,fp=CAP0805):
    return s.comp(ref,C,x,y,{'1':a,'2':b},value,footprint=fp,fit=fit)
def testpoint(s,ref,x,y,net):
    return s.comp(ref,TP,x,y,{'1':net},net,footprint='TestPoint:TestPoint_Pad_D1.5mm',note='PCB pad, no purchased part')
def flag(s,n,x,y,net): return s.comp('#FLG'+str(n),FLAG,x,y,{'1':net},'PWR_FLAG',footprint='')

s=Sheet('01_interface','01  Harness and XIAO RP2040','SWC-only prototype. Global labels connect across sheets. No Kenwood or illumination circuitry.')
j1nets={'7':None,'8':'SW2_RAW','9':'SWRC_PLUS','10':'SWRC_GND','11':None,'12':'ACC',
        '1':None,'2':None,'3':None,'4':'SW1_RAW','5':None,'6':'GND','MP1':None,'MP2':None}
s.comp('J1',J1SYM,81.28,76.2,j1nets,'Molex 43045-1209',footprint='',note='Manufacturer circuit numbers; confirmed cable face, latch up',fields=[(81.28,48.26),(81.28,50.8)])
s.text(25.4,109.22,'Confirmed view: INTO LOOSE CABLE PLUG, latch up.\nLeft to right: top pins 7-12; bottom pins 1-6.\nTop: empty, SW2, red, white, unused, ACC\nBottom: empty, empty, empty, SW1, empty, GND\nNew factory-installed SMT header; no salvage required.\nSWG bonded to GND in harness; Toyota cavity 24 stays NC.')
xiaonets={'1':'ADC_SW1','2':'ADC_SW2','3':None,'4':None,'5':None,'6':None,'7':'BR_47R','8':'BR_191R','9':'BR_390R','10':'BR_1K','11':'BR_2K','12':'+3V3_SENSE','13':'GND','14':'+5V_MODULE'}
s.comp('A1',XIAO,274.32,83.82,xiaonets,'XIAO RP2040',note='Plug-in standard module; two1x7 sockets',fields=[(274.32,58.42),(274.32,60.96)])
s.text(228.6,124.46,'D0/GP26 and D1/GP27: wheel ADC inputs.\nD6/GP0=47R; D7/GP1=191R; D8/GP2=390R\nD9/GP4=1k; D10/GP3=2k; all five on SIO GPIO bank0.\nUse 3.3V ADC reference; explicit 12-bit conversion.\nREMOVE JP1 shunt before USB; refit only after USB unplugged.\nHardware gate pulldowns hold all outputs OFF during reset.')
cap(s,'C10',60.96,147.32,'2.2uF 16V X7R','+3V3_SENSE')
testpoint(s,'TP9',157.48,147.32,'+3V3_SENSE')
s.comp('NT1',TIE,73.66,177.8,{'1':'SWRC_GND','2':'GND'},'SWRC return bond',footprint='NetTie:NetTie-2_SMD_Pad2.0mm',note='Copper net tie; output returns route to J1 pin 10')
cap(s,'C7',205.74,177.8,'10uF 16V X7R','+3V3_SENSE')
cap(s,'C8',279.4,177.8,'100nF 16V X7R','+3V3_SENSE')
resistor(s,'R4',350.52,177.8,'330R','+3V3_SENSE','GND',fp=RES1206,note='1%,0.25W;3V3 rail bleed for input clamp current')
for i,(net,x) in enumerate([('GND',40.64),('REG5',109.22),('SWRC_PLUS',177.8),('SWRC_GND',246.38)],1):testpoint(s,'TP'+str(i),x,223.52,net)
s.text(25.4,248.92,'Ground routing: power returns to J1 pin 6; Continental branch returns to J1 pin 10. NT1 bonds the two domains on the board.\nNo separate 3.5mm output jack: the confirmed red/white harness path carries the Continental commands.\nSWC-only board: no Kenwood connectors, bypass jumpers, UART buffers or illumination input.')
flag(s,1,350.52,223.52,'GND'); flag(s,2,299.72,223.52,'SWRC_GND')

s=Sheet('02_power','02  ACC protection and preregulator','ACC -> F1 -> D1 -> R1 -> clamped input -> U1 (~4.99V) -> JP1 -> XIAO 5V. REMOVE JP1 before USB connection.')
s.comp('F1',FUSE,48.26,55.88,{'1':'ACC','2':'ACC_FUSED'},'250mA fast / 125V',angle=90,footprint='',mpn='0451.250MRL',note='Littelfuse NANO2 6.1x2.69mm; footprint and pulse coordination pending')
s.comp('D1',D,147.32,55.88,{'1':'ACC_DIODE','2':'ACC_FUSED'},'STPS1H100A',angle=180,footprint='Diode_SMD:D_SMA',mpn='STPS1H100A',note='100V reverse-polarity blocking diode')
resistor(s,'R1',251.46,55.88,'10R / 1W','ACC_DIODE','ACC_CLAMP',fp='',note='Pulse-rated flameproof series resistor; package/MPN pending pulse-energy review')
s.comp('D2',ZENER,350.52,55.88,{'1':'ACC_CLAMP','2':'GND'},'SMBJ24A',angle=90,footprint='Diode_SMD:D_SMB',mpn='SMBJ24A',note='Unidirectional TVS: 24V standoff, 38.9V rated clamp')
s.comp('C1',CP,48.26,106.68,{'1':'ACC_CLAMP','2':'GND'},'47uF / 63V',footprint='',note='105C electrolytic; final case size pending')
cap(s,'C2',134.62,106.68,'10uF 63V X7R','ACC_CLAMP',fp='Capacitor_SMD:C_1210_3225Metric')
s.comp('U1',TPS,243.84,109.22,{'10':'ACC_CLAMP','11':'ACC_CLAMP','8':'ACC_CLAMP','2':'REG5','3':'REG5','4':'REG_FB','5':'GND','13':'GND','1':None,'6':None,'7':None,'9':None,'12':None},'LT3012EDE',footprint='',mpn='LT3012EDE#WPBF',note='DE-12 exposed pad13 GND; reverse-protected; carrier budget60mA',fields=[(243.84,86.36),(243.84,88.9)])
s.comp('C3',CP,350.52,106.68,{'1':'REG5','2':'GND'},'22uF 25V polymer',footprint='',note='Polarized: pin1 positive; 105C, 100mOhm ESR; stable capacitance under DC bias')
resistor(s,'R2',48.26,157.48,'30.1k 0.1%','REG5','REG_FB',note='0.1%, 25ppm/C feedback upper')
resistor(s,'R3',147.32,157.48,'10.0k 0.1%','REG_FB','GND',note='0.1%, 25ppm/C feedback lower')
s.comp('JP1',JUMPER,251.46,157.48,{'1':'REG5','2':'+5V_MODULE'},'REMOVE FOR USB',note='Remove shunt before USB; fitted for vehicle operation')
cap(s,'C4',350.52,157.48,'10uF 25V X7R','+5V_MODULE',fp='Capacitor_SMD:C_1206_3216Metric')
testpoint(s,'TP5',48.26,208.28,'ACC_CLAMP'); testpoint(s,'TP6',147.32,208.28,'+5V_MODULE')
flag(s,3,251.46,208.28,'ACC_CLAMP'); flag(s,4,350.52,208.28,'+5V_MODULE')
s.text(25.4,233.68,'U1: 1.24*(1+30.1k/10k)+30nA*30.1k = 4.9733V. Verify voltage before fitting XIAO.\n60mA output allocation: at16V IN, pass loss~0.66W plus IN*GND-current. Bench-check load and heat.\nJP1 isolates external power for USB programming. Module5V pin is directly tied to USB VBUS.\nD3 removed: JP1 disconnects supplies; LT3012 already tolerates reverse voltage. Never connect USB with JP1 fitted.\nC3 positive pad1=REG5; exposed pad13=GND; adjacent thermal vias.\nTransient coordination, cold clamp behavior and hot-dashboard operation remain unqualified.')

s=Sheet('03_inputs','03  Toyota wheel inputs','Two identical resistor-ladder inputs. XIAO 3V3 output feeds pull-ups and ADC clamps; ADC reference also3V3. See README for revised bands.')
for idx,y in [(1,60.96),(2,142.24)]:
    dref='D'+str(4+idx); cref='D'+str(6+idx); raw='SW'+str(idx)+'_RAW'; adc='ADC_SW'+str(idx); pull='PULL'+str(idx)
    dp=s.comp(dref,BAS,50.8,y,{'1':'+3V3_SENSE','2':None,'3':pull},'BAS70',angle=180,footprint=SOT23,mpn='BAS70,215',note='Pull-up blocking diode; low-drop blocking diode; reverse leakage remains; not an ideal isolator',autolabel=False)
    rp=s.comp('R'+str(4+idx),R,139.7,y,{'1':pull,'2':raw},'2.20k',angle=90,footprint=RES1206,note='1%, 0.25W pull-up; diode drop included in ADC ranges',autolabel=False)
    rs=s.comp('R'+str(6+idx),R,228.6,y,{'1':raw,'2':adc},'22.0k',angle=90,footprint=RES0805,note='1%, ADC series current limit',autolabel=False)
    cp=s.comp('C'+str(4+idx),C,309.88,y+20.32,{'1':adc,'2':'GND'},'10nF 50V X7R',footprint=CAP0805,autolabel=False)
    cl=s.comp(cref,CLAMP,246.38,y+30.48,{'1':'GND','2':'+3V3_SENSE','3':adc},'BAS70-04',angle=90,footprint=SOT23,mpn='BAS70-04,215',note='Pins 1=A1 GND, 2=K2 3V3, 3=common ADC; BAT54S artwork only',autolabel=False,fields=[(233.68,y+27.94),(233.68,y+30.48)])
    s.wire(dp['1'],(25.4,y));s.label((25.4,y),'+3V3_SENSE',180);s.wire(dp['3'],rp['1'])
    s.wire(rp['2'],(190.5,y));s.wire((190.5,y),rs['1']);s.junction((190.5,y));s.wire((190.5,y),(190.5,y-12.7));s.label((190.5,y-12.7),raw)
    s.wire(rs['2'],(281.94,y));s.wire((281.94,y),(309.88,y));s.wire((309.88,y),(337.82,y));s.label((337.82,y),adc)
    s.wire((309.88,y),cp['1']);s.junction((309.88,y));s.wire(cp['2'],(309.88,y+40.64));s.label((309.88,y+40.64),'GND')
    s.wire(cl['3'],(281.94,y+30.48));s.wire((281.94,y+30.48),(281.94,y));s.junction((281.94,y))
    for p,net in [('1','GND'),('2','+3V3_SENSE')]:
        end=(cl[p][0]-12.7,cl[p][1]);s.wire(cl[p],end);s.label(end,net,180)
    testpoint(s,'TP'+str(6+idx),360.68,y+30.48,adc)
    s.text(27.94,y+20.32,f'SW{idx}: A{idx-1}\nRC approximately 0.22ms')
s.text(25.4,215.9,'SW1: Seek+ <2.5R; Seek- 313-345R; Vol+ 950-1050R; Vol- 2955-3265R.\nSW2: MODE <2.5R; Hang Up 313-345R; Answer 950-1050R; optional voice band unused.\nReleased: 95-105k on either line. No radio pull-ups may remain connected to SW1/SW2.\nADC uses 3V3 reference and 12-bit counts; wheel pull-ups use same rail. Use finite bands with gaps; reject two active lines; debounce initially 20ms.\nD5/D6 are BAS70 (not BAS21); D7/D8 limit ADC voltage. R4 sinks limited clamp current.\nThis is not zero-leakage isolation. Validate leakage, cold clamp voltage and ADC acquisition before release.\nBench resistor sweep must include diode drop, supply variation, input leakage and all documented Toyota limits.')

s=Sheet('04_outputs','04  Continental resistor outputs','Radio supplies SWRC_PLUS. Five branches, seven commands. Blank all before applying a valid branch mask; hold that mask for held buttons.')
cap(s,'C11',330.2,55.88,'10nF 50V X7R','SWRC_PLUS','SWRC_GND')
s.text(307.34,78.74,'C11: switching-pulse filter.\nDoes not clamp an ACC fault.\nRadio pull-up inferred ~470R.')
branches=[(1,'47R','47R','D6 / GP0'),(3,'191R','191R','D7 / GP1'),(5,'390R','390R','D8 / GP2'),(6,'1K','1.00k','D9 / GP4'),(7,'2K','2.00k','D10 / GP3')]
for row,(i,name,val,gpio) in enumerate(branches):
    y=45.72+row*30.48; drain='OUT_D'+str(i); gate='OUT_G'+str(i)
    s.text(15.24,y-7.62,f'{val} branch ({gpio})',1.27)
    cr=s.comp('R'+str(10+i),R,256.54,y-10.16,{'1':drain,'2':'SWRC_PLUS'},val,angle=90,footprint=RES0805,note='1%, command resistor; user empirically verified window',autolabel=False)
    q=s.comp('Q'+str(i),MOS,190.5,y,{'1':gate,'2':'SWRC_GND','3':drain},'AO3400A',mpn='AO3400A',note='G=1 S=2 D=3; output active HIGH',autolabel=False)
    gr=s.comp('R'+str(20+i),R,120.65,y,{'1':'BR_'+name,'2':gate},'1.00k',angle=90,footprint=RES0805,note='1%, gate series resistor',autolabel=False)
    pd=s.comp('R'+str(30+i),R,162.56,y+6.35,{'1':gate,'2':'SWRC_GND'},'100k',footprint=RES0805,note='1%, gate-source pulldown; reset default OFF',autolabel=False,fields=[(149.86,y+5.08),(149.86,y+7.62)])
    s.wire(gr['1'],(101.6,y)); s.label((101.6,y),'BR_'+name,180)
    s.wire(gr['2'],(162.56,y)); s.wire((162.56,y),q['1']); s.wire((162.56,y),pd['1']); s.junction((162.56,y))
    s.wire(q['3'],(193.04,y-10.16)); s.wire((193.04,y-10.16),cr['1'])
    s.wire(cr['2'],(279.4,y-10.16)); s.label((279.4,y-10.16),'SWRC_PLUS')
    s.wire(q['2'],(193.04,y+10.16)); s.wire(pd['2'],(193.04,y+10.16)); s.junction((193.04,y+10.16))
    s.wire((193.04,y+10.16),(218.44,y+10.16)); s.label((218.44,y+10.16),'SWRC_GND')
s.text(25.4,205.74,'COMMAND MASKS (all other branches OFF):\nVol-: Q1 (47R); Vol+: Q3 + Q5 (128.21R); MODE: Q3 (191R)\nSeek+: Q5 + Q6 (280.58R); Seek-: Q5 (390R); Phone: Q6 (1k); Mute: Q7 (2k)\nIdle / invalid: all OFF. GP0/1/2/4/3; apply pairs in one SIO register write.\nClear SIO mask0x1F before setting the command mask; preserve all other GPIO.\nD2-D5 are unused. Capacitors remain populated per user preference.')
s.text(25.4,251.46,'All Q sources return to SWRC_GND, then NT1 to GND. Do not add a series resistor in the shared SWRC_PLUS path.\nAt VGS=2.5V the selected MOSFET adds <=0.048R at 25C datasheet conditions; bench-check completed branch resistance.\nPhone remains context-sensitive (answer/end); Hang Up intentionally selects the user-requested Mic Mute command.')

# Persist native files and the project-local symbol library.
for s in SHEETS:s.save()
SYMBOLS = {k:v for k,v in SYMBOLS.items() if any(k in s.used for s in SHEETS)}
lib=node('kicad_symbol_lib',node('version',20250114),node('generator',Atom('kicad_symbol_editor')),*SYMBOLS.values())
(HERE/'Tacoma.kicad_sym').write_text(dump(lib)+'\n')
(HERE/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Tacoma")(type "KiCad")(uri "${KIPRJMOD}/Tacoma.kicad_sym")(options "")(descr "Project-local draft symbols")))\n')
root=node('kicad_sch',node('version',20250114),node('generator',Atom('eeschema')),node('generator_version','10.0'),node('uuid',ROOT_ID),node('paper','A3'),node('lib_symbols'),
          node('title_block',node('title','Tacoma SWC-only translator'),node('date','2026-09-26'),node('rev','A-DRAFT')))
root.append(node('text','SWC ONLY - ELECTRICAL DRAFT\n3.3V Toyota wheel sensing to Continental resistor commands\nOpen each of the four circuit sheets below.\nRouted PCB draft available; power release checks remain before ordering.',node('at',25.4,20.32,0),fx(2.0,'left top'),node('uuid',uid('rootnote'))))
for i,s in enumerate(SHEETS):
    x=25.4+(i%3)*127; y=68.58+(i//3)*55.88
    sh=node('sheet',node('at',x,y),node('size',104.14,30.48),node('stroke',node('width',0.1524),node('type',Atom('default'))),node('fill',node('color',0,0,0,0)),node('uuid',s.uuid),
                     prop('Sheetname',s.title,x,y-2.54,False),prop('Sheetfile',s.name+'.kicad_sch',x,y+33.02,False),
                     node('instances',node('project',PROJECT,node('path','/'+ROOT_ID,node('page',str(i+2))))))
    for f in allof(sh,'property'):first(f,'effects').append(node('justify',Atom('left')))
    root.append(sh)
root.append(node('sheet_instances',node('path','/',node('page','1')))); root.append(node('embedded_fonts',Atom('no')))
(HERE/(PROJECT+'.kicad_sch')).write_text(dump(root)+'\n')
if not (HERE/(PROJECT+'.kicad_pro')).exists():
    (HERE/(PROJECT+'.kicad_pro')).write_text(json.dumps({'meta':{'filename':PROJECT+'.kicad_pro','version':1},'schematic':{'meta':{'version':1}},'text_variables':{'REVISION':'A-DRAFT'}},indent=2)+'\n')
(HERE/'design_intent.json').write_text(json.dumps(COMPONENTS,indent=2)+'\n')
print(f'Created {len(SHEETS)+1} native sheets, {len(COMPONENTS)} references (including power flags).')
