"""Focused sensitivity check using the user's inferred 470-ohm radio pull-up.
Reuses the same approximate model; candidate capacitor is NOT a PCB change.
"""
from pathlib import Path
import json
p=Path(__file__).with_name('run_simulation.py')
ns={'__file__':str(p)}
exec(p.read_text().split('s=Spice();')[0],ns)
s=ns['Spice']();rows=[]
for extra in [0,10e-9]:
 for cmd,mask in ns['command_masks'].items():
  if not mask:continue
  cir=ns['deck'](rpull=470,cradio=100e-12+extra,mask=mask,transient=True)
  # Historical A/B comparison: remove the now-installed C11 from both decks.
  cir='\n'.join(line for line in cir.splitlines() if not line.startswith('C11 '))+'\n'
  s.load(cir);s.command('tran 100n 8m')
  t=s.vector('time');v=s.vector(ns['node']('J1',9));assert t[-1]>=.008
  r=[x/((3.3-x)/470) for tt,x in zip(t,v) if .003<=tt<=.0039]
  lo,hi=ns['windows'][cmd];assert lo<=min(r)<=max(r)<=hi
  rows.append(dict(command=cmd,added_capacitance_f=extra,min_v=min(v),max_v=max(v),settled_ohms=[min(r),max(r)]))
out=ns['OUT']/'radio_470ohm.json'
out.write_text(json.dumps({'assumed_pullup_ohms':470,'assumed_intrinsic_capacitance_f':100e-12,'model':'Same approximate behavioral MOSFET model as run_simulation.py; not radio safety qualification','results':rows},indent=2)+'\n')
for extra in [0,10e-9]:
 a=[x for x in rows if x['added_capacitance_f']==extra]
 print(extra,max(x['max_v'] for x in a))
