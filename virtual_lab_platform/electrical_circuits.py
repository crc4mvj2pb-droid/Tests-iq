"""Educational DC resistor-network solver using nodal analysis.

Supports ideal DC voltage source between node 'source' and ground and a connected
network of positive resistors between named nodes. This is not an SPICE replacement.
"""
from __future__ import annotations
import math

class CircuitError(ValueError):
    pass

def _solve_linear(a, b):
    n = len(b)
    m = [list(map(float, row)) + [float(bi)] for row, bi in zip(a, b)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-14:
            raise CircuitError("Circuit matrix is singular. Check for floating nodes or an invalid topology.")
        m[col], m[pivot] = m[pivot], m[col]
        p = m[col][col]
        for j in range(col, n + 1): m[col][j] /= p
        for r in range(n):
            if r == col: continue
            factor = m[r][col]
            if factor:
                for j in range(col, n + 1): m[r][j] -= factor * m[col][j]
    return [m[i][n] for i in range(n)]

def solve_dc_circuit(request: dict) -> dict:
    """Solve a resistor network, report node voltages, branch currents and power.

    Request: {source_voltage: 9, ground: '0', source_node: 'S', resistors:[
      {id:'R1', a:'S', b:'N1', resistance_ohm:1000}, ...]}
    Source node is fixed at source_voltage; ground node fixed at 0 V.
    """
    try: voltage = float(request.get("source_voltage", 9.0))
    except (TypeError, ValueError): raise CircuitError("Source voltage must be a finite number.")
    if not math.isfinite(voltage) or abs(voltage) > 1e6: raise CircuitError("Source voltage must be finite and within ±1,000,000 V.")
    resistors = request.get("resistors")
    if not isinstance(resistors, list) or not resistors or len(resistors) > 200:
        raise CircuitError("Provide between 1 and 200 resistors.")
    ground = str(request.get("ground", "0")); source = str(request.get("source_node", "S"))
    if ground == source: raise CircuitError("Source node and ground must be different.")
    parsed=[]; nodes={ground,source}; ids=set()
    for i, r in enumerate(resistors):
        if not isinstance(r, dict): raise CircuitError(f"Resistor {i+1} is invalid.")
        rid=str(r.get("id",f"R{i+1}")); a=str(r.get("a","")); b=str(r.get("b",""))
        try: ohms=float(r.get("resistance_ohm"))
        except (TypeError,ValueError): raise CircuitError(f"{rid}: resistance must be numeric.")
        if not rid or rid in ids: raise CircuitError("Resistor IDs must be unique.")
        if not a or not b or a==b: raise CircuitError(f"{rid}: endpoints must be distinct named nodes.")
        if not math.isfinite(ohms) or ohms <= 0 or ohms > 1e15: raise CircuitError(f"{rid}: resistance must be finite and > 0 Ω.")
        ids.add(rid); nodes.update((a,b)); parsed.append({"id":rid,"display_name":str(r.get("display_name", rid)),"a":a,"b":b,"resistance_ohm":ohms})
    unknown=sorted(nodes-{ground,source}); index={n:i for i,n in enumerate(unknown)}
    gmat=[[0.0 for _ in unknown] for _ in unknown]; rhs=[0.0 for _ in unknown]
    for r in parsed:
        g=1.0/r["resistance_ohm"]; a,b=r["a"],r["b"]
        if a in index: gmat[index[a]][index[a]] += g
        if b in index: gmat[index[b]][index[b]] += g
        if a in index and b in index:
            gmat[index[a]][index[b]] -= g; gmat[index[b]][index[a]] -= g
        elif a in index and b==source: rhs[index[a]] += g*voltage
        elif b in index and a==source: rhs[index[b]] += g*voltage
    # Ground has 0 V and source is ideal at fixed voltage.
    values=_solve_linear(gmat,rhs) if unknown else []
    node_v={ground:0.0,source:voltage}; node_v.update({n:values[i] for n,i in index.items()})
    branches=[]; source_current=0.0; total_power=0.0
    for r in parsed:
        drop=node_v[r["a"]]-node_v[r["b"]]
        current=drop/r["resistance_ohm"]
        power=drop*current
        total_power+=power
        if r["a"]==source: source_current += current
        if r["b"]==source: source_current -= current
        branches.append({**r,"voltage_v":drop,"current_a":current,"power_w":power})
    # KCL check at internal nodes and power balance check.
    kcl={n:0.0 for n in unknown}
    for r in branches:
        if r["a"] in kcl:kcl[r["a"]]+=r["current_a"]
        if r["b"] in kcl:kcl[r["b"]]-=r["current_a"]
    max_kcl=max((abs(v) for v in kcl.values()),default=0.0)
    supplied=voltage*source_current
    return {"model":"ideal_dc_resistive_nodal_analysis","status":"computed","source_voltage_v":voltage,
      "source_current_a":source_current,"equivalent_resistance_ohm":(abs(voltage/source_current) if abs(source_current)>1e-15 else None),
      "source_power_supplied_w":supplied,"total_resistor_power_w":total_power,"power_balance_error_w":supplied-total_power,
      "node_voltages_v":node_v,"branches":branches,"checks":{"max_internal_kcl_residual_a":max_kcl,
      "power_balance_error_w":supplied-total_power,"numerically_consistent":max_kcl<1e-8 and abs(supplied-total_power)<1e-7*max(1.0,abs(total_power))},
      "assumptions":["DC steady state","ideal voltage source","ideal wires and meters","linear ohmic resistors at the entered resistance","no parasitic inductance/capacitance or temperature dependence"],
      "limitations":["Not a SPICE transient/nonlinear solver; diodes, transistors, AC, inductors and capacitors are not implemented in this circuit engine.","Use component data sheets and independent verification before using results for real hardware."]}
