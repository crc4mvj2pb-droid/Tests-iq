# Virtual Lab Platform v1.2

## Added
- Visual virtual bench for arranging selected components and equipment cards.
- Local CSV profiling: column type inference, missingness, duplicate rows, numeric summaries, categorical frequencies, Pearson correlations, preview and JSON export.
- Dataset analysis endpoint: `POST /api/analyze-dataset`.
- Explicit limitations distinguishing descriptive profiling from scientific validation.

## Important limits
- Bench cards are a visual workspace only, not physical 3D objects or validated digital twins.
- Correlations are exploratory and do not imply causation.
- Scientific units, domain-specific admissible ranges, experimental design, and data provenance still require user/source input.

- Added parameter overrides for supported global numeric SBML parameters and a bounded one-parameter sweep API/UI. Unknown parameter IDs and invalid sweep inputs are rejected.
