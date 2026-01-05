.PHONY: test run lint demo clean

PYTHON?=python3

run:
	$(PYTHON) -m regressionx.cli $(ARGS)

test:
	$(PYTHON) -m pytest $(ARGS)

demo:
	$(PYTHON) -m regressionx.cli run --config examples/config.example.yaml

clean:
	rm -rf demo
