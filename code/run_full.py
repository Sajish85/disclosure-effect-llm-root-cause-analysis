import json,os,sys,hashlib,shutil,subprocess,time,threading,uuid
from concurrent.futures import ThreadPoolExecutor
R='/Users/sajishkrishnan/d1-coincident-rca'
B='/tmp/d1full'
CLAUDE='/opt/homebrew/bin/claude'
CODEX='/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex'
PY='/tmp/d1runs/venv/bin/python'
PQ="normal_traces normal_metrics normal_metrics_histogram normal_metrics_sum normal_logs abnormal_traces abnormal_metrics abnormal_metrics_histogram abnormal_metrics_sum abnormal_logs".split()
KINDS="CPUStress ContainerKill DNSError HTTPRequestAbort HTTPRequestDelay HTTPRequestReplaceMethod HTTPRequestReplacePath HTTPResponseAbort HTTPResponseDelay HTTPResponseReplaceBody HTTPResponseReplaceCode JVMException JVMLatency JVMMemoryStress JVMReturn MemoryStress NetworkBandwidth NetworkCorrupt NetworkDelay NetworkLoss NetworkPartition PodFailure PodKill".split()
DIAG={'S':('claude','claude-sonnet-5-5'),'O':('claude','claude-opus-5-5'),'X':('codex','gpt-6.2-sol')}
plan={p['fid']:p for p in json.load(open(R+'/results/plan_full.json'))}
CAP_STOP=float(os.environ.get('CAP_STOP','115'))
cost_lock=threading.Lock()
def ledger_total():
    t=0.0
    for f in os.listdir(OUT):
        if f.endswith('.json'):
            try: t+=json.load(open(f"{OUT}/{f}")).get('cost_usd',0) or 0
            except Exception: pass
    return t
def notice(p,arm):
    A=p['A']; t=f"A planned experiment injected {A['chaos_type']} into {A['service']} during this window."
    return {'i':'','ii':"Notice: A planned maintenance/experiment window was in effect during this incident.",'iii':"Notice: "+t,'ctl_truth':"Notice: "+t,
      'fix':"Notice: "+t+" A notice does not bound the set of causes.",'ctl_invite':"Notice: "+t+" Search for a second, independent cause in addition to the disclosed one."}[arm]
