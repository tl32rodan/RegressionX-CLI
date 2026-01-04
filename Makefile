.PHONY: test run lint demo clean

PYTHON?=python3

run:
	$(PYTHON) -m regressionx.cli $(ARGS)

test:
	$(PYTHON) -m pytest $(ARGS)

demo:
	$(PYTHON) -m regressionx.cli run --config examples/demo_config.json

clean:
	rm -rf demo
