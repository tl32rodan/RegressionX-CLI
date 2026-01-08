import subprocess
import os
from .domain import Case

from pathlib import Path
from typing import Tuple, Any

def run_case(case: Case, work_root: str) -> Tuple[subprocess.CompletedProcess, subprocess.CompletedProcess, Path, Path]:
    """
    Executes the baseline and candidate commands in isolated sandbox directories.
    
    Args:
        case: The Case object containing commands.
        work_root: The root directory for the sandbox (e.g., /tmp/regressionx/run_123).
        
    Returns:
        (baseline_result, candidate_result, baseline_path, candidate_path)
    """
    root = Path(work_root) / case.name
    base_path = root / "baseline"
    cand_path = root / "candidate"
    
    # 1. Prepare Sandbox
    base_path.mkdir(parents=True, exist_ok=True)
    cand_path.mkdir(parents=True, exist_ok=True)
    
    env = os.environ.copy()
    if case.env:
        env.update(case.env)
        
    # 2. Run Baseline
    base_res = subprocess.run(
        case.baseline_command,
        cwd=str(base_path),
        shell=True,
        capture_output=True, # We might want to stream this later, but capture for now
        text=True,
        env=env
    )
    
    # 3. Run Candidate
    cand_res = subprocess.run(
        case.candidate_command,
        cwd=str(cand_path),
        shell=True,
        capture_output=True,
        text=True,
        env=env
    )
    
    return (base_res, cand_res, base_path, cand_path)
