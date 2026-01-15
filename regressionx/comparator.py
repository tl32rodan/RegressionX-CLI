import filecmp
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

@dataclass
class ComparatorResult:
    match: bool = True
    errors: List[str] = field(default_factory=list) # Structural errors (missing files)
    diffs: List[str] = field(default_factory=list)   # Content mismatches

def compare_directories(baseline: Path, candidate: Path) -> ComparatorResult:
    """
    Recursively compares two directories.
    Returns a ComparatorResult.
    """
    result = ComparatorResult()
    
    if not baseline.exists():
        result.match = False
        result.errors.append(f"Baseline directory does not exist: {baseline}")
        return result
        
    if not candidate.exists():
        result.match = False
        result.errors.append(f"Candidate directory does not exist: {candidate}")
        return result

    # Check if they are files
    if baseline.is_file() and candidate.is_file():
        if not filecmp.cmp(baseline, candidate, shallow=False):
            result.match = False
            result.diffs.append(f"Content mismatch: {baseline.name}")
        return result
        
    # Assume directories
    # common: files in both
    # left_only: files in baseline only
    # right_only: files in candidate only
    # diff_files: files in both but content differs
    
    # We use filecmp.dircmp. However, it's not fully recursive in one shot, 
    # we need to traverse.
    
    def _recursive_cmp(dcmp, rel_path=Path(".")):
        # 1. Structural checks
        for name in dcmp.left_only:
            result.match = False
            result.errors.append(f"Only in baseline: {rel_path / name}")
            
        for name in dcmp.right_only:
            result.match = False
            result.errors.append(f"Only in candidate: {rel_path / name}")
            
        # 2. Content checks (for files in both)
        # dcmp.diff_files only checks shallow unless we verify content.
        # But wait, dircmp does not do deep content compare by default.
        # We should manually compare common files.
        for name in dcmp.common_files:
            path_a = Path(dcmp.left) / name
            path_b = Path(dcmp.right) / name
            if not filecmp.cmp(path_a, path_b, shallow=False):
                result.match = False
                result.diffs.append(f"Content mismatch: {rel_path / name}")
                
        # 3. Recurse into subdirectories
        for sub_name, sub_dcmp in dcmp.subdirs.items():
            _recursive_cmp(sub_dcmp, rel_path / sub_name)
            
    dcmp = filecmp.dircmp(str(baseline), str(candidate))
    _recursive_cmp(dcmp)
    
    return result
