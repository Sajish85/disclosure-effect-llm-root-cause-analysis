import json,glob,re,csv,os,random,sys,math,collections
R='/Users/sajishkrishnan/d1-coincident-rca'
IN=os.environ.get('IN',R+'/results/full'); OUTD=os.environ.get('ANA',R+'/results')
plan={p['fid']:p for p in json.load(open(R+'/results/plan_full.json'))}
# ERRATA E3 overlay (topup-v2): plan_full.json is hashed and untouched; add display_config.injection_point.target_service to accept(A) for k05/k06
OVERLAY={'k05':['ts-train-service'],'k06':['ts-order-other-service']}
for _f,_a in OVERLAY.items(): plan[_f]['acceptA']=list(plan[_f]['acceptA'])+_a
KEY=re.compile(r'label\.json|causal_graph|injection\.json|env\.json|data/cases|data/raw|d1-coincident|manifest\.jsonl|ops-lite|huggingface|plan_full|ANALYSIS-PLAN|BRIEF|VETTING|ADDENDUM|(?<!tool-)results/|\.codex|pilot-vetting',re.I)
PATH=re.compile(r"(/tmp/[^\s\"'`;|)<>]*|/Users/[^\s\"'`;|)<>]*|~/[^\s\"'`;|)<>]*|/private/[^\s\"'`;|)<>]*)")
def events(so):
    L=[]
    for l in so.splitlines():
        try:L.append(json.loads(l))
        except: pass
    return L
def parse(d):
    L=events(d['stdout']); cmds=[]; txt=''; tok=dict(inp=0,out=0,cached=0); model=''
    if d['kind']=='claude':
        res=[x for x in L if x.get('type')=='result']; res=res[-1] if res else {}
        txt=res.get('result','') or ''
        for x in L:
            if x.get('type')=='assistant':
                for c in x['message']['content']:
                    if c.get('type')=='tool_use': cmds.append(json.dumps(c['input']))
        mu=list(res.get('modelUsage',{})); model=';'.join(mu)
        u=res.get('usage',{}); tok=dict(inp=u.get('input_tokens',0),out=u.get('output_tokens',0),cached=u.get('cache_read_input_tokens',0))
        err=res.get('is_error',True) if res else True
    else:
        msgs=[x['item']['text'] for x in L if x.get('type')=='item.completed' and x['item'].get('type')=='agent_message']
        txt=msgs[-1] if msgs else ''
        cmds=[x['item'].get('command','') for x in L if x.get('type')=='item.completed' and x['item'].get('type')=='command_execution']
        for x in L:
            if x.get('type')=='turn.completed':
                u=x.get('usage',{}); tok['inp']+=u.get('input_tokens',0); tok['out']+=u.get('output_tokens',0); tok['cached']+=u.get('cached_input_tokens',0)
        model=d.get('model_requested') or ''; err=(not bool(txt)) or any(x.get('type')=='turn.failed' for x in L) or not any(x.get('type')=='turn.completed' for x in L)  # topup-v2 fix: turn.failed or no turn.completed = failure
    m=re.findall(r'```json\s*(\{.*?\})\s*```',txt,re.S); ans=None
    if m:
        try: ans=json.loads(m[-1])['root_causes']
        except Exception: ans=None
    return ans,cmds,tok,model,err