def prompt(p,arm):
    n=notice(p,arm)
    return f"""You are an on-call engineer diagnosing an incident in a microservice system.

Telemetry is in the current directory as 10 parquet files: normal_* (before the incident window) and abnormal_* (during it), each for traces, metrics, metrics_histogram, metrics_sum and logs. Query them with {PY} (pandas, duckdb and pyarrow are installed). Use only these files; do not read anything outside the current directory.
{chr(10)+n+chr(10) if n else ''}
Find the root-cause service(s) and fault kind(s) for the incident. List as many root causes as the evidence supports, no more. Budget: at most 40 shell commands, then answer.

fault_kind must be one of: {', '.join(KINDS)}.

Finish with the answer as a single JSON block:
```json
{{"root_causes":[{{"service":"<service name as in the telemetry>","fault_kind":"<kind>","evidence":"<one line>"}}]}}
```"""
def sha(f):
    h=hashlib.sha256()
    with open(f,'rb') as fh:
        for b in iter(lambda:fh.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def src_hashes(case):
    return {f:sha(f"{R}/data/cases/{case}/{f}.parquet") for f in PQ}
_src={}
def codex_home():
    d=B+'/codexhome'
    if not os.path.exists(d+'/config.toml'):
        os.makedirs(d,exist_ok=True)
        open(d+'/config.toml','w').write('# minimal: no plugins, no MCP, no user instructions\n')
        if not os.path.lexists(d+'/auth.json'): os.symlink(os.path.expanduser('~/.codex/auth.json'),d+'/auth.json')
    return d
def run(job):
    fid,arm,dg,rep=job
    p=plan[fid]; kind,model=DIAG[dg]
    rid=f"{fid}_{arm}_{dg}_{rep}"
    out=f"{OUT}/{rid}.json"
    if os.path.exists(out): return
    if STOP.is_set(): return
    with cost_lock:
        if ledger_total()>=CAP_STOP:
            STOP.set(); print('COST STOP',flush=True); return
    if p['case'] not in _src: _src[p['case']]=src_hashes(p['case'])
    d=f"{B}/{rid}-{uuid.uuid4().hex[:6]}"; os.makedirs(d)
    for f in PQ: shutil.copyfile(f"{R}/data/cases/{p['case']}/{f}.parquet",f"{d}/{f}.parquet")
    pre={f:sha(f"{d}/{f}.parquet") for f in PQ}
    pr=prompt(p,arm); t=time.time(); so=se=''
    try:
        if kind=='claude':
            env=dict(os.environ,CLAUDE_CODE_DISABLE_AUTO_MEMORY='1')
            r=subprocess.run([CLAUDE,'-p',pr,'--model',model,'--setting-sources','','--strict-mcp-config','--disable-slash-commands','--no-session-persistence','--allowedTools','Bash Read Glob Grep','--max-budget-usd','3','--output-format','stream-json','--verbose'],cwd=d,env=env,capture_output=True,text=True,timeout=1500,stdin=subprocess.DEVNULL)
        else:
            env=dict(os.environ,CODEX_HOME=codex_home())
            r=subprocess.run([CODEX,'exec','--json','--skip-git-repo-check','--ephemeral','-m',model,'-s','workspace-write','-C',d,pr],cwd=d,env=env,capture_output=True,text=True,timeout=1500,stdin=subprocess.DEVNULL)
        so,se=r.stdout,r.stderr
    except subprocess.TimeoutExpired as e:
        so=(e.stdout.decode() if isinstance(e.stdout,bytes) else e.stdout) or ''; se='TIMEOUT'
    secs=time.time()-t
    post={f:sha(f"{d}/{f}.parquet") for f in PQ if os.path.exists(f"{d}/{f}.parquet")}
    extra=sorted(set(os.listdir(d))-{x+'.parquet' for x in PQ})
    cost=0.0
    if kind=='claude':
        for l in so.splitlines():
            try:
                x=json.loads(l)
                if x.get('type')=='result': cost=x.get('total_cost_usd',0) or 0
            except Exception: pass
    rec=dict(rid=rid,fid=fid,case=p['case'],arm=arm,diag=dg,rep=rep,kind=kind,model_requested=model,secs=secs,pre_hash=pre,post_hash=post,
      pre_eq_src=pre==_src[p['case']],post_eq_pre=post==pre,extra_files=extra,rundir=d,prompt=pr,stdout=so,stderr=se[-2000:],cost_usd=cost,started=t)
    json.dump(rec,open(out,'w'))
    shutil.rmtree(d,ignore_errors=True)
    print('done',rid,round(secs),round(cost,3),flush=True)
def jobs_for(rep_set,diags,fids=None):
    J=[]
    for fid,p in plan.items():
        if fids and fid not in fids: continue
        if p['kind']=='hybrid':
            for dg in diags:
                for arm in ['i','ii','iii','fix']:
                    for rep in rep_set:
                        if arm=='i' and rep in ('s1','s2','r1','r2','r3'): J.append((fid,arm,dg,rep))
                        elif arm!='i' and rep in ('r1','r2','r3'): J.append((fid,arm,dg,rep))
        else:
            for dg in diags:
                for arm in ['ctl_truth','ctl_invite']:
                    for rep in rep_set:
                        if rep in ('r1','r2','r3'): J.append((fid,arm,dg,rep))
    return J
if __name__=='__main__':
    OUT=os.environ.get('OUT',R+'/results/full'); os.makedirs(OUT,exist_ok=True); os.makedirs(B,exist_ok=True)
    STOP=threading.Event()
    reps=sys.argv[1].split(','); diags=sys.argv[2].split(','); fids=sys.argv[3].split(',') if len(sys.argv)>3 else None
    J=jobs_for(reps,diags,fids)
    print('jobs',len(J),flush=True)
    with ThreadPoolExecutor(int(os.environ.get('W','6'))) as ex: list(ex.map(run,J))
