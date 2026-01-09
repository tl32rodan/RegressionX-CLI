import subprocess
import os
from .domain import Case

from pathlib import Path
from typing import Tuple

def skipped_result() -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args="(skipped)", returncode=0, stdout="", stderr="")

def run_case(
    case: Case,
    run_baseline: bool = True,
    run_candidate: bool = True
) -> Tuple[subprocess.CompletedProcess, subprocess.CompletedProcess, Path, Path]:
    """
    Executes the baseline and candidate commands in configured directories.
    
    Args:
        case: The Case object containing commands and output paths.
        run_baseline: Whether to execute the baseline command.
        run_candidate: Whether to execute the candidate command.
        
    Returns:
        (baseline_result, candidate_result, baseline_path, candidate_path)
    """
    if not case.base_path or not case.cand_path:
        raise ValueError(f"Case '{case.name}' must define base_path and cand_path.")

    base_path = Path(case.base_path)
    cand_path = Path(case.cand_path)
    
    # 1. Prepare Output Paths
    base_path.mkdir(parents=True, exist_ok=True)
    cand_path.mkdir(parents=True, exist_ok=True)
    
    env = os.environ.copy()
    if case.env:
        env.update(case.env)
        
    # 2. Run Baseline
    if run_baseline:
        base_res = subprocess.run(
            case.baseline_command,
            cwd=str(base_path),
            shell=True,
            capture_output=True, # We might want to stream this later, but capture for now
            text=True,
            env=env
        )
    else:
        base_res = skipped_result()
    
    # 3. Run Candidate
    if run_candidate:
        cand_res = subprocess.run(
            case.candidate_command,
            cwd=str(cand_path),
            shell=True,
            capture_output=True,
            text=True,
            env=env
        )
    else:
        cand_res = skipped_result()
    
    return (base_res, cand_res, base_path, cand_path)
