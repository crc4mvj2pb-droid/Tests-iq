"""v5.4 — RC transient of a wired workbench circuit, clicked in Chromium."""
from __future__ import annotations


def test_rc_transient_from_the_workbench(page, bench, evidence):
    src, r1, r2, cap, gnd = bench.add("dc-source"), bench.add("resistor"), bench.add("resistor"), bench.add("capacitor"), bench.add("ground")
    bench.set_value(src, 10); bench.set_value(r1, 1000); bench.set_value(r2, 1000)
    for a, pa, b, pb in ((src, "N", gnd, "GND"), (src, "P", r1, "A"), (r1, "B", r2, "A"), (r2, "B", gnd, "GND"), (cap, "A", r1, "B"), (cap, "B", gnd, "GND")):
        bench.wire(a, pa, b, pb)
    page.click("#wbTransient")
    page.wait_for_selector("#wbResult [data-transient]")
    tau = page.inner_text("#wbResult [data-tau]")
    assert tau == "0.00050000 s"
    assert page.locator("#wbResult svg polyline").count() == 2
    assert [r["model_id"] for r in bench.history()] == ["electrical_workbench_transient"]
    page.click(f'#wbBench [data-remove="{r1}"]')  # leaves the source + terminal unwired
    page.click("#wbTransient")
    page.wait_for_function("document.querySelector('#wbResult h3').textContent.includes('non calculé')")
    evidence("Transitoire RC sur la paillasse", "Câbler source 10 V, R1 = R2 = 1 kΩ, C = 1 µF ; simuler le transitoire", "τ = 0,5 ms, courbe tension/courant, dossier enregistré",
             f"τ affiché : {tau} ; message après retrait de R1 : {page.inner_text('#wbResult p')}")
