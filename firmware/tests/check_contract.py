"""Check the firmware's physical mapping and model windows against current hardware."""
from pathlib import Path
import json,re,ast
root=Path(__file__).resolve().parents[2]
h=(root/'firmware/include/swc_logic.h').read_text()
m=(root/'firmware/src/main.cpp').read_text()
c=json.loads((root/'hardware/output_commands.json').read_text())
masks=list(map(int,re.search(r'masks\[\] = \{([^}]+)',h)[1].split(',')))
names=re.findall(r'"([a-z_]+)"',re.search(r'names\[\] = \{([^}]+)',h)[1])
assert dict(zip(names,masks))=={v['command']:v['port_set_masks']['SIO'] for v in c['commands']}
intent=json.loads((root/'hardware/design_intent.json').read_text())['A1']['pins']
assert intent['1']['name']=='D0/GP26/ADC0' and intent['1']['net']=='ADC_SW1'
assert intent['2']['name']=='D1/GP27/ADC1' and intent['2']['net']=='ADC_SW2'
assert 'sw1Pin=26,sw2Pin=27' in m
for b in c['branches']:assert f"GP{b['bit']}" in intent[str(b['module_pad'])]['name']
model=ast.parse((root/'hardware/simulation/run_simulation.py').read_text())
bands=next(ast.literal_eval(n.value) for n in model.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='bands' for t in n.targets))
assert [(b[1],b[2]) for b in bands]==[(0,60),(340,630),(930,1390),(1830,2530),(3160,4095)]
assert 'sio_hw->gpio_set=swc::mask(c)' in m
print('PASS: output masks, input GPIOs, branch GPIOs, and modeled ADC windows match hardware contract')
