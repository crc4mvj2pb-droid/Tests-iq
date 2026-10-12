# Virtual Lab Platform v0.8 — expanded scientific library

## What changed
- Expanded the machine-readable knowledge base from 35 to 179 entries.
- Added coverage in mathematics, statistics, physics, chemistry, biology, medicine, neuroscience, environment, computer science, engineering, materials science, cosmetics, astronomy, Earth science and systems/decision analysis.
- Added SI base/derived unit reference: `scientific_library/units_and_dimensions.json`.
- Added a starter set of selected physical constants: `scientific_library/physical_constants.json`.
- Added local API endpoints: `/api/units` and `/api/constants`.
- Increased knowledge-base tests and updated API version to 0.8.

## Important scientific status
The catalogue is a curated starting point, not “all science”. Most entries are explanatory references and are deliberately marked non-executable and not individually validated in this software. Formula inclusion does not imply that a real-world system is adequately modeled. High-precision constants, bibliographic provenance, domain-specific unit checking, and application-specific validation must be completed before research-grade use.

## Run
- macOS/Linux: `sh launch_macos_linux.sh`
- Windows: double-click `launch_windows.bat`
- Then open `http://127.0.0.1:8765`

Requires Python 3.10+.
