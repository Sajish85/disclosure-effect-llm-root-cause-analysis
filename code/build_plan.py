import json,hashlib,os,shutil,collections
R='/Users/sajishkrishnan/d1-coincident-rca'
man={json.loads(l)['name']:json.loads(l) for l in open(R+'/data/raw/manifest.jsonl')}
hy=sorted([x for x in man.values() if x['n_required_faults']==2],key=lambda x:(x['n_service_edges'],x['name']))
idx=[round(i*(len(hy)-1)/11) for i in range(12)]
assert len(set(idx))==12
sel=[hy[i] for i in idx]
def desc(edges,s):
    seen=set();st=[s]
    while st:
        a=st.pop()
        for u,v in edges:
            if u==a and v not in seen: seen.add(v);st.append(v)
    return seen
plan=[]
alt=0
for x in sel:
    lab=json.load(open(f"{R}/data/cases/{x['name']}/label.json"))
    req=[f for f in lab['faults'] if f['role']=='required']
    assert len(req)==2
    d=[len(desc(lab['service_edges'],f['service'])) for f in req]
    same=req[0]['chaos_type']==req[1]['chaos_type']
    if d[0]!=d[1] and not same: A=0 if d[0]>d[1] else 1; rule='prominent=more downstream services'
    else: A=alt%2; alt+=1; rule='rotated (either plausible)'
    plan.append(dict(case=x['name'],system=x['system'],kind='hybrid',n_edges=x['n_service_edges'],path=x['longest_service_path'],
      faultA=req[A],faultB=req[1-A],downstream=d,rule=rule,also_accept={f['service']:f.get('also_accept',[]) for f in req}))
ctl=[]
for s in ['hs','otel-demo','ts']:
    c=sorted([x for x in man.values() if x['n_injected_faults']==1 and x['system']==s],key=lambda x:x['name'])[:2]
    for x in c:
        lab=json.load(open(f"{R}/data/cases/{x['name']}/label.json"))
        f=lab['faults'][0]
        plan.append(dict(case=x['name'],system=s,kind='control',n_edges=x['n_service_edges'],path=x['longest_service_path'],faultA=f,faultB=None,also_accept={f['service']:f.get('also_accept',[])}))
json.dump(plan,open(R+'/results/plan.json','w'),indent=1)
for p in plan: print(p['kind'],p['system'],p['case'][-8:],p['n_edges'],p['path'],p['faultA']['service'],p['faultA']['chaos_type'],(p['faultB'] or {}).get('service'),p.get('rule',''))
