from regressionx import Template

# A and B write different things
run_logic = Template(
    baseline_command="echo {base} > output.txt",
    candidate_command="echo {cand} > output.txt",
)

cases = run_logic.generate([
    {"name": "should_fail", "base": "foo", "cand": "bar"},
])
