# Virtual Lab Platform v1.0 — first executable SBML subset

## Added
- SBML Level 2/3 subset parser for fixed-compartment reaction networks.
- Safe MathML evaluator for common arithmetic, powers, exponential/logarithmic and selected trigonometric operators.
- Fixed-step RK4 numerical integration with step caps, finite-value checks, non-negativity checks and explicit unsupported-feature errors.
- Imported SBML model can be selected and simulated from the UI.
- Output table and JSON export with model hash and limitations.

## Supported subset / limits
Supports fixed compartments, species initial amount/concentration, global and local numeric parameters, constant stoichiometry and kinetic laws in supported MathML. Does not support events, assignment/rate/algebraic rules, function definitions, dynamic compartments, variable stoichiometry, delays, or every MathML/SBML feature. Units are not automatically reconciled. Always compare against an SBML conformance suite and trusted reference outputs before research use.

## Run
macOS/Linux: `sh launch_macos_linux.sh`
Windows: double-click `launch_windows.bat`
Open `http://127.0.0.1:8765`. Requires Python 3.10+.