rows=[];ident=collections.defaultdict(set)
for f in sorted(glob.glob(IN+'/*.json')):
    d=json.load(open(f)); p=plan[d['fid']]
    ans,cmds,tok,model,err=parse(d)
    named=[((r.get('service') or '').strip().lower(),r.get('fault_kind','')) for r in (ans or []) if isinstance(r,dict)]
    aA=set(x.lower() for x in p['acceptA']); aB=set(x.lower() for x in p['acceptB']) if p['B'] else set()
    A=p['A'];B=p['B']
    overlap=bool(aA&aB)
    def hit(acc,F,strict):
        for s,k in named:
            if s in acc and (not (strict or overlap) or k==F['chaos_type']): return 1
        return 0
    ok=ans is not None
    spurious=sum(1 for s,k in named if s not in (aA|aB)) if ok else ''
    leak_key=[];outside=[]
    for c in cmds:
        if KEY.search(c): leak_key.append(c[:150])
        for pth in PATH.findall(c):
            pth=pth[len('/private'):] if pth.startswith('/private/tmp') else pth
            if pth.startswith(d['rundir']) or pth.startswith('/tmp/d1runs/venv') or '/.claude/projects/' in pth or '/tool-results/' in pth: continue
            outside.append(pth[:100])
    ident[p['case']].add((json.dumps(d['pre_hash'],sort_keys=True)))
    rows.append(dict(rid=d['rid'],fid=d['fid'],system=p['system'],kind=p['kind'],arm=d['arm'],diag=d['diag'],rep=d['rep'],model=model,parsed=int(ok),
      named=' | '.join(f'{s}:{k}' for s,k in named),n_named=len(named),
      hitA=hit(aA,A,False) if ok else '',hitB=(hit(aB,B,False) if B else '') if ok else '',hitB_strict=(hit(aB,B,True) if B else '') if ok else '',
      spurious=spurious,tools=len(cmds),tok_in=tok['inp'],tok_out=tok['out'],tok_cached=tok['cached'],cost_usd=d.get('cost_usd',0) or 0,secs=round(d['secs']),
      pre_eq_src=int(d['pre_eq_src']),post_eq_pre=int(d['post_eq_pre']),extra_files=len(d['extra_files']),leak_key=len(leak_key),outside_paths=len(set(outside)),outside_examples=' ; '.join(sorted(set(outside))[:3]),started=d.get('started',0),err=int(bool(err))))
