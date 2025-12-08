.PHONY: test run lint

PYTHON?=python3

run:
$(PYTHON) -m regressionx.cli $(ARGS)

test:
$(PYTHON) -m pytest $(ARGS)
