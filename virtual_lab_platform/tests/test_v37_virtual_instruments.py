import math
import pytest
from virtual_instruments import simulate_instrument_measurement


def test_seeded_measurement_is_reproducible_and_explicitly_simulated():
    request = {"instrument_id": "thermometer", "true_value": 25, "seed": 12}
    a = simulate_instrument_measurement(request)
    b = simulate_instrument_measurement(request)
    assert a == b
    assert a["status"] == "simulated_measurement"
    assert a["experimental_data"] is False
    assert a["instrument"]["unit"] == "°C"


def test_calibration_offset_correction_removes_injected_bias_on_seeded_reading():
    base = simulate_instrument_measurement({"instrument_id": "ph_meter", "true_value": 7.0, "seed": 9})
    biased = simulate_instrument_measurement({"instrument_id": "ph_meter", "true_value": 7.0, "instrument_bias": 0.4, "calibration_offset": 0.4, "seed": 9})
    assert math.isclose(base["indicated_reading"], biased["indicated_reading"])


def test_uncertainty_budget_combines_independent_components():
    result = simulate_instrument_measurement({"instrument_id": "analytical_balance", "true_value": 2.5, "calibration_uncertainty_sd": 0.003, "resolution": 0.01, "seed": 1})
    u = result["uncertainty_budget"]
    expected = math.sqrt(0.001**2 + 0.003**2 + (0.01 / math.sqrt(12))**2)
    assert math.isclose(u["combined_standard_uncertainty"], expected)
    assert math.isclose(u["expanded_uncertainty_k2"], 2 * expected)
    assert len(u["approximate_interval_k2"]) == 2


def test_rejects_unknown_non_measuring_equipment_and_unit_mismatch():
    with pytest.raises(ValueError, match="Unknown instrument_id"):
        simulate_instrument_measurement({"instrument_id": "not_real", "true_value": 1})
    with pytest.raises(ValueError, match="no supported measurement uncertainty"):
        simulate_instrument_measurement({"instrument_id": "beaker", "true_value": 1})
    with pytest.raises(ValueError, match="Unit mismatch"):
        simulate_instrument_measurement({"instrument_id": "thermometer", "true_value": 20, "unit": "K"})


@pytest.mark.parametrize("payload", [
    {"instrument_id": "thermometer", "true_value": float("nan")},
    {"instrument_id": "thermometer", "true_value": 20, "resolution": -1},
    {"instrument_id": "thermometer", "true_value": 20, "calibration_gain": 0},
    {"instrument_id": "thermometer", "true_value": 20, "seed": 1.2},
])
def test_rejects_invalid_numeric_inputs(payload):
    with pytest.raises(ValueError):
        simulate_instrument_measurement(payload)


def test_api_and_ui_expose_virtual_instrument_measurement_feature():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    app = (root / "app.py").read_text(encoding="utf-8")
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    assert '"version": APP_VERSION' in app
    assert '"/api/instruments/measure"' in app
    assert "fetch('/api/instruments/measure'" in html
    assert "mesure simulée" in html.lower()
