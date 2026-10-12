"""v7.1 — thermal models: lumped transient and composite wall, verified against independent references."""
from __future__ import annotations

import math

import pytest

import model_registry
import pipelines
import thermal
from contracts import ContractError


def _rk4(f, y, t_end, dt):
    t = 0.0
    for _ in range(int(round(t_end / dt))):
        k1 = f(y); k2 = f(y + dt / 2 * k1); k3 = f(y + dt / 2 * k2); k4 = f(y + dt * k3)
        y += dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4); t += dt
    return y


def run(model, inputs):
    return model_registry.run_model(model, inputs)["result"]


@pytest.mark.parametrize("power,t0", [(10.0, 298.15), (0.0, 400.0), (-5.0, 320.0)])
def test_lumped_transient_against_independent_integration(power, t0):
    r_th, c_th, t_amb, duration = 2.0, 50.0, 298.15, 250.0
    d = run("lumped_thermal_transient", {"power_w": power, "ambient_temperature_k": t_amb, "thermal_resistance_k_per_w": r_th, "thermal_capacitance_j_per_k": c_th,
                                         "initial_temperature_k": t0, "duration_s": duration, "points": 11})
    reference = _rk4(lambda T: (power - (T - t_amb) / r_th) / c_th, t0, duration, 0.01)
    assert d["final_temperature_k"] == pytest.approx(reference, rel=1e-9)
    assert d["time_constant_s"] == pytest.approx(100.0) and d["steady_temperature_k"] == pytest.approx(t_amb + power * r_th)


def test_lumped_energy_balance():
    d = run("lumped_thermal_transient", {"power_w": 10.0, "thermal_resistance_k_per_w": 2.0, "thermal_capacitance_j_per_k": 50.0, "duration_s": 300.0, "points": 3001})
    assert d["checks"]["energy_balance_relative_error"] < 1e-5


def test_biot_number_check():
    ok = run("lumped_thermal_transient", {"convection_coefficient_w_m2k": 10.0, "characteristic_length_m": 0.01, "conductivity_w_mk": 200.0})
    assert ok["biot_number"] == pytest.approx(5e-4) and ok["warnings"] == []
    bad = run("lumped_thermal_transient", {"convection_coefficient_w_m2k": 100.0, "characteristic_length_m": 0.05, "conductivity_w_mk": 0.5})
    assert bad["biot_number"] == pytest.approx(10.0) and bad["warnings"][0]["code"] == "lumped_assumption_invalid"
    with pytest.raises(thermal.ThermalError) as exc:
        run("lumped_thermal_transient", {"convection_coefficient_w_m2k": 100.0})
    assert exc.value.code == "incomplete_biot_inputs"


def test_steady_heating_adapter_is_the_long_time_limit_of_the_transient():
    adapter = pipelines.ADAPTERS["lumped_steady_heating"]["function"]({"power_w": 3.0, "ambient_temperature_k": 298.15, "thermal_resistance_k_per_w": 4.0,
                                                                      "thermal_capacitance_j_per_k": 5.0})
    integrated = _rk4(lambda T: (3.0 - (T - 298.15) / 4.0) / 5.0, 298.15, 40 * 20.0, 0.01)  # 40 time constants
    assert adapter["temperature_k"] == pytest.approx(integrated, rel=1e-9) and adapter["thermal_time_constant_s"] == pytest.approx(20.0)


def _finite_difference_wall(layers, area, t_hot, t_cold, nodes_per_layer=40):
    """Independent solver: steady conduction d/dx(k dT/dx) = 0 discretised node by node, solved by Gauss–Seidel then Thomas algorithm."""
    xs, ks = [], []
    for layer in layers:
        dx = layer["thickness_m"] / nodes_per_layer
        xs += [dx] * nodes_per_layer
        ks += [layer["conductivity_w_mk"]] * nodes_per_layer
    n = len(xs) + 1  # temperature nodes
    g = [k / dx for k, dx in zip(ks, xs)]  # conductance per unit area between nodes i and i+1
    a, b, c, d = [0.0] * n, [1.0] * n, [0.0] * n, [0.0] * n
    d[0], d[-1] = t_hot, t_cold
    for i in range(1, n - 1):
        a[i], b[i], c[i] = -g[i - 1], g[i - 1] + g[i], -g[i]
    for i in range(1, n):  # Thomas algorithm
        m = a[i] / b[i - 1]
        b[i] -= m * c[i - 1]; d[i] -= m * d[i - 1]
    temps = [0.0] * n
    temps[-1] = d[-1] / b[-1]
    for i in range(n - 2, -1, -1):
        temps[i] = (d[i] - c[i] * temps[i + 1]) / b[i]
    flux = g[0] * (temps[0] - temps[1])
    return flux * area, temps[nodes_per_layer]


def test_composite_wall_against_finite_differences():
    layers = [{"thickness_m": 0.012, "conductivity_w_mk": 0.17}, {"thickness_m": 0.1, "conductivity_w_mk": 0.038}, {"thickness_m": 0.2, "conductivity_w_mk": 0.72}]
    d = run("plane_wall_conduction", {"layers": layers, "area_m2": 3.0, "hot_temperature_k": 294.0, "cold_temperature_k": 263.0})
    q_fd, t_interface = _finite_difference_wall(layers, 3.0, 294.0, 263.0)
    assert d["heat_rate_w"] == pytest.approx(q_fd, rel=1e-9)
    assert d["temperatures"][1]["temperature_k"] == pytest.approx(t_interface, rel=1e-9)
    assert d["checks"]["closure_error_k"] < 1e-9


def test_single_layer_hand_calculation():
    d = run("plane_wall_conduction", {"layers": [{"thickness_m": 0.2, "conductivity_w_mk": 1.4}], "area_m2": 10.0, "hot_temperature_k": 293.15, "cold_temperature_k": 273.15})
    assert d["heat_rate_w"] == pytest.approx(1.4 * 10.0 * 20.0 / 0.2, rel=1e-12)  # 1400 W
    with_conv = run("plane_wall_conduction", {"layers": [{"thickness_m": 0.2, "conductivity_w_mk": 1.4}], "area_m2": 10.0, "hot_temperature_k": 293.15,
                                              "cold_temperature_k": 273.15, "h_hot_w_m2k": 10.0, "h_cold_w_m2k": 20.0})
    assert with_conv["heat_rate_w"] == pytest.approx(20.0 / (1 / 100 + 0.2 / 14 + 1 / 200), rel=1e-12)
    assert with_conv["u_value_w_m2k"] == pytest.approx(1 / (10.0 * (1 / 100 + 0.2 / 14 + 1 / 200)), rel=1e-12)


@pytest.mark.parametrize("inputs", [{"layers": []}, {"layers": [{"thickness_m": -1, "conductivity_w_mk": 1}]}, {"layers": [{"thickness_m": 0.1}]}])
def test_invalid_walls_are_refused(inputs):
    with pytest.raises(thermal.ThermalError) as exc:
        run("plane_wall_conduction", inputs)
    assert exc.value.code == "invalid_layers"


def test_contract_refuses_out_of_range_values():
    with pytest.raises(ContractError):
        run("lumped_thermal_transient", {"thermal_capacitance_j_per_k": 0})


def test_joule_pipeline_is_now_fully_verified():
    r = pipelines.run_pipeline(pipelines.example_pipelines()["joule_heating_kinetics"])
    assert r["maturity"]["level"] == "verified"
