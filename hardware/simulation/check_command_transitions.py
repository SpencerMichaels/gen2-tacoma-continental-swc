"""All directed command transitions with a proposed 20 us break-before-make stub.
C11 sensitivity at 7/13 nF is an engineering screen, not a guaranteed tolerance bound.
No actual firmware or regulator/brownout behavior is represented.
"""
from pathlib import Path
import itertools,json,hashlib
p=Path(__file__).with_name('run_simulation.py');ns={'__file__':str(p)}
exec(p.read_text().split('s=Spice();')[0],ns)
s=ns['Spice']();rows=[];failures=[]
for (before,mb),(after,ma),cap in itertools.product(ns['command_masks'].items(),ns['command_masks'].items(),[7e-9,13e-9]):
 if before==after:continue
 cir=ns['deck'](rpull=470,cradio=100e-12,mask=mb)
 for i,bit in ns['branches']:
  vb=3.3 if mb&(1<<bit) else 0;va=3.3 if ma&(1<<bit) else 0
  cir=cir.replace(f'Vmcu{i} drive{i} 0 DC {vb}',f'Vmcu{i} drive{i} 0 PWL(0 {vb} 1m {vb} 1.001m 0 1.021m 0 1.022m {va} 2m {va})')
 cir='\n'.join(line.rsplit(' ',1)[0]+f' {cap}' if line.startswith('C11 ') else line for line in cir.splitlines())+'\n'
 s.load(cir);s.command('tran 1u 2m 0 1u');t=s.vector('time');v=s.vector(ns['node']('J1',9));assert t[-1]>=.002
 settled=[x for tt,x in zip(t,v) if tt>=.0012]
 if after=='release':ok=min(settled)>3.299
 else:
  r=[x/((3.3-x)/470) for x in settled];lo,hi=ns['windows'][after];ok=lo<=min(r)<=max(r)<=hi
 if not ok:failures.append([before,after,cap,'settling'])
 rows.append(dict(before=before,after=after,c11_f=cap,min_v=min(v),max_v=max(v),settled_pass=ok))
report=dict(status='PASS_WITH_MODEL_LIMITATIONS' if not failures else 'FAIL',cases=len(rows),failures=failures,
 netlist_sha256=hashlib.sha256((ns['BASE']/'checks/netlist.xml').read_bytes()).hexdigest(),
 assumptions=['470 ohm radio pull-up to ideal 3.3 V;100 pF intrinsic input capacitance','C11 screened at 7/13 nF;not a manufacturer worst-case envelope','Gate edges 1 us;20 us all-off interval;settling checked 178 us after new mask completes','Behavioral MCU and approximate MOSFET model;no firmware,receiver sampling,or power-stage validation','Transitions can cross intermediate command voltages;radio debounce behavior unknown'],results=rows)
(ns['OUT']/'command_transitions.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['status'],report['cases'],'cases; peak',max(x['max_v'] for x in rows),'V; failures',failures)
assert not failures
