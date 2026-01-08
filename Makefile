.PHONY: test run clean demo demo-fail demo-nested

PYTHON?=python

test:
	$(PYTHON) -m unittest discover tests

clean:
	$(PYTHON) -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"
	$(PYTHON) -c "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"
	$(PYTHON) -c "import pathlib; [p.unlink() for p in pathlib.Path('.').glob('*.html')]"
	$(PYTHON) -c "import pathlib; [p.unlink() for p in pathlib.Path('.').glob('*.md') if 'README' not in p.name]"

demo:
	$(PYTHON) bin/regressionX run --config examples/factory_config.py

demo-fail:
	$(PYTHON) bin/regressionX run --config examples/ab_fail.py --report demo_fail.md
	type demo_fail.md

demo-nested:
	$(PYTHON) bin/regressionX run --config examples/nested_output.py --report nested_report.md
	type nested_report.md