if not rows: print('no rows'); sys.exit()
with open(OUTD+'/per_run_full.csv','w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# run validity
def valid(r): return r['pre_eq_src'] and r['post_eq_pre'] and not r['leak_key']
# identity per case
with open(OUTD+'/bundle_identity_full.csv','w',newline='') as fh:
    w=csv.writer(fh);w.writerow(['fid','case','runs','distinct_pre_hash_sets','all_pre_eq_source','all_post_eq_pre'])
    for fid,p in plan.items():
        rr=[r for r in rows if r['fid']==fid]
        if rr: w.writerow([fid,p['case'],len(rr),len(ident[p['case']]),all(r['pre_eq_src'] for r in rr),all(r['post_eq_pre'] for r in rr)])
# ---- statistics
def vals(diag,fid,arm,reps,key='hitB'):
    return [r[key] for r in rows if r['diag']==diag and r['fid']==fid and r['arm']==arm and r['rep'] in reps and r['parsed'] and valid(r)]
AN=('r1','r2','r3')
def atrisk(diag):
    out={};
    for fid,p in plan.items():
        if p['kind']!='hybrid': continue
        s=vals(diag,fid,'i',('s1','s2'))
        out[fid]=(sum(s) if len(s)>0 else None,len(s))
    return out
def boot(diag,armX,armY,cases,key='hitB',n=10000,seed=0,family=False):
    rnd=random.Random(seed)
    data={c:(vals(diag,c,armX,AN,key),vals(diag,c,armY,AN,key)) for c in cases}
    data={c:v for c,v in data.items() if v[0] and v[1]}
    cs=list(data)
    if not cs: return None
    def mean(x): return sum(x)/len(x)
    pt=mean([mean(data[c][0])-mean(data[c][1]) for c in cs])
    fam=collections.defaultdict(list)
    for c in cs: fam[plan[c]['family']].append(c)
    fl=list(fam)
    ds=[]
    for _ in range(n):
        if family: pick=[c for f in (rnd.choice(fl) for _ in fl) for c in fam[f]]
        else: pick=[rnd.choice(cs) for _ in cs]
        per=[]
        for c in pick:
            x,y=data[c]
            xm=mean([rnd.choice(x) for _ in x]); ym=mean([rnd.choice(y) for _ in y]); per.append(xm-ym)
        ds.append(mean(per))
    ds.sort()
    return dict(n_cases=len(cs),mean=round(pt,4),lo=round(ds[int(.025*n)],4),hi=round(ds[int(.975*n)-1],4),up=sum(1 for c in cs if mean(data[c][0])>mean(data[c][1])),down=sum(1 for c in cs if mean(data[c][0])<mean(data[c][1])),same=sum(1 for c in cs if mean(data[c][0])==mean(data[c][1])))
def wilson(k,n,z=1.96):
    if n==0: return (None,None)
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return (round((c-h)/d,3),round((c+h)/d,3))
summ={}; diags=sorted({r['diag'] for r in rows})
hyb=[fid for fid,p in plan.items() if p['kind']=='hybrid']
for dg in diags:
    ar=atrisk(dg); AR=[c for c,(k,n) in ar.items() if k and k>=1]; FL=[c for c,(k,n) in ar.items() if k==0 and n>0]
    summ[f'{dg}|screen']=dict(at_risk=AR,floor=FL,screen_hits={c:ar[c] for c in ar})
    for nm,(x,y) in {'iii_vs_i':('iii','i'),'ii_vs_i':('ii','i'),'fix_vs_iii':('fix','iii'),'fix_vs_i':('fix','i')}.items():
        for stratum,cs in [('at_risk',AR),('all',hyb),('floor',FL)]:
            for key in ['hitB','hitB_strict']:
                if nm!='iii_vs_i' and key=='hitB_strict': continue
                summ[f'{dg}|{nm}|{stratum}|{key}']=boot(x_dg:=dg,x,y,cs,key)
    summ[f'{dg}|PRIMARY_iii_vs_i_at_risk_family']=boot(dg,'iii','i',AR,'hitB',family=True)
    for arm in ['i','ii','iii','fix']:
        rr=[r for r in rows if r['diag']==dg and r['kind']=='hybrid' and r['arm']==arm and r['rep'] in AN and valid(r)]
        pr=[r for r in rr if r['parsed']]
        summ[f'{dg}|rate|{arm}']=dict(runs=len(rr),parsed=len(pr),hitB=sum(r['hitB'] for r in pr),hitA=sum(r['hitA'] for r in pr),spurious_runs=sum(1 for r in pr if r['spurious']>0),mean_tools=round(sum(r['tools'] for r in rr)/len(rr),2) if rr else None,
            mean_tools_cost=round(sum(r['cost_usd'] for r in rr),3))
    for arm in ['ctl_truth','ctl_invite']:
        pr=[r for r in rows if r['diag']==dg and r['kind']=='control' and r['arm']==arm and r['parsed'] and valid(r)]
        k=sum(1 for r in pr if r['spurious']>0)
        summ[f'{dg}|ctl|{arm}']=dict(n=len(pr),spurious_runs=k,wilson=wilson(k,len(pr)),disclosed_named=sum(r['hitA'] for r in pr))
# conditioning table: arm-i recall of B and A per case & diag
with open(OUTD+'/arm_i_conditioning.csv','w',newline='') as fh:
    w=csv.writer(fh);w.writerow(['fid','system','A','B','diag','screen_B_hits','screen_n','i_B_hits','i_n','i_A_hits','iii_B_hits','iii_n','ii_B_hits','fix_B_hits'])
    for fid in hyb:
        p=plan[fid]
        for dg in diags:
            s=vals(dg,fid,'i',('s1','s2')); a=vals(dg,fid,'i',AN); aa=vals(dg,fid,'i',AN,'hitA'); i3=vals(dg,fid,'iii',AN); i2=vals(dg,fid,'ii',AN); fx=vals(dg,fid,'fix',AN)
            w.writerow([fid,p['system'],p['A']['service']+':'+p['A']['chaos_type'],p['B']['service']+':'+p['B']['chaos_type'],dg,sum(s),len(s),sum(a),len(a),sum(aa),sum(i3),len(i3),sum(i2),sum(fx)])
# cost ledger
led=collections.OrderedDict()
for r in sorted(rows,key=lambda r:r['started']): led.setdefault(r['diag'],[]).append(r)
summ['_meta']=dict(runs=len(rows),parsed=sum(r['parsed'] for r in rows),invalid=sum(1 for r in rows if not valid(r)),leak_key_runs=sum(1 for r in rows if r['leak_key']),outside_path_runs=sum(1 for r in rows if r['outside_paths']),
   extra_file_runs=sum(1 for r in rows if r['extra_files']),claude_cost_usd=round(sum(r['cost_usd'] for r in rows if r['diag'] in ('S','O')),2),cost_by_diag={k:round(sum(x['cost_usd'] for x in v),2) for k,v in led.items()},
   codex_tokens=dict(inp=sum(r['tok_in'] for r in rows if r['diag']=='X'),out=sum(r['tok_out'] for r in rows if r['diag']=='X'),cached=sum(r['tok_cached'] for r in rows if r['diag']=='X')),runs_by_diag=dict(collections.Counter(r['diag'] for r in rows)))
json.dump(summ,open(OUTD+'/summary_full.json','w'),indent=1,default=str)
print(json.dumps(summ['_meta'],indent=1))
