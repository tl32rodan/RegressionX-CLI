import hashlib
import os
import subprocess
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
import string
from typing import Any, Dict, Iterable, List

from .config import CaseConfig, Config


@dataclass
class CommandExecution:
    version: str
    command: str
    succeeded: bool
    returncode: int
    stderr: str = ""


@dataclass
class CaseResult:
    case_id: str
    status: str
    differences: List[str]
    commands: List[CommandExecution] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class TemplateResolver:
    def __init__(self, base_context: Dict[str, Any]):
        self.base_context = base_context

    def render(self, template: str) -> str:
        formatter = _DotFormatter()
        return formatter.vformat(template, args=(), kwargs=self.base_context)


class _DotFormatter(string.Formatter):
    def get_field(self, field_name, args, kwargs):  # pragma: no cover - exercised via render
        return self._resolve(field_name, kwargs), field_name

    def _resolve(self, expr: str, ctx: Dict[str, Any]):
        value: Any = ctx
        for part in expr.split('.'):
            if isinstance(value, dict):
                value = value[part]
            else:
                value = getattr(value, part)
        return value


class RegressionRunner:
    def __init__(self, config: Config):
        self.config = config

    def run_all(self) -> List[CaseResult]:
        results: List[CaseResult] = []
        for case in self.config.cases:
            results.append(self._run_case(case))
        return results

    def _run_case(self, case: CaseConfig) -> CaseResult:
        commands: List[CommandExecution] = []
        errors: List[str] = []

        try:
            artifact_paths: Dict[str, Path] = {}
            for version, version_label in self.config.versions.items():
                context = self._context_for(case, version, version_label)
                resolver = TemplateResolver(context)
                workspace_root = Path(resolver.render(self.config.paths["workspace_root"]))
                artifacts_root = Path(resolver.render(self.config.paths["artifacts_root"]))
                context = {**context, "workspace_root": str(workspace_root), "artifacts_root": str(artifacts_root)}
                resolver = TemplateResolver(context)
                artifact_paths[version] = artifacts_root

                workspace_root.mkdir(parents=True, exist_ok=True)
                artifacts_root.mkdir(parents=True, exist_ok=True)

                if "preprocess" in self.config.cmd_templates:
                    cmd = resolver.render(self.config.cmd_templates["preprocess"])
                    commands.append(self._execute_command(cmd, workspace_root, version))
                cmd = resolver.render(self.config.cmd_templates.get("run", ""))
                commands.append(self._execute_command(cmd, workspace_root, version, env={"ARTIFACTS_ROOT": str(artifacts_root)}))

            left = artifact_paths.get("baseline") or artifact_paths.get("left")
            right = artifact_paths.get("candidate") or artifact_paths.get("right")
            differences = []
            if left and right:
                differences = sorted(self._compare_artifacts(left, right, case))
            status = "PASS" if not differences else "FAIL"
        except Exception as exc:  # pragma: no cover - captured for reporting
            errors.append(str(exc))
            status = "ERROR"
            differences = []

        return CaseResult(
            case_id=case.case_id,
            status=status,
            differences=differences,
            commands=commands,
            errors=errors,
        )

    def _execute_command(self, command: str, workdir: Path, version: str, env: Dict[str, str] | None = None) -> CommandExecution:
        env_vars = {**{k: str(v) for k, v in (env or {}).items()}, "REGX_VERSION": version}
        proc = subprocess.run(
            command,
            cwd=workdir,
            shell=True,
            env={**os.environ, **env_vars},
            capture_output=True,
            text=True,
        )
        return CommandExecution(
            version=version,
            command=command,
            succeeded=proc.returncode == 0,
            returncode=proc.returncode,
            stderr=proc.stderr.strip(),
        )

    def _context_for(self, case: CaseConfig, version: str, version_label: str) -> Dict[str, Any]:
        return {
            "case_id": case.case_id,
            "version": version,
            "version_label": version_label,
            "params": case.params,
            "metadata": case.metadata,
        }

    def _compare_artifacts(self, left_dir: Path, right_dir: Path, case: CaseConfig) -> Iterable[str]:
        include_patterns = self.config.filters.get("include", [])
        ignore_patterns = self.config.filters.get("ignore", [])
        extra_ignore = case.extra_ignore if self.config.filters.get("extra_ignore_allowed", False) else []

        left_files = self._collect_files(left_dir)
        right_files = self._collect_files(right_dir)
        all_paths = left_files.union(right_files)

        differences = []
        for rel_path in all_paths:
            if not self._is_included(rel_path, include_patterns, ignore_patterns, extra_ignore):
                continue
            left_file = left_dir / rel_path
            right_file = right_dir / rel_path
            if not left_file.exists() or not right_file.exists():
                differences.append(rel_path.as_posix())
                continue
            if not self._is_same(left_file, right_file):
                differences.append(rel_path.as_posix())
        return differences

    def _collect_files(self, root: Path) -> set[Path]:
        files: set[Path] = set()
        for path in root.rglob("*"):
            if path.is_file():
                files.add(path.relative_to(root))
        return files

    def _is_included(
        self,
        path: Path,
        include_patterns: List[str],
        ignore_patterns: List[str],
        extra_ignore: List[str],
    ) -> bool:
        path_str = path.as_posix()
        match = lambda pattern: self._matches_pattern(path_str, pattern)
        included = any(match(pattern) for pattern in include_patterns) or not include_patterns
        if any(match(pattern) for pattern in ignore_patterns):
            included = False
        if any(match(pattern) for pattern in include_patterns):
            included = True
        if any(match(pattern) for pattern in extra_ignore):
            included = False
        return included

    def _matches_pattern(self, path_str: str, pattern: str) -> bool:
        if pattern in {"**/*", "**"}:
            return True
        return Path(path_str).match(pattern)

    def _is_same(self, left: Path, right: Path) -> bool:
        return self._hash(left) == self._hash(right)

    def _hash(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()
