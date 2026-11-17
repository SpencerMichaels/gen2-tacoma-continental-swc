"""Replay ngspice input waveforms through the actual portable C++ firmware logic.
Does not emulate RP2040 ADC, Arduino scheduling, regulator or radio firmware.
"""
from pathlib import Path
import bisect, hashlib, itertools, json, subprocess, tempfile
p=Path(__file__).with_name('run_simulation.py'); ns={'__file__':str(p)}
exec(p.read_text().split('s=Spice();')[0],ns)
root=p.resolve().parents[2]; out=ns['OUT']; s=ns['Spice'](); rows=[]
with tempfile.TemporaryDirectory(prefix='swc-firmware-') as td:
    td=Path(td); cpp=td/'replay.cpp'; exe=td/'replay'
    cpp.write_text('#include "swc_logic.h"\n#include <iostream>\nint main(){unsigned t,a,b;swc::Wheel w;while(std::cin>>t>>a>>b){if(t==99999){w.reset();continue;}std::cout<<t<<" "<<swc::name(w.update(a,b,t))<<"\\n";}}\n')
    subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(root/'firmware/include'),str(cpp),'-o',str(exe)],check=True)
    for (line,r,cmd),cap,bounce in itertools.product([(1,.001,'seek_up'),(1,329,'seek_down'),(1,1000,'volume_up'),(1,3110,'volume_down'),(2,.001,'source'),(2,329,'mute'),(2,1000,'phone')],[7e-9,10e-9,13e-9],[False,True]):
        raw=ns['node']('J1',4 if line==1 else 8)
        cir=ns['deck']().replace(f'Rwheel{line} {raw} 0 100k',f'Bwheel{line} {raw} 0 I=V({raw})/(V(press)>.5 ? {r} : 100000)')
        cir='\n'.join(x.rsplit(' ',1)[0]+f' {cap}' if x.startswith(('C5 ','C6 ')) else x for x in cir.splitlines())
        edges='150m 0 150.001m 1 151m 1 151.001m 0 153m 0 153.001m 1' if bounce else '150m 0 150.001m 1'
        cir=cir.replace('.end',f'Vpress press 0 PWL(0 0 {edges} 250m 1 250.001m 0 400m 0)\n.end')
        s.load(cir);s.command('tran 20u 400m 0 20u');t=s.vector('time');a=s.vector(ns['node']('A1',1));b=s.vector(ns['node']('A1',2))
        inputs=[]; descriptions=[]
        for phase,ea,eb in itertools.product([i*.25 for i in range(8)],[-32,0,32],[-32,0,32]):
            samples=[]
            for tick in range(0,399,2):
                k=min(bisect.bisect_left(t,(tick+phase)*.001),len(t)-1)
                samples.append((tick,*[max(0,min(4095,round(4095*x[k]/3.3)+err)) for x,err in [(a,ea),(b,eb)]]))
            inputs.extend('%d %d %d\n'%x for x in samples);inputs.append('99999 0 0\n')
            descriptions.append((phase,ea,eb,samples))
        output=subprocess.check_output([str(exe)],input=''.join(inputs),text=True).splitlines()
        for n,(phase,ea,eb,samples) in enumerate(descriptions):
            ev=[(int(v.split()[0]),v.split()[1]) for v in output[n*200:(n+1)*200]]
            active=[tt for tt,c in ev if c==cmd]
            ok=len(ev)==200 and bool(active) and 170<=min(active)<=180 and all(c in ['release',cmd] for _,c in ev) and all(c=='release' for tt,c in ev if tt>=254 or tt<150)
            rows.append(dict(line=line,command=cmd,c_filter_f=cap,bounce=bounce,sample_phase_ms=phase,adc_errors=[ea,eb],passed=ok,first_active_ms=active[:1],last_active_ms=active[-1:]))
        print(f'{cmd} C={cap:g} bounce={bounce}: cumulative {len(rows)} cases',flush=True)
report=dict(status='PASS_WITH_MODEL_LIMITATIONS' if all(x['passed'] for x in rows) else 'FAIL',cases=len(rows),failures=[x for x in rows if not x['passed']],
    firmware_sha256=hashlib.sha256((root/'firmware/include/swc_logic.h').read_bytes()).hexdigest(),netlist_sha256=hashlib.sha256((ns['BASE']/'checks/netlist.xml').read_bytes()).hexdigest(),
    assumptions=['Actual Wheel C++ code compiled on host; not MCU execution','Ideal 3.3V; approximate diode models; C5/C6=7/10/13nF sensitivity screen','2ms sampling with eight phases and independent +/-32-count offsets','Seven nominal button resistances, clean and bounced presses, 100ms holds; not all physical input conditions'],results=rows)
(out/'firmware_integration.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['status'],len(rows),'cases',len(report['failures']),'failures')
assert not report['failures']
