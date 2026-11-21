import json,re,sys,csv,duckdb,glob,os
R='/Users/sajishkrishnan/d1-coincident-rca'
man=[json.loads(l) for l in open(R+'/data/raw/manifest.jsonl')]
cases=[x['name'] for x in man if x['n_required_faults']==2]
cases+= [p['case'] for p in json.load(open(R+'/results/plan.json')) if p['kind']=='control']
STRONG=re.compile(r'chaos[-_ ]?mesh|chaosmesh|chaos-daemon|chaosd|podchaos|networkchaos|stresschaos|jvmchaos|httpchaos|dnschaos|iochaos|timechaos|kernelchaos|chaos\.mesh|chaos-mesh\.org|litmus|chaosblade|toxiproxy|stress-ng|byteman|tcconfig|chaos[_ -]?experiment|fault[_ -]?inject|injected fault|inject[_-]?(fault|chaos|success)|\bchaos\b',re.I)
WEAK=re.compile(r'pod-?failure|pod-?kill|network-?(delay|partition|loss|corrupt|bandwidth)|memory-?stress|cpu-?stress|jvm-?(latency|exception|return)|dns-?error|container-?kill|http-?(request|response)-?(abort|delay)|\binjection\b|\binject(ed)?\b',re.I)
out=[]
for c in cases:
    d=f"{R}/data/cases/{c}"; s=0;w=0;ex=[];wex=[];nrows=0
    for f in ['normal_logs','abnormal_logs']:
        con=duckdb.connect()
        cols=[r[0] for r in con.execute(f"describe select * from '{d}/{f}.parquet'").fetchall() if r[1]=='VARCHAR']
        q=" || ' ' || ".join(f'coalesce("{x}",\'\')' for x in cols)
        rows=[(a,'') for (a,) in con.execute(f"select {q} from '{d}/{f}.parquet'").fetchall()]
        nrows+=len(rows)
        for m,t in rows:
            txt=(m or '')+' '+(t or '')
            if STRONG.search(txt):
                s+=1
                if len(ex)<3: ex.append(f+': '+STRONG.search(txt).group(0)+' | '+re.sub(r'\s+',' ',txt[max(0,STRONG.search(txt).start()-80):STRONG.search(txt).end()+80]))
            elif WEAK.search(txt):
                w+=1
                if len(wex)<2: wex.append(f+': '+WEAK.search(txt).group(0)+' | '+re.sub(r'\s+',' ',txt[max(0,WEAK.search(txt).start()-80):WEAK.search(txt).end()+80]))
    # traces: span names / attrs; metrics: metric names
    ts=0
    for f in ['normal_traces','abnormal_traces']:
        cc=duckdb.connect(); cols=[r[0] for r in cc.execute(f"describe select * from '{d}/{f}.parquet'").fetchall() if r[1]=='VARCHAR' and r[0] not in ('trace_id','span_id','parent_span_id')]; q=" || ' ' || ".join(f'coalesce("{x}",\'\')' for x in cols); r=[(a,'') for (a,) in cc.execute(f"select distinct {q} from '{d}/{f}.parquet'").fetchall()]
        ts+=sum(1 for a,b in r if STRONG.search((a or '')+' '+(b or '')))
    ms=0
    for f in ['normal_metrics','abnormal_metrics','normal_metrics_sum','abnormal_metrics_sum','normal_metrics_histogram','abnormal_metrics_histogram']:
        r=duckdb.connect().execute(f"select distinct metric,service_name from '{d}/{f}.parquet'").fetchall()
        ms+=sum(1 for a,b in r if STRONG.search((a or '')+' '+(b or '')))
    out.append(dict(case=c,log_rows=nrows,strong_log=s,weak_log=w,strong_trace=ts,strong_metric=ms,strong_examples=' || '.join(ex),weak_examples=' || '.join(wex)))
    print(c[-8:],nrows,s,w,ts,ms,flush=True)
with open(R+'/results/leakage_audit.csv','w',newline='') as fh:
    wr=csv.DictWriter(fh,fieldnames=list(out[0]));wr.writeheader();wr.writerows(out)
