# Scientific knowledge ingestion policy

This library is designed to grow by verified, versioned records rather than by treating generated text as scientific truth.

Every imported item should record: exact source and access date; authors/version/DOI where available; license; original units and conventions; domain and applicability; assumptions; known limitations; validation evidence; hash of source artifact; and whether it is explanatory, executable, benchmarked, or validated.

## Entry classes
- `concept` / `definition`: terminology and formal definitions.
- `equation` / `law` / `constraint`: formulae and conditions of use.
- `dataset`: data, schema, units, sampling protocol, license and provenance.
- `model`: equations plus executable implementation, solver and parameter definitions.
- `benchmark`: expected outputs and tolerances for checking implementations.
- `protocol`: reproducible steps for a defined computational workflow.

## Safety and epistemic controls
- Never mark an item validated just because it parses or runs.
- Never infer a source license from availability on the internet.
- Separate physical constants from fitted parameters and illustrative values.
- Preserve units, uncertainty, calibration range and domain shift warnings.
- Clinical, toxicological and other high-stakes models require specialist review and evidence appropriate to intended use.
- Imported models must run in a sandboxed/isolated worker before they can be executable in the platform.
- An equation being listed does not mean the platform can solve it. `executable` remains false until an implementation and tests exist.

## Current state
The first release contains foundational mathematical/scientific records to demonstrate the schema. It is deliberately incomplete, several records need bibliographic review, and entries are not individually validated by the software. This is the beginning of the knowledge architecture, not a claim to contain all scientific knowledge.
