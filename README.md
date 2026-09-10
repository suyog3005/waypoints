# block-planner

Railway maintenance block scheduling system.

## Structure

```
block-planner/
  src/
    config.py     # central constants
    data_gen.py    # synthetic data generation
    baseline.py    # baseline heuristic scheduler
    check.py       # solution validation
    solver.py       # OR-Tools optimization solver
    model.py        # predictive modeling (LightGBM/SHAP)
  scripts/
    run.py          # pipeline entry point
  tests/
  outputs/
  models/
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python scripts/run.py
```
