# Test Backend

Generated FastAPI backend contract.

## Run

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

## Test

```bash
python3 -m unittest discover -s tests
```
