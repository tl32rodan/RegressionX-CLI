from regressionx import Template

# A and B write the same thing
run_logic = Template(
    baseline_command="echo {content} > output.txt",
    candidate_command="echo {content} > output.txt",
    base_path="runs/{name}/baseline",
    cand_path="runs/{name}/candidate"
)

cases = run_logic.generate([
    {"name": "should_pass", "content": "hello_world"},
])
