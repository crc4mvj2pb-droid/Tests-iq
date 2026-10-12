import json, sys, urllib.request
sys.path.insert(0, sys.argv[1]); from lab_designer import CATALOG
wf=next(x for x in CATALOG['workflows'] if x['id']=='solution_dilution')
req={'name':'proto audit','workflow_id':'solution_dilution','discipline':wf['discipline'],'components':wf['required_components'][:],'equipment':wf['required_equipment'][:]+[g[0] for g in wf.get('required_equipment_options',[])],'protocol_steps':[{'id':'s1','action':'Prepare dilution','duration_s':0}],'parameters':{'stock_concentration_mM':10,'stock_volume_ml':0.5,'diluent_volume_ml':9.5}}
U="http://127.0.0.1:8765"
d=json.loads(urllib.request.urlopen(urllib.request.Request(U+"/api/protocol/run",data=json.dumps(req).encode(),method="POST")).read())
i=d["history_record"]["id"]; print("protocol saved id",i,"has configuration key:", "configuration" in d)
print("verify:", json.loads(urllib.request.urlopen(f"{U}/api/history/{i}/verify").read()))
