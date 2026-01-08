from regressionx import Template

# Define the "Shape" of the run
# This is the "Parametric Regression" vision: 
# One command template,# 1. Define the Logic (Template)
run_logic = Template(
    baseline_command="echo Running Baseline for {module}...",
    candidate_command="echo Running Candidate for {module}...",
    env={"TEST_MODE": "{mode}"}
)

# Define the data
# No need to repeat the command string!
cases = run_logic.generate([
    {"name": "auth_fast", "module": "auth", "mode": "fast"},
    {"name": "auth_full", "module": "auth", "mode": "full"},
    {"name": "payment_fast", "module": "payment", "mode": "fast"},
])
