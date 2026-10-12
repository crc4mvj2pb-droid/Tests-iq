import sqlite3, json, sys, urllib.request
db=sys.argv[1]; U="http://127.0.0.1:8765"
c=sqlite3.connect(db)
d=json.loads(c.execute("select dossier_json from experiments where id=1").fetchone()[0])
# 1) tamper results only
d["source_current_a"]=123.0; d["branches"][0]["current_a"]=123.0
c.execute("update experiments set dossier_json=? where id=1",(json.dumps(d),)); c.commit()
print("results tampered -> verify:", json.loads(urllib.request.urlopen(U+"/api/history/1/verify").read())["valid"])
# 2) tamper config AND recompute hash (same row)
sys.path.insert(0, sys.argv[2]); from experiment_lifecycle import configuration_hash
d["configuration"]["components"][1]["qty"]=2000; d["configuration_hash"]=configuration_hash(d["configuration"])
c.execute("update experiments set dossier_json=? where id=1",(json.dumps(d),)); c.commit()
print("config+hash rewritten -> verify:", json.loads(urllib.request.urlopen(U+"/api/history/1/verify").read())["valid"])
# 3) column hash vs dossier hash divergence
print("column hash still old:", c.execute("select configuration_hash from experiments where id=1").fetchone()[0][:16], "dossier:", d["configuration_hash"][:16])
# 4) tamper config without hash -> replay refused?
d["configuration"]["components"][1]["qty"]=3000
c.execute("update experiments set dossier_json=? where id=1",(json.dumps(d),)); c.commit()
r=urllib.request.Request(U+"/api/history/1/replay",data=b"{}",method="POST")
try: urllib.request.urlopen(r)
except urllib.error.HTTPError as e: print("config tampered -> replay:", e.code, json.loads(e.read())["error"])
