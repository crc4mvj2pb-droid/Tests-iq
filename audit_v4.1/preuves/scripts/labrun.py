import json, sys, urllib.request
sys.path.insert(0, sys.argv[1])
from lab_designer import CATALOG
wf=next(x for x in CATALOG['workflows'] if x['id']=='solution_dilution')
req={'name':'audit','workflow_id':'solution_dilution','discipline':wf['discipline'],'components':wf['required_components'][:],'equipment':wf['required_equipment'][:]+[g[0] for g in wf.get('required_equipment_options',[])],'steps':[{'action':'Prepare'}],'protocol_steps':[{'id':'s1','action':'Prepare dilution','duration_s':0}],'parameters':{'stock_concentration_mM':10,'stock_volume_ml':0.5,'diluent_volume_ml':9.5}}
r=urllib.request.Request("http://127.0.0.1:8765/api/lab/validate",data=json.dumps(req).encode(),method="POST")
print("validate:", json.loads(urllib.request.urlopen(r).read()).get("valid"))
r=urllib.request.Request("http://127.0.0.1:8765/api/protocol/validate",data=json.dumps(req).encode(),method="POST")
print("protocol valid:", json.loads(urllib.request.urlopen(r).read()).get("valid"))
r=urllib.request.Request("http://127.0.0.1:8765/api/lab/run",data=json.dumps(req).encode(),method="POST")
try: print(urllib.request.urlopen(r).status)
except urllib.error.HTTPError as e: print("lab/run ->", e.code, e.read().decode())
