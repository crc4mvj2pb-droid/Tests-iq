# Virtual Lab Platform v1.3

## Added
- Connected the material-heating workflow to the existing 1D heat-diffusion solver.
- Added an SIR population-dynamics workflow connected to the existing compartment solver.
- Added UI parameters for both workflows and generalized result tables/check display.

## Limits
- The heat model is a simplified homogeneous 1D explicit finite-difference model with fixed boundary temperatures.
- The SIR model assumes homogeneous mixing and fixed parameters; it is not for public-health decisions or individual predictions.
- Both are educational L1 simulations, not empirically validated for real-world decisions.
