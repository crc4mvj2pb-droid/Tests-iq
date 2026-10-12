import json, urllib.request, sys
U="http://127.0.0.1:8765"
def post(p, body, raw=False):
    data = body if raw else json.dumps(body).encode()
    req = urllib.request.Request(U+p, data=data, method="POST", headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
S=lambda i,v=9:{"instanceId":i,"id":"dc-source","displayName":i,"qty":v}
R=lambda i,v:{"instanceId":i,"id":"resistor","displayName":i,"qty":v}
G=lambda i="g":{"instanceId":i,"id":"ground","displayName":"GND","qty":1}
W=lambda a,pa,b,pb:{"a":a,"pinA":pa,"b":b,"pinB":pb}
base=[W("s","N","g","GND")]
cases={
 "series 1k+2k (expect 3 mA)": ([S("s"),R("r1",1000),R("r2",2000),G()], base+[W("s","P","r1","A"),W("r1","B","r2","A"),W("r2","B","g","GND")]),
 "parallel 1k||1k (expect 18 mA, Req 500)": ([S("s"),R("r1",1000),R("r2",1000),G()], base+[W("s","P","r1","A"),W("s","P","r2","A"),W("r1","B","g","GND"),W("r2","B","g","GND")]),
 "source shorted": ([S("s"),R("r1",1000),G()], base+[W("s","P","g","GND"),W("r1","A","s","P"),W("r1","B","g","GND")]),
 "resistor bypassed by wire": ([S("s"),R("r1",1000),R("r2",1000),G()], base+[W("s","P","r1","A"),W("r1","B","r2","A"),W("r2","B","g","GND"),W("r1","A","r1x","B")]),
 "isolated resistor loop (floating)": ([S("s"),R("r1",1000),R("r2",50),R("r3",50),G()], base+[W("s","P","r1","A"),W("r1","B","g","GND"),W("r2","A","r3","A"),W("r2","B","r3","B")]),
 "open circuit (R unwired pin)": ([S("s"),R("r1",1000),G()], base+[W("s","P","r1","A")]),
 "high R 1e14 ohm (valid circuit)": ([S("s"),R("r1",1e14),G()], base+[W("s","P","r1","A"),W("r1","B","g","GND")]),
 "R=0": ([S("s"),R("r1",0),G()], base+[W("s","P","r1","A"),W("r1","B","g","GND")]),
 "R='1k' string": ([S("s"),R("r1","1k"),G()], base+[W("s","P","r1","A"),W("r1","B","g","GND")]),
 "R=true (bool)": ([S("s"),R("r1",True),G()], base+[W("s","P","r1","A"),W("r1","B","g","GND")]),
 "V='Infinity'": ([S("s","Infinity"),R("r1",1000),G()], base+[W("s","P","r1","A"),W("r1","B","g","GND")]),
 "no ground wire to source -": ([S("s"),R("r1",1000),G()], [W("s","P","r1","A"),W("r1","B","g","GND"),W("s","N","r1","B")]),
 "two sources": ([S("s"),S("s2"),R("r1",1000),G()], base+[W("s","P","r1","A"),W("r1","B","g","GND")]),
 "connected capacitor": ([S("s"),R("r1",1000),{"instanceId":"c","id":"capacitor","displayName":"C","qty":1e-6},G()], base+[W("s","P","r1","A"),W("r1","B","g","GND"),W("c","A","s","P")]),
 "unconnected LED present (silently ignored?)": ([S("s"),R("r1",1000),{"instanceId":"l","id":"led","displayName":"LED","qty":1},G()], base+[W("s","P","r1","A"),W("r1","B","g","GND")]),
 "wire to non-existent component": ([S("s"),R("r1",1000),G()], base+[W("s","P","r1","A"),W("r1","B","zz","GND")]),
}
# fix typo case: bypass wire on same resistor uses a==b -> use explicit wire comp
cases["resistor bypassed by wire"]=([S("s"),R("r1",1000),R("r2",1000),G(),{"instanceId":"w","id":"wire","displayName":"wire","qty":1}], base+[W("s","P","r1","A"),W("r1","B","r2","A"),W("r2","B","g","GND"),W("w","A","r1","A"),W("w","B","r1","B")])
for name,(c,w) in cases.items():
    code,d=post("/api/electrical/workbench-solve",{"components":c,"connections":w})
    if code==200: print(f"[{code}] {name}: I={d['source_current_a']:.6g} A Req={d['equivalent_resistance_ohm']} nodes={d['node_voltages_v']}")
    else: print(f"[{code}] {name}: {d.get('error')}")
print("--- malformed bodies")
for name,body in {"JSON list":b"[1,2]","JSON string":b'"x"',"invalid json":b"{bad","NaN literal in qty":b'{"components":[{"instanceId":"s","id":"dc-source","qty":NaN}],"connections":[]}'}.items():
    print(name, post("/api/electrical/workbench-solve",body,raw=True))
print("--- /api/lab/run with UI-like minimal request")
print(post("/api/lab/run",{"name":"t","workflow_id":"solution_dilution","components":[],"equipment":[],"steps":[]}))
