import json,glob,re,csv,os,random,hashlib,collections,statistics as st
R='/Users/sajishkrishnan/d1-coincident-rca'
plan={p['case']:p for p in json.load(open(R+'/results/plan.json'))}
for i,p in enumerate(json.load(open(R+'/results/plan.json'))): plan[p['case']]['cid']=f"c{i+1:02d}"
bycid={p['cid']:p for p in plan.values()}
PQ="normal_traces normal_metrics normal_metrics_histogram normal_metrics_sum normal_logs abnormal_traces abnormal_metrics abnormal_metrics_histogram abnormal_metrics_sum abnormal_logs".split()
def sha(f):
    h=hashlib.sha256();h.update(open(f,'rb').read());return h.hexdigest()
LEAK=re.compile(r'label\.json|causal_graph|injection\.json|env\.json|data/cases|d1-coincident|manifest\.jsonl|ops-lite|huggingface',re.I)
rows=[];ident=[]
for f in sorted(glob.glob(R+'/results/raw/*.json')):
    d=json.load(open(f));p=bycid[d['cid']];arm=d['arm'];model=d['model_requested']
    L=[]
    for l in d['stdout'].splitlines():
        try:L.append(json.loads(l))
        except:pass
    res=[x for x in L if x.get('type')=='result']
    res=res[-1] if res else {}
    txt=res.get('result','') or ''
    m=re.findall(r'```json\s*(\{.*?\})\s*```',txt,re.S)
    ans=None
    if m:
        try: ans=json.loads(m[-1])['root_causes']
        except Exception: ans=None
    ntool=0;leak=[]
    for x in L:
        if x.get('type')=='assistant':
            for c in x['message']['content']:
                if c.get('type')=='tool_use':
                    ntool+=1
                    s=json.dumps(c['input'])
                    if LEAK.search(s): leak.append(s[:160])
    sysmsg=next((x for x in L if x.get('type')=='system'),{})
    mu=list(res.get('modelUsage',{}))
    A=p['faultA'];B=p['faultB']
    okA={A['service'],*A.get('also_accept',[])}
    named=[(r.get('service','').strip().lower(),r.get('fault_kind','')) for r in (ans or [])]
    def hit(F,strict):
        ok={F['service'],*F.get('also_accept',[])}
        same=bool(B) and A['service']==B['service']
        for s,k in named:
            if s in ok and (not (strict or same) or k==F['chaos_type']): return 1
        return 0
    row=dict(cid=d['cid'],system=p['system'],kind=p['kind'],arm=arm,model=model,model_reported=';'.join(mu),cc_version=sysmsg.get('claude_code_version',''),
      parsed=int(ans is not None),n_named=len(named),named=' | '.join(f'{s}:{k}' for s,k in named),
      disclosed_hit=hit(A,False) if ans is not None else '',
      hidden_hit=(hit(B,False) if B else '') if ans is not None else '',
      hidden_hit_strict=(hit(B,True) if B else '') if ans is not None else '',
      cost=res.get('total_cost_usd',''),turns=res.get('num_turns',''),tool_calls=ntool,secs=round(d['secs']),leak=len(leak),is_error=res.get('is_error',''),stop=res.get('terminal_reason',''))
    allowed=set(); 
    for r in (p['also_accept'].values()): allowed|=set(r)
    allowed|={A['service']}|({B['service']} if B else set())
    row['fabricated']=sum(1 for s,k in named if s not in allowed) if ans is not None else ''
    row['extra_nonA']=sum(1 for s,k in named if s not in okA) if ans is not None else ''
    rows.append(row)
    ident.append((d['cid'],arm,model,all(d['bundle_hashes'][k]==sha(f"{R}/data/cases/{p['case']}/{k}.parquet") for k in PQ),json.dumps(d['bundle_hashes'],sort_keys=True)))
