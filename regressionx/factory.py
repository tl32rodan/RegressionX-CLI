from typing import List, Dict, Optional, Any
from .domain import Case

class Template:
    """
    A factory class to generate multiple Cases from command templates and a list of data dictionaries.
    """
    def __init__(
        self,
        baseline_command: str,
        candidate_command: str,
        env: Optional[Dict[str, str]] = None,
        base_path: Optional[str] = None,
        cand_path: Optional[str] = None
    ):
        self.baseline_template = baseline_command
        self.candidate_template = candidate_command
        self.env_template = env or {}
        self.base_path_template = base_path
        self.cand_path_template = cand_path

    def _resolve_path(self, template: Optional[str], data: Dict[str, Any], label: str) -> str:
        if template is not None:
            try:
                return template.format(**data)
            except KeyError as e:
                raise KeyError(f"Missing key in data for {label} template: {e}")
        if label in data:
            return str(data[label])
        raise KeyError(f"Data dictionary must include '{label}' or provide a template.")

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
                base_path=self._resolve_path(self.base_path_template, data, "base_path"),
                cand_path=self._resolve_path(self.cand_path_template, data, "cand_path"),
                env=env if env else None
            ))
            
        return cases
