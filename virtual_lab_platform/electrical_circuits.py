"""Educational DC resistor-network solver using nodal analysis.

Supports ideal DC voltage source between node 'source' and ground and a connected
network of positive resistors between named nodes. This is not an SPICE replacement.
"""
from __future__ import annotations
import math
import sys
from fractions import Fraction

class CircuitError(ValueError):
    pass

# Relative pivot tolerance: a pivot this small compared with the largest conductance means a
# floating node or a numerically singular network, whatever the absolute resistance scale.
RELATIVE_PIVOT_TOLERANCE = 1e-13
# Error model for the checks: each node voltage carries the a-posteriori error estimated by
# iterative refinement (at least K·eps·|V|), so a branch current I = (Va − Vb)/R is uncertain by
# δI = (δVa + δVb + K·eps·|Va − Vb|)/R. K is a heuristic safety factor; KCL and power balance
# are checked against these propagated bounds instead of a fixed tolerance.
ROUNDING_SAFETY_FACTOR = 16
DISPLAY_RELATIVE_PRECISION = 1e-5  # results are displayed with 5 significant digits
CONVENTIONS = {
    "branch_current": "positive from terminal a to terminal b of each resistor (A → B on the workbench)",
    "branch_voltage": "V(a) − V(b)",
    "source_current": "positive when leaving the source's + terminal into the network",
    "power": "positive = dissipated by a resistor or supplied by the source",
    "reference": "ground node fixed at 0 V",
}


def _lu_factor(a):
    """LU factorization with partial pivoting; rejects (numerically) singular matrices."""
    n = len(a)
    lu = [list(map(float, row)) for row in a]
    perm = list(range(n))
    scale = max((abs(v) for row in lu for v in row), default=0.0)
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(lu[r][col]))
        if scale == 0.0 or abs(lu[pivot][col]) <= RELATIVE_PIVOT_TOLERANCE * scale:
            raise CircuitError("Circuit matrix is singular. Check for floating nodes or an invalid topology.")
        lu[col], lu[pivot] = lu[pivot], lu[col]; perm[col], perm[pivot] = perm[pivot], perm[col]
        for r in range(col + 1, n):
            factor = lu[r][col] / lu[col][col]
            lu[r][col] = factor
            if factor:
                row, prow = lu[r], lu[col]
                for j in range(col + 1, n): row[j] -= factor * prow[j]
    return lu, perm


def _lu_solve(lu, perm, b):
    n = len(b)
    y = [0.0] * n
    for i in range(n):
        y[i] = b[perm[i]] - math.fsum(lu[i][j] * y[j] for j in range(i))
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (y[i] - math.fsum(lu[i][j] * x[j] for j in range(i + 1, n))) / lu[i][i]
    return x


def _solve_refined(a, b, steps=4, exact=None):
    """Solve a·x = b with mixed-precision iterative refinement.

    `exact` optionally gives the system as exact rationals (rows of {column: Fraction}, rhs list).
    The factorization is done once in floating point; each residual is computed exactly, so
    the refined solution approaches the correctly rounded solution of the exact system as long
    as cond(a)·eps ≪ 1. Returns (x, a-posteriori error estimate per unknown): the last correction
    |δx|, floored at K·eps·|x| (ROUNDING_SAFETY_FACTOR).
    """
    lu, perm = _lu_factor(a)
    x = _lu_solve(lu, perm, b)
    if exact is None:
        rows = [{j: Fraction(v) for j, v in enumerate(row) if v} for row in a]
        rhs = [Fraction(v) for v in b]
    else:
        rows, rhs = exact
    correction = [0.0] * len(b)
    for _ in range(steps):
        residual = [float(rhs[i] - sum((g * Fraction(x[j]) for j, g in rows[i].items()), Fraction(0))) for i in range(len(b))]
        correction = _lu_solve(lu, perm, residual)
        x = [xi + di for xi, di in zip(x, correction)]
        if all(abs(d) <= sys.float_info.epsilon * abs(xi) for d, xi in zip(correction, x)):
            break
    floor = ROUNDING_SAFETY_FACTOR * sys.float_info.epsilon
    return x, [max(abs(d), floor * abs(xi)) for d, xi in zip(correction, x)]


