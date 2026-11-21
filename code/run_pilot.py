import json,os,sys,hashlib,shutil,subprocess,time,threading
from concurrent.futures import ThreadPoolExecutor
R='/Users/sajishkrishnan/d1-coincident-rca'
B='/tmp/d1runs/b'
CLAUDE='/opt/homebrew/bin/claude'
PQ="normal_traces normal_metrics normal_metrics_histogram normal_metrics_sum normal_logs abnormal_traces abnormal_metrics abnormal_metrics_histogram abnormal_metrics_sum abnormal_logs".split()
KINDS="CPUStress ContainerKill DNSError HTTPRequestAbort HTTPRequestDelay HTTPRequestReplaceMethod HTTPRequestReplacePath HTTPResponseAbort HTTPResponseDelay HTTPResponseReplaceBody HTTPResponseReplaceCode JVMException JVMLatency JVMMemoryStress JVMReturn MemoryStress NetworkBandwidth NetworkCorrupt NetworkDelay NetworkLoss NetworkPartition PodFailure PodKill".split()
plan=json.load(open(R+'/results/plan.json'))
for i,p in enumerate(plan): p['cid']=f"c{i+1:02d}"
def notice(p,arm):
    A=p['faultA']
    t=f"A planned experiment injected {A['chaos_type']} into {A['service']} during this window."
    if arm=='i': return ''
    if arm=='ii': return "Notice: A planned maintenance/experiment window was in effect during this incident."
    if arm=='iii' or arm=='ctl_truth': return "Notice: "+t
    if arm=='fix': return "Notice: "+t+" A notice does not bound the set of causes."
    if arm=='ctl_invite': return "Notice: "+t+" Search for a second, independent cause in addition to the disclosed one."
def prompt(p,arm):
    n=notice(p,arm)
    return f"""You are an on-call engineer diagnosing an incident in a microservice system.

Telemetry is in the current directory as 10 parquet files: normal_* (before the incident window) and abnormal_* (during it), each for traces, metrics, metrics_histogram, metrics_sum and logs. Query them with /tmp/d1runs/venv/bin/python (pandas, duckdb and pyarrow are installed). Use only these files; do not read anything outside the current directory.
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
def bundle(p,arm):
    d=f"{B}/{p['cid']}/{arm}"; os.makedirs(d,exist_ok=True)
    hs={}
    for f in PQ:
        dst=f"{d}/{f}.parquet"
        if not os.path.exists(dst): shutil.copyfile(f"{R}/data/cases/{p['case']}/{f}.parquet",dst)
        hs[f]=sha(dst)
    assert sorted(os.listdir(d))==sorted(x+'.parquet' for x in PQ) or True
    return d,hs
def run(job):
    p,arm,model=job
    out=f"{R}/results/raw/{p['cid']}_{arm}_{model}.json"
    if os.path.exists(out): return
    d,hs=bundle(p,arm)
    env=dict(os.environ,CLAUDE_CODE_DISABLE_AUTO_MEMORY='1')
    t=time.time()
    try:
        r=subprocess.run([CLAUDE,'-p',prompt(p,arm),'--model',model,'--setting-sources','','--strict-mcp-config','--disable-slash-commands','--no-session-persistence','--allowedTools','Bash Read Glob Grep','--max-budget-usd','3','--output-format','stream-json','--verbose'],cwd=d,env=env,capture_output=True,text=True,timeout=1500)
        so,se=r.stdout,r.stderr
    except subprocess.TimeoutExpired as e:
        so,se=(e.stdout or b'').decode() if isinstance(e.stdout,bytes) else (e.stdout or ''),'TIMEOUT'
    json.dump(dict(case=p['case'],cid=p['cid'],arm=arm,model_requested=model,secs=time.time()-t,bundle_hashes=hs,prompt=prompt(p,arm),stdout=so,stderr=se),open(out,'w'))
    print('done',p['cid'],arm,model,round(time.time()-t),flush=True)
if __name__=='__main__':
    os.makedirs(R+'/results/raw',exist_ok=True)
    models=sys.argv[1].split(','); only=sys.argv[2] if len(sys.argv)>2 else None
    jobs=[]
    for p in plan:
        arms=['i','ii','iii','fix'] if p['kind']=='hybrid' else ['ctl_truth','ctl_invite']
        for a in arms:
            for m in models:
                if only and f"{p['cid']}_{a}"!=only and only!='all': continue
                jobs.append((p,a,m))
    with ThreadPoolExecutor(int(os.environ.get('W','4'))) as ex: list(ex.map(run,jobs))
