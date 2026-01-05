from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

try:
    import jsonschema
except ImportError:  # pragma: no cover - optional dependency for schema validation
    jsonschema = None

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
    execution: Dict[str, Any] = field(default_factory=dict)


REQUIRED_KEYS = ["schema_version", "paths", "versions", "cmd_templates", "filters", "reporting", "cases"]


class ConfigError(ValueError):
    pass


def _load_raw_config(path: Path) -> Dict[str, Any]:
    content = path.read_text()
    if path.suffix not in {".yaml", ".yml"}:
        raise ConfigError("Configuration must be a YAML file (.yaml or .yml)")
    if yaml is None:
        raise ConfigError("PyYAML is required to load RegressionX configs")
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ConfigError("Configuration root must be a mapping")
    return data


def _validate_keys(data: Dict[str, Any]) -> None:
    for key in REQUIRED_KEYS:
        if key not in data:
            raise ConfigError(f"Missing required config section: {key}")


def _load_schema(schema_name: str) -> Dict[str, Any]:
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / schema_name
    return json.loads(schema_path.read_text())


def _validate_schema(data: Dict[str, Any]) -> None:
    if jsonschema is None:
        raise ConfigError("jsonschema is required to validate RegressionX configs")
    case_schema = _load_schema("regression_case.schema.json")
    config_schema = _load_schema("regression_config.schema.json")
    store = {
        case_schema["$id"]: case_schema,
        config_schema["$id"]: config_schema,
    }
    resolver = jsonschema.RefResolver.from_schema(config_schema, store=store)
    validator = jsonschema.Draft202012Validator(config_schema, resolver=resolver)
    errors = sorted(validator.iter_errors(data), key=lambda err: err.path)
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.path)
        location = f" at '{path}'" if path else ""
        raise ConfigError(f"Schema validation error{location}: {error.message}")


def load_config(path: Path) -> Config:
    data = _load_raw_config(path)
    _validate_schema(data)
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
        execution=data.get("execution", {}),
        cases=cases,
    )
