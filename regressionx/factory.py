from typing import List, Dict, Optional, Any
from .domain import Case

class Template:
    """
    A factory class to generate multiple Cases from command templates and a list of data dictionaries.
    """
    def __init__(self, baseline_command: str, candidate_command: str, env: Optional[Dict[str, str]] = None):
        self.baseline_template = baseline_command
        self.candidate_template = candidate_command
        self.env_template = env or {}

    def generate(self, data_list: List[Dict[str, Any]]) -> List[Case]:
        """
        Generates a list of Case objects by applying each dictionary in data_list to the templates.
        """
        cases = []
        for data in data_list:
            if "name" not in data:
                raise KeyError("Data dictionary must contain 'name' key for Case identity")
            
            # Format commands
            try:
                base_cmd = self.baseline_template.format(**data)
                cand_cmd = self.candidate_template.format(**data)
            except KeyError as e:
                raise KeyError(f"Missing key in data for command template: {e}")
            
            # Format env
            env = {}
            for k, v in self.env_template.items():
                try:
                    env[k] = v.format(**data)
                except KeyError as e:
                    raise KeyError(f"Missing key in data for env template '{k}': {e}")
            
            cases.append(Case(
                name=str(data["name"]),
                baseline_command=base_cmd,
                candidate_command=cand_cmd,
                env=env if env else None
            ))
            
        return cases
