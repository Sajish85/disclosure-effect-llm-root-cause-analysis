import json
R='/Users/sajishkrishnan/d1-coincident-rca'
man={json.loads(l)['name']:json.loads(l) for l in open(R+'/data/raw/manifest.jsonl')}
NET={'NetworkDelay','NetworkLoss','NetworkPartition','NetworkCorrupt','NetworkBandwidth'}
def accept(case,f):
    s={f['service'],*(f.get('also_accept') or [])}
    inj=json.load(open(f"{R}/data/cases/{case}/injection.json"))
    if f['chaos_type'] in NET:
        for e in [x for x in (inj.get('engine_config_summary') or (inj.get('engine_config') if isinstance(inj.get('engine_config'),list) else [])) if isinstance(x,dict)]:
            if e.get('app')==f['service'] and e.get('chaos_type')==f['chaos_type'] and e.get('target_service'): s.add(e['target_service'])
    return sorted(s)
hy=sorted([x for x in man.values() if x['n_required_faults']==2],key=lambda x:(x['n_service_edges'],x['name']))
plan=[]
for i,x in enumerate(hy):
    lab=json.load(open(f"{R}/data/cases/{x['name']}/label.json"))
    req=sorted([f for f in lab['faults'] if f['role']=='required'],key=lambda f:f['index'])
    assert len(req)==2
    a=i%2
    A,B=req[a],req[1-a]
    fam=sorted(f"{f['service']}:{f['chaos_type']}" for f in req)
    plan.append(dict(fid=f"f{i+1:02d}",case=x['name'],system=x['system'],kind='hybrid',n_edges=x['n_service_edges'],A=A,B=B,acceptA=accept(x['name'],A),acceptB=accept(x['name'],B),family='|'.join(fam)))
# controls: same six single-fault cases as the pilot
old=json.load(open(R+'/results/plan.json'))
for j,p in enumerate([p for p in old if p['kind']=='control']):
    f=p['faultA']
    plan.append(dict(fid=f"k{j+1:02d}",case=p['case'],system=p['system'],kind='control',n_edges=p['n_edges'],A=f,B=None,acceptA=accept(p['case'],f),acceptB=None,family=f"{f['service']}:{f['chaos_type']}"))
json.dump(plan,open(R+'/results/plan_full.json','w'),indent=1)
for p in plan: print(p['fid'],p['system'],p['n_edges'],'A',p['A']['service'],p['A']['chaos_type'],p['acceptA'],'B',(p['B'] or {}).get('service'),(p['B'] or {}).get('chaos_type'),p['acceptB'])