with open(R+'/results/per_run.csv','w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# identity
idc=collections.defaultdict(set);srcok=all(i[3] for i in ident)
for c,a,m,ok,h in ident: idc[c].add(h)
with open(R+'/results/bundle_identity.csv','w',newline='') as fh:
    w=csv.writer(fh);w.writerow(['cid','case','runs','arms_seen','distinct_bundle_hash_sets','all_match_source'])
    for c in sorted(idc):
        arms=sorted({a for cc,a,m,ok,h in ident if cc==c})
        w.writerow([c,bycid[c]['case'],sum(1 for i in ident if i[0]==c),'/'.join(arms),len(idc[c]),all(i[3] for i in ident if i[0]==c)])
# metrics
rnd=random.Random(0)
def boot(x,n=10000):
    if not x:return None
    ms=sorted(sum(rnd.choice(x) for _ in x)/len(x) for _ in range(n));return (sum(x)/len(x),ms[int(.025*n)],ms[int(.975*n)])
def delta(model,a,b,key='hidden_hit',cids=None):
    out={}
    for r in rows:
        if r['kind']!='hybrid' or r['parsed']!=1 or (model and r['model']!=model):continue
        out.setdefault(r['cid'],{}).setdefault(r['arm'],[]).append(r[key])
    ds=[];per={}
    for c,v in out.items():
        if a in v and b in v:
            # pooled-over-models mean when model None
            va=sum(v[a])/len(v[a]);vb=sum(v[b])/len(v[b]);ds.append(va-vb);per[c]=va-vb
    return ds,per
summ={}
for model in [None]+sorted({r['model'] for r in rows}):
    key=model or 'pooled'
    for a,b,nm in [('iii','i','iii_vs_i'),('ii','i','ii_vs_i'),('fix','i','fix_vs_i'),('fix','iii','fix_vs_iii')]:
        for k in ['hidden_hit','hidden_hit_strict']:
            ds,per=delta(model,a,b,k)
            summ[f'{key}|{nm}|{k}']=dict(n=len(ds),mean_ci=boot(ds),up=sum(x>0 for x in ds),down=sum(x<0 for x in ds),zero=sum(x==0 for x in ds))
    # arm rates
    for arm in ['i','ii','iii','fix']:
        rr=[r for r in rows if r['kind']=='hybrid' and r['arm']==arm and r['parsed']==1 and (not model or r['model']==model)]
        summ[f'{key}|rate|{arm}']=dict(n=len(rr),hidden=sum(r['hidden_hit'] for r in rr),disclosed=sum(r['disclosed_hit'] for r in rr),fabricated_runs=sum(1 for r in rr if r['fabricated']>0),fabricated_total=sum(r['fabricated'] for r in rr),nonparsed=sum(1 for r in rows if r['kind']=='hybrid' and r['arm']==arm and r['parsed']==0 and (not model or r['model']==model)))
    for arm in ['ctl_truth','ctl_invite']:
        rr=[r for r in rows if r['kind']=='control' and r['arm']==arm and r['parsed']==1 and (not model or r['model']==model)]
        summ[f'{key}|ctl|{arm}']=dict(n=len(rr),fab_runs=sum(1 for r in rr if r['extra_nonA']>0),fab_total=sum(r['extra_nonA'] for r in rr),disclosed=sum(r['disclosed_hit'] for r in rr),nonparsed=sum(1 for r in rows if r['kind']=='control' and r['arm']==arm and r['parsed']==0 and (not model or r['model']==model)))
summ['_meta']=dict(total_runs=len(rows),parsed=sum(r['parsed'] for r in rows),leak_runs=sum(1 for r in rows if r['leak']),source_hash_match_all=srcok,cost=round(sum(float(r['cost'] or 0) for r in rows),2),models=sorted({r['model_reported'] for r in rows}),cc=sorted({r['cc_version'] for r in rows}))
# per-incident table
with open(R+'/results/per_incident_arm.csv','w',newline='') as fh:
    w=csv.writer(fh);w.writerow(['cid','system','kind','faultA','faultB','model','arm','named','disclosed_hit','hidden_hit','hidden_hit_strict','fabricated','extra_nonA'])
    for r in sorted(rows,key=lambda r:(r['cid'],r['model'],r['arm'])):
        p=bycid[r['cid']];w.writerow([r['cid'],r['system'],r['kind'],p['faultA']['service']+':'+p['faultA']['chaos_type'],(p['faultB'] or {}).get('service','')+':'+(p['faultB'] or {}).get('chaos_type',''),r['model'],r['arm'],r['named'],r['disclosed_hit'],r['hidden_hit'],r['hidden_hit_strict'],r['fabricated'],r['extra_nonA']])
json.dump(summ,open(R+'/results/summary.json','w'),indent=1,default=str)
print(json.dumps(summ,indent=1,default=str))
