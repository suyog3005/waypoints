# pipeline/

Vendored mirror of the CP-SAT maintenance block optimiser from the
`block-planner` repo (`src/` + `models/priority_classifier.joblib` at the
time of copying). This is a straight copy, not a reimplementation.

**Do not modify `config.py`, `data_gen.py`, `baseline.py`, `solver.py`,
`check.py` or `model.py`.** To pull in upstream changes, re-copy the files
from block-planner rather than hand-editing them here. `priority_classifier.joblib`
is likewise vendored as-is.

## Why `src/` is a symlink

The vendored files import each other as `from src.config import ...` etc,
matching their package layout in the source repo. `src` in this directory is
a symlink to `.` (itself) so those imports resolve unmodified once
`services/optimization-service/pipeline/` is on `sys.path` — it is not a
real second copy of the files.

## Current state

Load-bearing: `app/planner.py`'s `run_optimization()` runs this pipeline end
to end (`model.py`'s classifier -> `solver.py`'s `schedule_solver` ->
`check.py`'s `validate`), via the translation layer in `app/adapter.py`. The
old `merge_windows` placeholder (`app/optimizer.py`, `app/shadow_finder.py`)
is no longer called but is kept in the tree.

`model.py`'s `MODEL_PATH` is relative to block-planner's own repo root, not
this service's cwd; `app/planner.py` patches that module attribute at import
time to point at `models/priority_classifier.joblib` in this directory
rather than editing the vendored file.
