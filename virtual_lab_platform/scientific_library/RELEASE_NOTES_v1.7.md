# Virtual Lab Platform v1.7

## Delivered in this increment
- Bounded, dependency-free coordinate-search parameter fitting for implemented numerical models against user-supplied x/y observations.
- Fit diagnostics: SSE, RMSE, MAE, descriptive R², residual table, bounds, iteration count and convergence flag.
- Cross-model software sanity suite accessible at `GET /api/research/validation-suite` and through the UI.
- UI to fit parameters from pasted CSV observations and export a JSON fit dossier; UI to run/export the validation dossier.
- Automated tests for recovery of a known first-order reaction parameter, bounds validation, and cross-model sanity checks.

## Interpretation and limits
- Parameter fitting uses unweighted least squares, linear interpolation, and a deterministic coordinate search. It can converge to a local minimum.
- No confidence intervals, covariance matrix, parameter identifiability analysis, or independent experimental validation is included.
- The validation suite checks software-level mathematical invariants across ten executable solvers. Passing it does not validate the models against nature or certify medical, cosmetic, engineering, environmental, or clinical use.
- No complete cancer or Alzheimer simulator, external dataset ingestion/curation pipeline, physical instrument control, or AI research agent is claimed. Those require domain-specific implementation and independent validation.
