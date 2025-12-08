from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

try:
    import yaml
except ImportError:  # pragma: no cover - fallback if yaml missing
    yaml = None


@dataclass
class CaseConfig:
    case_id: str
    params: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    extra_ignore: List[str] = field(default_factory=list)


@dataclass
class Config:
    schema_version: int
    paths: Dict[str, str]
    versions: Dict[str, str]
    cmd_templates: Dict[str, str]
    filters: Dict[str, Any]
    reporting: Dict[str, Any]
    cases: List[CaseConfig]


REQUIRED_KEYS = ["schema_version", "paths", "versions", "cmd_templates", "filters", "reporting", "cases"]


class ConfigError(ValueError):
    pass


def _load_raw_config(path: Path) -> Dict[str, Any]:
    content = path.read_text()
    if path.suffix in {".yaml", ".yml"}:
        if yaml is None:
            try:
                data = json.loads(content)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise ConfigError("PyYAML is required to load YAML configs") from exc
        else:
            data = yaml.safe_load(content)
    else:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            if yaml is None:
                raise
            data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ConfigError("Configuration root must be a mapping")
    return data


def _validate_keys(data: Dict[str, Any]) -> None:
    for key in REQUIRED_KEYS:
        if key not in data:
            raise ConfigError(f"Missing required config section: {key}")


def load_config(path: Path) -> Config:
    data = _load_raw_config(path)
    _validate_keys(data)

    cases = []
    for raw_case in data.get("cases", []):
        if "case_id" not in raw_case or "params" not in raw_case:
            raise ConfigError("Each case requires case_id and params")
        cases.append(
            CaseConfig(
                case_id=raw_case["case_id"],
                params=raw_case.get("params", {}),
                metadata=raw_case.get("metadata", {}),
                extra_ignore=raw_case.get("extra_ignore", []),
            )
        )

    return Config(
        schema_version=data["schema_version"],
        paths=data["paths"],
        versions=data["versions"],
        cmd_templates=data["cmd_templates"],
        filters=data["filters"],
        reporting=data["reporting"],
        cases=cases,
    )
