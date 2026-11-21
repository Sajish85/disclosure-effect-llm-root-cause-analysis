import json,sys
m=[json.loads(l) for l in open(sys.argv[1])]
hy=sorted([x for x in m if x['n_required_faults']==2],key=lambda x:x['name'])
print(len(hy))
ctl={}
for s in ['hs','otel-demo','ts']:
    c=sorted([x for x in m if x['n_injected_faults']==1 and x['system']==s],key=lambda x:x['name'])
    ctl[s]=c
json.dump({'hybrid':hy,'ctl':{k:v[:3] for k,v in ctl.items()}},open('cand.json','w'),indent=1)