def _solve_linear(a, b):
    """Backward-compatible helper: solution only."""
    return _solve_refined(a, b)[0]


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
    # The conductance system is assembled exactly (rationals) and rounded once for the float factorization.
    exact_rows=[{} for _ in unknown]; exact_rhs=[Fraction(0) for _ in unknown]; v_exact=Fraction(voltage)
    def add(i,j,value): exact_rows[i][j]=exact_rows[i].get(j,Fraction(0))+value
    for r in parsed:
        g=1/Fraction(r["resistance_ohm"]); a,b=r["a"],r["b"]
        if a in index: add(index[a],index[a],g)
        if b in index: add(index[b],index[b],g)
        if a in index and b in index:
            add(index[a],index[b],-g); add(index[b],index[a],-g)
        elif a in index and b==source: exact_rhs[index[a]] += g*v_exact
        elif b in index and a==source: exact_rhs[index[b]] += g*v_exact
    gmat=[[float(row.get(j,0)) for j in range(len(unknown))] for row in exact_rows]; rhs=[float(v) for v in exact_rhs]
    # Ground has 0 V and source is ideal at fixed voltage.
    values,errors=_solve_refined(gmat,rhs,exact=(exact_rows,exact_rhs)) if unknown else ([],[])
    node_v={ground:0.0,source:voltage}; node_v.update({n:values[i] for n,i in index.items()})
    # Estimated absolute error of each node voltage (source and ground are imposed exactly).
    node_err={ground:0.0,source:0.0}; node_err.update({n:errors[i] for n,i in index.items()})
    branches=[]; source_current=0.0; total_power=0.0
    unit=ROUNDING_SAFETY_FACTOR*sys.float_info.epsilon
    for r in parsed:
        drop=node_v[r["a"]]-node_v[r["b"]]
        current=drop/r["resistance_ohm"]
        power=drop*current
        total_power+=power
        if r["a"]==source: source_current += current
        if r["b"]==source: source_current -= current
        d_drop=node_err[r["a"]]+node_err[r["b"]]+unit*abs(drop)
        d_current=d_drop/r["resistance_ohm"]
        branches.append({**r,"voltage_v":drop,"current_a":current,"power_w":power,
                         "current_rounding_uncertainty_a":d_current,
                         "current_relative_uncertainty":(d_current/abs(current) if current else None)})
    # KCL at every internal node, return current through ground, and power balance, each
    # compared with the propagated rounding bound of the branches involved.
    kcl={n:0.0 for n in unknown}; kcl_bound={n:0.0 for n in unknown}
    ground_return=0.0; source_bound=0.0; ground_bound=0.0; power_bound=0.0
    for r in branches:
        di=r["current_rounding_uncertainty_a"]
        for end,sign in ((r["a"],1),(r["b"],-1)):
            if end in kcl: kcl[end]+=sign*r["current_a"]; kcl_bound[end]+=di
            if end==source: source_bound+=di
            if end==ground: ground_bound+=di
        if r["b"]==ground: ground_return+=r["current_a"]
        if r["a"]==ground: ground_return-=r["current_a"]
        power_bound+=2*abs(r["current_a"])*di*r["resistance_ohm"]
    max_kcl=max((abs(v) for v in kcl.values()),default=0.0)
    supplied=voltage*source_current
    power_bound+=abs(voltage)*source_bound
    # Current leaving the + terminal must come back through the ground node (the source closes the loop).
    source_loop_residual=source_current-ground_return
    tiny=1e-300
    kcl_ok=all(abs(kcl[n])<=kcl_bound[n]+tiny for n in kcl) and abs(source_loop_residual)<=source_bound+ground_bound+tiny
    power_ok=abs(supplied-total_power)<=power_bound+tiny
    # A branch is flagged when its current is not reliable to the displayed 5 significant digits,
    # unless that current is negligible next to the circuit's currents (e.g. a dead-end branch at ~0 A).
    i_max=max([abs(r["current_a"]) for r in branches]+[0.0])
    imprecise=[r["display_name"] for r in branches if r["current_rounding_uncertainty_a"]>DISPLAY_RELATIVE_PRECISION*max(abs(r["current_a"]),1e-12*i_max)]
    warnings=[]
    if imprecise or not (kcl_ok and power_ok):
        warnings.append({"code":"numerical_precision","params":{"names":", ".join(imprecise[:8])},
          "message":"Resistance ratio too extreme for double precision: the current of "+(", ".join(imprecise[:8]) or "some branches")+
                    " is not reliable to 5 significant digits. Node voltages remain usable."})
    return {"model":"ideal_dc_resistive_nodal_analysis","status":"computed","source_voltage_v":voltage,
      "source_current_a":source_current,"equivalent_resistance_ohm":(abs(voltage/source_current) if abs(source_current)>1e-15 else None),
      "source_power_supplied_w":supplied,"total_resistor_power_w":total_power,"power_balance_error_w":supplied-total_power,
      "node_voltages_v":node_v,"node_voltage_uncertainty_v":node_err,"branches":branches,"checks":{"max_internal_kcl_residual_a":max_kcl,
      "source_loop_residual_a":source_loop_residual,
      "power_balance_error_w":supplied-total_power,"rounding_safety_factor":ROUNDING_SAFETY_FACTOR,
      "max_kcl_bound_a":max(kcl_bound.values(),default=0.0),"power_balance_bound_w":power_bound,
      "kcl_satisfied":kcl_ok,"power_balance_satisfied":power_ok,"numerically_consistent":kcl_ok and power_ok},
      "conventions":CONVENTIONS,"warnings":warnings,
      "assumptions":["DC steady state","ideal voltage source","ideal wires and meters","linear ohmic resistors at the entered resistance","no parasitic inductance/capacitance or temperature dependence"],
      "limitations":["Not a SPICE transient/nonlinear solver; diodes, transistors, AC, inductors and capacitors are not implemented in this circuit engine.","Use component data sheets and independent verification before using results for real hardware."]}
