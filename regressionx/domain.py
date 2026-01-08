from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Case:
    """
    Represents a single Regression Test Unit.
    
    A Case consists of two parts:
    1. Execution: "Run this"
       - name: Unique identifier for the case.
       - command: The actual shell command to execute.
       - env: Optional environment variables to set during execution.
       
    2. Verification: "Check this"
       - output: (Optional) The path (file or directory) where the command writes its result.
                 If None, we only check the return code.
       - baseline: (Optional) The path (file or directory) containing the expected result.
                   If None, no comparison is performed.
    """
    name: str # Identity
    
    # Baseline (The Control)
    baseline_command: str
    
    # Candidate (The Experiment)
    candidate_command: str
    
    env: Optional[Dict[str, str]] = None # Action Context
    
    # Verification
    # Output paths are now handled by the Executor (Sandbox) or auto-generated.
