import importlib.util
import os
from typing import List
from .domain import Case

def load_config(path: str) -> List[Case]:
    """
    Loads a python configuration file and returns the list of cases defined in it.
    The configuration file must define a variable named 'cases' which is a list of Case objects.
    """
    if not os.path.exists(path):
         raise FileNotFoundError(f"Config file not found: {path}")

    # Load module from path
    spec = importlib.util.spec_from_file_location("user_config", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load config from {path}")
    
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise RuntimeError(f"Error executing config file: {e}")
    
    if not hasattr(module, 'cases'):
         raise ValueError(f"Config file {path} fails to define 'cases' list.")
         
    cases = getattr(module, 'cases')
    if not isinstance(cases, list):
        raise TypeError("'cases' must be a list")
        
    return cases
