import sys, io, json, traceback
sys.path.insert(0, sys.argv[1])
import history, tempfile, pathlib
history.DB_PATH = pathlib.Path(tempfile.mkdtemp())/"h.sqlite3"
import app
from lab_designer import CATALOG
def call(path, body):
    h = app.Handler.__new__(app.Handler)
    raw = json.dumps(body).encode() if not isinstance(body, bytes) else body
    h.path = path; h.headers = {"Content-Length": str(len(raw))}; h.rfile = io.BytesIO(raw)
    out = {}
    h._send = lambda code, b, ct=None: out.update(code=code, body=b)
    # surface the swallowed exception
    orig = app.Handler.do_POST
    try:
        sys.settrace(None); orig(h)
    except Exception: traceback.print_exc()
    return out
# Patch: make the generic except re-raise by wrapping _send for 500
wf=next(x for x in CATALOG['workflows'] if x['id']=='solution_dilution')
req={'name':'audit','workflow_id':'solution_dilution','discipline':wf['discipline'],'components':wf['required_components'][:],'equipment':wf['required_equipment'][:]+[g[0] for g in wf.get('required_equipment_options',[])],'steps':[{'action':'Prepare'}],'protocol_steps':[{'id':'s1','action':'Prepare dilution','duration_s':0}],'parameters':{'stock_concentration_mM':10,'stock_volume_ml':0.5,'diluent_volume_ml':9.5}}
import builtins
_exc=[]
orig_send = app.Handler._send
def tracing_send(self, code, body, ct="application/json"):
    if code == 500: _exc.append(traceback.format_exc())
app.Handler._send = tracing_send
h = app.Handler.__new__(app.Handler); raw=json.dumps(req).encode()
h.path="/api/lab/run"; h.headers={"Content-Length":str(len(raw))}; h.rfile=io.BytesIO(raw); h.do_POST()
print(_exc[-1].strip().splitlines()[-3:] if _exc else "no 500")
_exc.clear()
for body in (b"[1,2]",):
    h = app.Handler.__new__(app.Handler); h.path="/api/electrical/workbench-solve"; h.headers={"Content-Length":str(len(body))}; h.rfile=io.BytesIO(body); h.do_POST()
    print("list body ->", _exc[-1].strip().splitlines()[-1] if _exc else "no 500")
