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
    stdout: str = ""
    timed_out: bool = False


@dataclass
class CaseResult:
    case_id: str
    status: str
    differences: List[str]
    commands: List[CommandExecution] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TemplateResolver:
    def __init__(self, context: Dict[str, Any], allowed_keys: set[str]):
        self.context = context
        self.allowed_keys = allowed_keys

    def render(self, template: str) -> str:
        formatter = string.Formatter()
        for field_name, *_ in formatter.parse(template):
            if field_name is None:
                continue
            if field_name not in self.allowed_keys:
                raise ValueError(f"Unsupported template field: {field_name}")
        return formatter.vformat(template, args=(), kwargs=self.context)


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
            case_contexts = {}
            for version, version_label in self.config.versions.items():
                context = self._context_for(case, version, version_label)
                workspace_root = Path(context["workspace_root"])
                artifacts_root = Path(context["artifacts_root"])
                artifact_paths[version] = artifacts_root
                workspace_root.mkdir(parents=True, exist_ok=True)
                artifacts_root.mkdir(parents=True, exist_ok=True)
                case_contexts[version] = (context, workspace_root, artifacts_root)

            for template_key in ("preprocess", "run", "postprocess"):
                template = self.config.cmd_templates.get(template_key)
                if not template:
                    continue
                for version, (context, workspace_root, artifacts_root) in case_contexts.items():
                    resolver = TemplateResolver(context, set(context.keys()))
                    cmd = resolver.render(template)
                    commands.append(
                        self._execute_command(
                            cmd,
                            workspace_root,
                            version,
                            env={"ARTIFACTS_ROOT": str(artifacts_root)},
                        )
                    )

            compare_template = self.config.cmd_templates.get("compare")
            if compare_template:
                compare_context = self._compare_context(case, case_contexts)
                resolver = TemplateResolver(compare_context, set(compare_context.keys()))
                cmd = resolver.render(compare_template)
                compare_workdir = (
                    compare_context.get("workspace_root_baseline")
                    or compare_context.get("workspace_root_candidate")
                    or str(next(iter(case_contexts.values()))[1])
                )
                commands.append(
                    self._execute_command(
                        cmd,
                        Path(compare_workdir),
                        "compare",
                        env={
                            "ARTIFACTS_ROOT_BASELINE": compare_context.get("artifacts_root_baseline", ""),
                            "ARTIFACTS_ROOT_CANDIDATE": compare_context.get("artifacts_root_candidate", ""),
                        },
                    )
                )

            left = artifact_paths.get("baseline") or artifact_paths.get("left")
            right = artifact_paths.get("candidate") or artifact_paths.get("right")
            differences = []
            if left and right:
                differences = sorted(self._compare_artifacts(left, right, case))
            failures = [cmd for cmd in commands if not cmd.succeeded]
            if failures:
                for cmd in failures:
                    suffix = " (timeout)" if cmd.timed_out else ""
                    errors.append(
                        f"Command failed{suffix}: {cmd.command} (version={cmd.version}, code={cmd.returncode})"
                    )
                status = "FAILURE"
            else:
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
            params=case.params,
            metadata=case.metadata,
        )

    def _execute_command(self, command: str, workdir: Path, version: str, env: Dict[str, str] | None = None) -> CommandExecution:
        env_vars = {**{k: str(v) for k, v in (env or {}).items()}, "REGX_VERSION": version}
        timeout_seconds = self.config.execution.get("timeout_seconds")
        try:
            proc = subprocess.run(
                command,
                cwd=workdir,
                shell=True,
                env={**os.environ, **env_vars},
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            return CommandExecution(
                version=version,
                command=command,
                succeeded=proc.returncode == 0,
                returncode=proc.returncode,
                stderr=proc.stderr.strip(),
                stdout=proc.stdout.strip(),
            )
        except subprocess.TimeoutExpired as exc:
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            if timeout_seconds:
                stderr = (stderr.strip() + "\n" if stderr.strip() else "") + f"Timed out after {timeout_seconds}s"
            return CommandExecution(
                version=version,
                command=command,
                succeeded=False,
                returncode=-1,
                stderr=stderr.strip(),
                stdout=stdout.strip(),
                timed_out=True,
            )

    def report_from_artifacts(self, cases: Iterable[CaseConfig] | None = None) -> List[CaseResult]:
        results: List[CaseResult] = []
        for case in cases or self.config.cases:
            results.append(self._report_case(case))
        return results

    def _report_case(self, case: CaseConfig) -> CaseResult:
        errors: List[str] = []
        artifact_paths: Dict[str, Path] = {}
        for version, version_label in self.config.versions.items():
            context = self._context_for(case, version, version_label)
            artifacts_root = Path(context["artifacts_root"])
            artifact_paths[version] = artifacts_root
            if not artifacts_root.exists():
                errors.append(f"Missing artifacts for {version}: {artifacts_root}")

        left = artifact_paths.get("baseline") or artifact_paths.get("left")
        right = artifact_paths.get("candidate") or artifact_paths.get("right")
        differences: List[str] = []
        if left and right and left.exists() and right.exists():
            differences = sorted(self._compare_artifacts(left, right, case))
        status = "ERROR" if errors else ("PASS" if not differences else "FAIL")
        return CaseResult(
            case_id=case.case_id,
            status=status,
            differences=differences,
            commands=[],
            errors=errors,
            params=case.params,
            metadata=case.metadata,
        )

    def _context_for(self, case: CaseConfig, version: str, version_label: str) -> Dict[str, Any]:
        context = {
            "case_id": case.case_id,
            "version": version,
            "version_label": version_label,
            "workspace_root": self.config.paths["workspace_root"].format(
                case_id=case.case_id,
                version=version,
                version_label=version_label,
            ),
            "artifacts_root": self.config.paths["artifacts_root"].format(
                case_id=case.case_id,
                version=version,
                version_label=version_label,
            ),
        }
        for key, value in case.params.items():
            context[f"params_{key}"] = value
        for key, value in case.metadata.items():
            context[f"metadata_{key}"] = value
        return context

    def _compare_context(self, case: CaseConfig, case_contexts: Dict[str, tuple[Dict[str, Any], Path, Path]]) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "case_id": case.case_id,
        }
        for key, value in case.params.items():
            context[f"params_{key}"] = value
        for key, value in case.metadata.items():
            context[f"metadata_{key}"] = value
        baseline = case_contexts.get("baseline")
        candidate = case_contexts.get("candidate")
        if baseline:
            base_context, workspace_root, artifacts_root = baseline
            context.update(
                {
                    "workspace_root_baseline": str(workspace_root),
                    "artifacts_root_baseline": str(artifacts_root),
                    "version_baseline": base_context["version"],
                    "version_label_baseline": base_context["version_label"],
                }
            )
        if candidate:
            cand_context, workspace_root, artifacts_root = candidate
            context.update(
                {
                    "workspace_root_candidate": str(workspace_root),
                    "artifacts_root_candidate": str(artifacts_root),
                    "version_candidate": cand_context["version"],
                    "version_label_candidate": cand_context["version_label"],
                }
            )
        return context

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
