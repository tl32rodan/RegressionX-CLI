from regressionx import Case

cases = [
    Case(name="Hello World", baseline_command="echo Hello", candidate_command="echo Hello World"),
    Case(name="Python Info", baseline_command="python --version", candidate_command="python --version"),
]
