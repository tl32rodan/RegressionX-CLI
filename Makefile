.PHONY: test run clean demo

PYTHON?=python

test:
	$(PYTHON) -m unittest discover tests

clean:
	$(PYTHON) -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"
	$(PYTHON) -c "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"

demo:
	$(PYTHON) bin/regressionX run --config examples/config.py
