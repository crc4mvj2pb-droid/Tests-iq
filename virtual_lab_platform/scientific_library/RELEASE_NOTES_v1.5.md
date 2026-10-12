# Virtual Lab Platform v1.5

## Delivered
1. Equipment catalogue now carries explicit illustrative capacity and one-sigma performance parameters for supported transfer and measurement devices.
2. Stock/diluent material flows drive the dilution solver; declared transfer devices constrain capacity.
3. First-order propagation estimates concentration uncertainty from independent transfer-volume uncertainties.
4. Thermal-chamber setpoint uncertainty is deterministically applied to the boundary conditions before running the heat solver.
5. Measurement plans can target a numeric solver output and sample row; compatible instruments generate reproducible synthetic readings with uncertainty, linked to the protocol trace.

## Validation
- Unit tests cover flow-driven concentration, transfer-capacity rejection, uncertainty propagation, repeatable instrument noise, unconnected measurement targets and thermal-chamber effects on solver outputs.
- API smoke checks cover dilution and heat workflows, local history, equipment perturbations and instrument readings.
- Frontend JavaScript syntax and Python compilation checked.

## Limits
- Equipment specifications are illustrative, not manufacturer-certified.
- Synthetic measurements are not real observations.
- Gaussian error models are simplified; no calibration curves, bias drift, cross-sensitivity or full metrology model is implemented.
- Dilution assumes ideal additive volumes and one shared stock concentration.
- Thermal chamber uses boundary setpoint perturbations only, not a full thermal digital twin.
- Models are not independently validated for research, clinical, safety, or engineering decisions.
