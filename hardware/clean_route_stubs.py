"""Remove only dangling trace segments/vias identified by the current KiCad DRC report.
Always rerun DRC after this operation; this is not a substitute for connectivity checking.
"""
from pathlib import Path
import json, pcbnew as p
base=Path(__file__).resolve().parent
report=json.loads((base/'checks/pcb-drc.json').read_text())
ids={i['uuid'] for v in report['violations'] if v['type'] in ['track_dangling','via_dangling'] for i in v['items']}
b=p.LoadBoard(str(base/'tacoma_swc_only.kicad_pcb'))
removed=0
for t in list(b.GetTracks()):
 if str(t.m_Uuid.AsString()) in ids:
  b.Remove(t);removed+=1
p.SaveBoard(str(base/'tacoma_swc_only.kicad_pcb'),b)
print('Removed',removed,'DRC-identified dangling trace segments/vias; rerun DRC.')
