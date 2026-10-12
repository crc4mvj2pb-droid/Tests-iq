"""Translate the graphical workbench's pin-to-pin wires into a DC netlist.

This is intentionally a small, explicit subset: one ideal DC source, one
reference/ground node, ideal wires, and linear resistors. It delegates numerical
analysis to electrical_circuits.solve_dc_circuit and does not pretend to be SPICE.
"""
from __future__ import annotations

import math

from electrical_circuits import solve_dc_circuit


class WorkbenchCircuitError(ValueError):
    """Invalid or unsupported topology assembled in the graphical workbench.

    `code` and `params` let the interface show a translated message; the English
    text remains the API's default explanation.
    """

    def __init__(self, message: str, code: str = "invalid_circuit", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def _label(item: dict) -> str:
    return str(item.get("displayName") or item.get("id") or "component")


def _number(value, label: str, quantity: str, code: str) -> float:
    if isinstance(value, bool) or value is None or (isinstance(value, str) and not value.strip()):
        raise WorkbenchCircuitError(f"Enter a numeric {quantity} for '{label}'.", code, name=label)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise WorkbenchCircuitError(f"Enter a numeric {quantity} for '{label}'.", code, name=label)
    return number


PINS: dict[str, tuple[str, ...]] = {
    "dc-source": ("P", "N"),
    "battery": ("P", "N"),
    "resistor": ("A", "B"),
    "resistor2": ("A", "B"),
    "wire": ("A", "B"),
    "ground": ("GND",),
    # Pins are recognized so the API can explain why these are not yet solvable.
    "capacitor": ("A", "B"),
    "capacitor2": ("A", "B"),
    "inductor": ("A", "B"),
    "switch": ("A", "B"),
    "fuse": ("A", "B"),
    "led": ("A", "B"),
    "diode": ("A", "B"),
    "potentiometer": ("A", "B"),
    "ac-source": ("P", "N"),
    "function-generator": ("P", "N"),
    "transistor": ("C", "B", "E"),
    "opamp": ("+", "-", "OUT"),
    "transformer": ("P1", "P2", "S1", "S2"),
    "motor-dc": ("A", "B"),
    "relay": ("A", "B"),
    "voltmeter": ("+", "-"),
    "ammeter": ("A", "B"),
    "multimeter": ("A", "B"),
    "oscilloscope": ("A", "B"),
    "breadboard": ("A", "B"),
}
SOLVER_IDS = {"dc-source", "battery", "resistor", "resistor2", "wire", "ground"}
SOURCE_IDS = {"dc-source", "battery"}
RESISTOR_IDS = {"resistor", "resistor2"}


def _biconnected_blocks(edges):
    """Edge sets of the biconnected blocks of a multigraph (Tarjan). edges: list of (u, v)."""
    adjacency: dict = {}
    for i, (u, v) in enumerate(edges):
        adjacency.setdefault(u, []).append((v, i)); adjacency.setdefault(v, []).append((u, i))
    disc: dict = {}; low: dict = {}; stack: list = []; blocks: list = []; clock = [0]

    def visit(u, parent_edge):
        disc[u] = low[u] = clock[0]; clock[0] += 1
        for v, i in adjacency[u]:
            if i == parent_edge:
                continue
            if v not in disc:
                stack.append(i); visit(v, i); low[u] = min(low[u], low[v])
                if low[v] >= disc[u]:
                    block = set()
                    while True:
                        e = stack.pop(); block.add(e)
                        if e == i:
                            break
                    blocks.append(block)
            elif disc[v] < disc[u]:
                stack.append(i); low[u] = min(low[u], disc[v])

    for node in adjacency:
        if node not in disc:
            visit(node, None)
    return blocks


def _topology_issues(resistors, find, source_pos, ground_net):
    """Return (floating resistors, no-current resistors) before any numerical solve.

    A resistor is floating when no chain of resistors links it to the source + net or to
    the ground net: that sub-network has no defined potential and would make the nodal
    matrix singular. A connected resistor can carry current only if it lies on a cycle
    through the source, i.e. in the same biconnected block as the source branch; any other
    resistor hangs from the circuit through a single node and carries no current whatever
    the values (it is valid, but reported).
    """
    ends = [(find((x["instanceId"], "A")), find((x["instanceId"], "B"))) for x in resistors]
    adjacency: dict = {}
    for a, b in ends:
        adjacency.setdefault(a, set()).add(b); adjacency.setdefault(b, set()).add(a)
    reached, stack = {source_pos, ground_net}, [source_pos, ground_net]
    while stack:
        for nxt in adjacency.get(stack.pop(), ()):
            if nxt not in reached:
                reached.add(nxt); stack.append(nxt)
    floating = [_label(x) for x, (a, b) in zip(resistors, ends) if a not in reached or b not in reached]
    connected = [(x, e) for x, e in zip(resistors, ends) if e[0] in reached and e[1] in reached]
    edges = [e for _, e in connected] + [(source_pos, ground_net)]  # the ideal source closes the loop
    source_edge = len(edges) - 1
    source_block = next(b for b in _biconnected_blocks(edges) if source_edge in b)
    no_current = [_label(x) for i, (x, _) in enumerate(connected) if i not in source_block]
    return floating, no_current


def solve_workbench_circuit(request: dict) -> dict:
    """Solve the placed and wired components from a workbench request.

    Components use {instanceId, id, displayName, qty}; connections use
    {a, pinA, b, pinB}. Every connection is an ideal wire between two terminals.
    """
    components = request.get("components")
    connections = request.get("connections")
    if not isinstance(components, list) or len(components) > 150:
        raise WorkbenchCircuitError("The workbench must provide a component list (maximum 150 items).", "invalid_request")
    if not isinstance(connections, list) or len(connections) > 500:
        raise WorkbenchCircuitError("The workbench must provide a wire list (maximum 500 connections).", "invalid_request")
    if not components:
        raise WorkbenchCircuitError("Add a DC source, at least one resistor, and a ground/reference symbol to the workbench.", "empty_bench")

    by_instance: dict[str, dict] = {}
    for item in components:
        if not isinstance(item, dict):
            raise WorkbenchCircuitError("One of the workbench components is invalid.", "invalid_request")
        instance_id = str(item.get("instanceId", ""))
        item_id = str(item.get("id", ""))
        if not instance_id or instance_id in by_instance:
            raise WorkbenchCircuitError("Component instance IDs must be present and unique.", "duplicate_instance")
        if item_id not in PINS:
            raise WorkbenchCircuitError(f"Unsupported electrical item '{item_id or 'unknown'}': terminal definitions are missing.", "unknown_item", name=item_id or "unknown")
        by_instance[instance_id] = {**item, "instanceId": instance_id, "id": item_id}

    parent: dict[tuple[str, str], tuple[str, str]] = {}

    def find(node: tuple[str, str]) -> tuple[str, str]:
        if node not in parent:
            parent[node] = node
        if parent[node] != node:
            parent[node] = find(parent[node])
        return parent[node]

    def union(a: tuple[str, str], b: tuple[str, str]) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            # Deterministic roots make exported net labels reproducible.
            if ra <= rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    connected_pins: set[tuple[str, str]] = set()
    normalized_connections = []
    for index, edge in enumerate(connections, start=1):
        if not isinstance(edge, dict):
            raise WorkbenchCircuitError(f"Wire {index} is invalid.", "invalid_wire", index=index)
        a, b = str(edge.get("a", "")), str(edge.get("b", ""))
        pin_a, pin_b = str(edge.get("pinA", "")), str(edge.get("pinB", ""))
        if not a or not b or a not in by_instance or b not in by_instance:
            raise WorkbenchCircuitError(f"Wire {index} refers to a component that is no longer on the workbench.", "orphan_wire", index=index)
        if a == b:
            raise WorkbenchCircuitError(f"Wire {index} must connect two different component terminals.", "self_wire", index=index)
        if not pin_a or pin_a not in PINS[by_instance[a]["id"]]:
            raise WorkbenchCircuitError(f"Wire {index}: invalid terminal '{pin_a}' on {_label(by_instance[a])}.", "invalid_terminal", index=index, pin=pin_a, name=_label(by_instance[a]))
        if not pin_b or pin_b not in PINS[by_instance[b]["id"]]:
            raise WorkbenchCircuitError(f"Wire {index}: invalid terminal '{pin_b}' on {_label(by_instance[b])}.", "invalid_terminal", index=index, pin=pin_b, name=_label(by_instance[b]))
        na, nb = (a, pin_a), (b, pin_b)
        union(na, nb)
        connected_pins.update((na, nb))
        normalized_connections.append({"a": a, "pinA": pin_a, "b": b, "pinB": pin_b, "kind": "ideal-wire"})

    # An explicit wire component internally joins its two terminals.
    for item in by_instance.values():
        if item["id"] == "wire":
            union((item["instanceId"], "A"), (item["instanceId"], "B"))

    active_unsupported = []
    for item in by_instance.values():
        if item["id"] not in SOLVER_IDS and any((item["instanceId"], p) in connected_pins for p in PINS[item["id"]]):
            active_unsupported.append(item)
    if active_unsupported:
        names = ", ".join(str(x.get("displayName") or x["id"]) for x in active_unsupported[:5])
        raise WorkbenchCircuitError(
            f"The connected component(s) {names} are not yet supported by the workbench DC solver. "
            "For now use only a DC source, resistors, ideal wire segments, and ground.",
            "unsupported_connected", names=names,
        )

    solver_items = [x for x in by_instance.values() if x["id"] in SOLVER_IDS]
    sources = [x for x in solver_items if x["id"] in SOURCE_IDS]
    grounds = [x for x in solver_items if x["id"] == "ground"]
    resistors = [x for x in solver_items if x["id"] in RESISTOR_IDS]
    if len(sources) != 1:
        raise WorkbenchCircuitError("The supported DC workbench solver requires exactly one DC source (dc-source or battery).", "source_count", count=len(sources))
    if len(grounds) != 1:
        raise WorkbenchCircuitError("Place exactly one ground/reference symbol and connect it to the circuit.", "ground_count", count=len(grounds))
    if not resistors:
        raise WorkbenchCircuitError("Place and wire at least one resistor. Capacitors, inductors and nonlinear devices are not solved by this DC network engine.", "no_resistor")

    # All terminals of each supported component must be connected deliberately.
    for item in solver_items:
        for pin in PINS[item["id"]]:
            if (item["instanceId"], pin) not in connected_pins:
                label = item.get("displayName") or item["id"]
                pretty_pin = {"P": "+", "N": "−", "GND": "GND"}.get(pin, pin)
                raise WorkbenchCircuitError(f"Terminal {pretty_pin} of '{label}' is not wired. Connect every terminal before solving.", "terminal_unwired", pin=pretty_pin, name=label)

    source, ground = sources[0], grounds[0]
    source_pos = find((source["instanceId"], "P"))
    source_neg = find((source["instanceId"], "N"))
    ground_net = find((ground["instanceId"], "GND"))
    if source_pos == source_neg:
        raise WorkbenchCircuitError("The source's + and − terminals are short-circuited by the wires.", "source_short", name=_label(source))
    if source_neg != ground_net:
        raise WorkbenchCircuitError("Connect the source's negative (−) terminal to the ground/reference node before solving.", "source_not_grounded", name=_label(source))

    # Name the source and reference nets as required by the nodal solver.
    source_node, ground_node = "SOURCE_PLUS", "0"
    root_to_node = {source_pos: source_node, ground_net: ground_node}
    roots = set()
    for item in resistors:
        for pin in ("A", "B"):
            roots.add(find((item["instanceId"], pin)))
    unknown_roots = sorted(roots - {source_pos, ground_net})
    for index, root in enumerate(unknown_roots, start=1):
        root_to_node[root] = f"N{index}"

    resistor_netlist = []
    for item in resistors:
        a_root, b_root = find((item["instanceId"], "A")), find((item["instanceId"], "B"))
        a_node, b_node = root_to_node.get(a_root), root_to_node.get(b_root)
        if a_node is None or b_node is None:
            raise WorkbenchCircuitError(f"Could not map the terminals of '{_label(item)}' to circuit nodes.", "unmapped_terminal", name=_label(item))
        if a_root == b_root:
            raise WorkbenchCircuitError(
                f"Both terminals of '{_label(item)}' are on the same node: it is bypassed by an ideal wire. Rewire the circuit.",
                "resistor_bypassed", name=_label(item),
            )
        ohms = _number(item.get("qty"), _label(item), "resistance in ohms", "invalid_resistance")
        if not math.isfinite(ohms) or ohms <= 0 or ohms > 1e15:
            raise WorkbenchCircuitError(f"The resistance of '{_label(item)}' must be a finite value > 0 Ω and ≤ 1e15 Ω.", "invalid_resistance", name=_label(item))
        resistor_netlist.append({"id": f"{item['id']}:{item['instanceId']}", "display_name": str(item.get("displayName") or item["id"]), "a": a_node, "b": b_node, "resistance_ohm": ohms})

    floating, dead_ends = _topology_issues(resistors, find, source_pos, ground_net)
    if floating:
        names = ", ".join(floating[:8])
        raise WorkbenchCircuitError(
            f"Part of the circuit is connected neither to the source nor to ground: {names}. Connect it or remove it.",
            "floating_network", names=names,
        )

    source_voltage = _number(source.get("qty"), _label(source), "DC source voltage in volts", "invalid_voltage")
    if not math.isfinite(source_voltage) or abs(source_voltage) > 1e6:
        raise WorkbenchCircuitError(f"The voltage of '{_label(source)}' must be finite and within ±1,000,000 V.", "invalid_voltage", name=_label(source))

    result = solve_dc_circuit({
        "source_voltage": source_voltage,
        "ground": ground_node,
        "source_node": source_node,
        "resistors": resistor_netlist,
    })
    node_labels = {ground_net: "0 (GND)", source_pos: "SOURCE+"}
    for index, root in enumerate(unknown_roots, start=1):
        node_labels[root] = f"N{index}"
    terminal_nodes = []
    for item in solver_items:
        for pin in PINS[item["id"]]:
            terminal_nodes.append({
                "component": str(item.get("displayName") or item["id"]),
                "instanceId": item["instanceId"],
                "pin": pin,
                "node": node_labels.get(find((item["instanceId"], pin)), "unmapped"),
            })
    result["topology"] = {
        "component_count": len(solver_items),
        "wire_count": len(normalized_connections),
        "net_count": len(set(find((i["instanceId"], p)) for i in solver_items for p in PINS[i["id"]])),
        "terminal_nodes": terminal_nodes,
        "netlist": resistor_netlist,
        "source": {"name": str(source.get("displayName") or source["id"]), "positive_node": "SOURCE+", "negative_node": "0 (GND)"},
        "ground": str(ground.get("displayName") or ground["id"]),
    }
    ignored = [_label(x) for x in by_instance.values() if x["id"] not in SOLVER_IDS]
    result["ignored_components"] = ignored
    if ignored:
        result["warnings"].append({"code": "ignored_components", "params": {"names": ", ".join(ignored[:8])},
                                   "message": f"Unwired component(s) not part of the DC calculation: {', '.join(ignored[:8])}."})
    if dead_ends:
        result["warnings"].append({"code": "dead_end_branch", "params": {"names": ", ".join(dead_ends[:8])},
                                   "message": f"Branch(es) attached to the circuit through a single node, carrying no current: {', '.join(dead_ends[:8])}."})
    result["assumptions"].append("The graphical wires are ideal conductors; the displayed pin-to-pin topology is converted to a node netlist.")
    result["limitations"].append("This workbench topology solver supports only one ideal DC source, a ground reference, ideal wires and linear resistors. It is not SPICE; capacitors, inductors, switches, diodes and transistors are not solved here.")
    return result
