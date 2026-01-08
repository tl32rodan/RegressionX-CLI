from regressionx import Template

# A and B write to nested directories
# We use mkdir -p (shell feature) to ensure subdirs exist
run_logic = Template(
    baseline_command="python -c \"import os; os.makedirs('sub/dir', exist_ok=True); open('sub/dir/file.txt', 'w').write('{base}')\"",
    candidate_command="python -c \"import os; os.makedirs('sub/dir', exist_ok=True); open('sub/dir/file.txt', 'w').write('{cand}')\"",
)

cases = run_logic.generate([
    # This should PASS
    {"name": "nested_pass", "base": "same", "cand": "same"},
    
    # This should FAIL (content mismatch in subdir)
    {"name": "nested_fail", "base": "foo", "cand": "bar"},
])
