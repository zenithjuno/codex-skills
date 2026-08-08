#!/usr/bin/env python3
"""Durable batch QA and one-review-per-batch lifecycle for Thai math DOCX work."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import thai_math_docx_qa as qa


SCHEMA_VERSION = "1.0.0"
STATE_FILENAME = "knowledge-review-state.json"
MANIFEST_FILENAME = "project-build-manifest.json"
CONFIG_FILENAME = "batch-config.json"
AGGREGATE_FILENAME = "batch-qa-report.json"
PROJECT_ID_RE = re.compile(r"PRJ-[a-z0-9][a-z0-9-]*\Z")
BATCH_ID_RE = re.compile(r"BAT-[a-z0-9][a-z0-9-]*\Z")
CAPABILITY_ID_RE = re.compile(r"KNW-[0-9]{4}\Z")
PROFILE_ID_RE = re.compile(r"PRF-[a-z0-9][a-z0-9-]*\Z")
CANDIDATE_CLASSES = {
    "safe-primitive",
    "material-pattern",
    "family-recipe",
    "profile-preference",
    "qa-rule",
    "workflow-rule",
}
CANDIDATE_STATUSES = {"candidate", "ready-for-promotion", "one-off", "obsolete"}
CANDIDATE_TRIGGERS = {
    "unsupported-capability",
    "repeated-local-behavior",
    "explicit-user-feedback",
    "approved-preference",
    "qa-finding",
    "manifest-delta",
}
CANDIDATE_ACTIONS = {
    "review-for-promotion",
    "keep-project-local",
    "mark-one-off",
    "retire",
}
SOURCE_KINDS = {
    "generator",
    "preference-ledger",
    "design-note",
    "build-log",
    "handoff",
    "user-statement",
    "generated-draft",
    "returned-final-artifact",
}
EVIDENCE_BASES = {
    "explicit-user-approval",
    "independent-family-recurrence",
    "deterministic-correctness-safety",
    "representative-source-evidence",
}


class BatchStateError(RuntimeError):
    pass


def _canonical_hash(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def candidate_fingerprint(delta: Mapping[str, Any]) -> str:
    _validate_candidate_delta(delta)
    return _canonical_hash(
        {
            "title": _normalize_text(str(delta["title"])),
            "summary": _normalize_text(str(delta["summary"])),
            "capability_class": delta["capability_class"],
            "trigger": delta["trigger"],
            "recommended_action": delta["recommended_action"],
        }
    )


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"candidate delta {field} must be a non-empty string")
    return value


def _validate_candidate_delta(delta: Mapping[str, Any]) -> None:
    if not isinstance(delta, Mapping):
        raise ValueError("candidate delta must be an object")
    for field in ("title", "summary"):
        _require_nonempty_string(delta.get(field), field)
    controlled = {
        "capability_class": CANDIDATE_CLASSES,
        "promotion_status": CANDIDATE_STATUSES,
        "trigger": CANDIDATE_TRIGGERS,
        "recommended_action": CANDIDATE_ACTIONS,
        "source_kind": SOURCE_KINDS,
    }
    defaults = {"promotion_status": "candidate", "source_kind": "generated-draft"}
    for field, allowed in controlled.items():
        value = delta.get(field, defaults.get(field))
        if not isinstance(value, str) or value not in allowed:
            raise ValueError(f"candidate delta {field} must be one of {sorted(allowed)}, got {value!r}")
    for field in ("locator", "family_id", "observed_behavior"):
        if field in delta:
            _require_nonempty_string(delta[field], field)
    family_id = str(delta.get("family_id", "FAM-project-local"))
    if re.fullmatch(r"FAM-[a-z0-9][a-z0-9-]*", family_id) is None:
        raise ValueError(f"candidate delta family_id is invalid: {family_id!r}")
    basis = delta.get("basis", ["representative-source-evidence"])
    if (
        not isinstance(basis, list)
        or not basis
        or any(not isinstance(item, str) or item not in EVIDENCE_BASES for item in basis)
    ):
        raise ValueError(f"candidate delta basis must contain only {sorted(EVIDENCE_BASES)}")
    if len(basis) != len(set(basis)):
        raise ValueError("candidate delta basis must not contain duplicates")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _empty_review() -> dict[str, Any]:
    return {
        "status": "pending",
        "review_count": 0,
        "trigger": "none",
        "reviewed_candidate_ids": [],
        "promoted_entry_ids": [],
    }


class BatchWorkspace:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.manifest_path = self.root / MANIFEST_FILENAME
        self.config_path = self.root / CONFIG_FILENAME
        self.state_path = self.root / STATE_FILENAME
        self.reports_dir = self.root / "qa-reports"
        self.aggregate_path = self.root / AGGREGATE_FILENAME

    @classmethod
    def start(
        cls,
        root: str | Path,
        *,
        project_id: str,
        batch_id: str,
        expected_artifacts: int | None,
    ) -> "BatchWorkspace":
        workspace = cls(root)
        workspace.root.mkdir(parents=True, exist_ok=True)
        if PROJECT_ID_RE.fullmatch(project_id) is None:
            raise ValueError(f"invalid project_id: {project_id!r}")
        if BATCH_ID_RE.fullmatch(batch_id) is None:
            raise ValueError(f"invalid batch_id: {batch_id!r}")
        if expected_artifacts is not None and expected_artifacts < 1:
            raise ValueError("expected_artifacts must be at least 1")
        state: dict[str, Any] | None = None
        if workspace.state_path.exists():
            state = _read_json(workspace.state_path)
            if state["project_id"] != project_id:
                raise BatchStateError(
                    f"project_id mismatch: state has {state['project_id']!r}, requested {project_id!r}"
                )
        if workspace.manifest_path.exists():
            previous = _read_json(workspace.manifest_path)
            if previous["batch"]["status"] != "closed":
                raise BatchStateError(f"unfinished batch manifest already exists: {workspace.manifest_path}")
            missing_archive_sources = [
                str(path)
                for path in (workspace.config_path, workspace.aggregate_path)
                if not path.is_file()
            ]
            if missing_archive_sources:
                raise BatchStateError(
                    f"closed batch is incomplete; cannot archive missing files: {missing_archive_sources}"
                )
            archive = workspace.root / "history" / previous["batch"]["batch_id"]
            if archive.exists() and any(archive.iterdir()):
                raise BatchStateError(f"history archive already exists and is not empty: {archive}")
            archive.mkdir(parents=True, exist_ok=True)
            for path in (workspace.manifest_path, workspace.config_path, workspace.aggregate_path):
                if path.exists():
                    path.replace(archive / path.name)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "document_type": "project-build-manifest",
            "project_id": project_id,
            "batch": {"batch_id": batch_id, "status": "in-progress"},
            "artifacts": [],
            "capability_ids": [],
            "profile_ids": [],
            "local_extensions": [],
            "unsupported_events": [],
            "candidate_events": [],
            "knowledge_review": _empty_review(),
        }
        config = {
            "schema_version": SCHEMA_VERSION,
            "expected_artifacts": expected_artifacts,
            "qa_results": 0,
            "aggregate_reports": 0,
            "knowledge_reviews": 0,
            "intermediate_reviews": 0,
        }
        _write_json(workspace.manifest_path, manifest)
        _write_json(workspace.config_path, config)
        if state is None:
            _write_json(
                workspace.state_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "project_id": project_id,
                    "next_candidate_number": 1,
                    "next_evidence_number": 1,
                    "pending_candidates": {},
                    "reviewed_fingerprints": [],
                    "reviewed_candidates": {},
                },
            )
        else:
            state.setdefault("reviewed_candidates", {})
            _write_json(workspace.state_path, state)
        return workspace

    def _load(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        if not self.manifest_path.is_file() or not self.config_path.is_file() or not self.state_path.is_file():
            raise BatchStateError(f"incomplete batch workspace: {self.root}")
        return _read_json(self.manifest_path), _read_json(self.config_path), _read_json(self.state_path)

    def _save(
        self,
        manifest: Mapping[str, Any],
        config: Mapping[str, Any],
        state: Mapping[str, Any],
    ) -> None:
        _write_json(self.manifest_path, manifest)
        _write_json(self.config_path, config)
        _write_json(self.state_path, state)

    def _candidate_event(
        self,
        delta: Mapping[str, Any],
        artifact_id: str,
        artifact_path: Path,
        state: dict[str, Any],
    ) -> tuple[str, dict[str, Any] | None]:
        fingerprint = candidate_fingerprint(delta)
        if fingerprint in state["reviewed_fingerprints"]:
            reviewed = state.get("reviewed_candidates", {}).get(fingerprint)
            if reviewed is None:
                return fingerprint, None
            evidence_id = f"EVD-{state['next_evidence_number']:04d}"
            state["next_evidence_number"] += 1
            event = self._manifest_candidate(reviewed, keep_artifacts=False)
            event["artifact_ids"] = [artifact_id]
            event["evidence"] = [
                {
                    "evidence_id": evidence_id,
                    "source_kind": delta.get("source_kind", "generated-draft"),
                    "source_path": str(artifact_path),
                    "source_sha256": qa.sha256_file(artifact_path),
                    "locator": str(delta.get("locator", f"artifact {artifact_id}")),
                    "family_id": str(delta.get("family_id", "FAM-project-local")),
                    "observed_behavior": str(delta.get("observed_behavior", delta["summary"])),
                    "basis": list(delta.get("basis", ["representative-source-evidence"])),
                }
            ]
            return fingerprint, event
        pending = state["pending_candidates"].get(fingerprint)
        source_hash = qa.sha256_file(artifact_path)
        evidence_key = (str(artifact_path), str(delta.get("locator", "artifact")), source_hash)
        if pending is None:
            candidate_id = f"CAN-{state['next_candidate_number']:04d}"
            state["next_candidate_number"] += 1
            pending = {
                "candidate_id": candidate_id,
                "fingerprint": fingerprint,
                "title": str(delta["title"]),
                "summary": str(delta["summary"]),
                "capability_class": delta["capability_class"],
                "promotion_status": delta.get("promotion_status", "candidate"),
                "lifecycle": "project-local-extension",
                "trigger": delta["trigger"],
                "artifact_ids": [],
                "evidence": [],
                "recommended_action": delta["recommended_action"],
                "batch_ids": [],
                "evidence_keys": [],
            }
            state["pending_candidates"][fingerprint] = pending
        batch_id = _read_json(self.manifest_path)["batch"]["batch_id"]
        if batch_id not in pending["batch_ids"]:
            pending["batch_ids"].append(batch_id)
        if artifact_id not in pending["artifact_ids"]:
            pending["artifact_ids"].append(artifact_id)
        serialized_key = list(evidence_key)
        if serialized_key not in pending["evidence_keys"]:
            evidence_id = f"EVD-{state['next_evidence_number']:04d}"
            state["next_evidence_number"] += 1
            pending["evidence_keys"].append(serialized_key)
            pending["evidence"].append(
                {
                    "evidence_id": evidence_id,
                    "source_kind": delta.get("source_kind", "generated-draft"),
                    "source_path": str(artifact_path),
                    "source_sha256": source_hash,
                    "locator": str(delta.get("locator", f"artifact {artifact_id}")),
                    "family_id": str(delta.get("family_id", "FAM-project-local")),
                    "observed_behavior": str(delta.get("observed_behavior", delta["summary"])),
                    "basis": list(delta.get("basis", ["representative-source-evidence"])),
                }
            )
        return fingerprint, self._manifest_candidate(pending)

    @staticmethod
    def _manifest_candidate(pending: Mapping[str, Any], *, keep_artifacts: bool = True) -> dict[str, Any]:
        return {
            key: value
            for key, value in pending.items()
            if key not in {"batch_ids", "evidence_keys"}
            and (keep_artifacts or key != "artifact_ids")
        } | ({"artifact_ids": []} if not keep_artifacts else {})

    @staticmethod
    def _merge_candidate(manifest: dict[str, Any], event: Mapping[str, Any]) -> None:
        existing = next(
            (item for item in manifest["candidate_events"] if item["fingerprint"] == event["fingerprint"]),
            None,
        )
        if existing is None:
            manifest["candidate_events"].append(dict(event))
            return
        existing["artifact_ids"] = sorted(set(existing["artifact_ids"]) | set(event["artifact_ids"]))
        evidence_by_id = {item["evidence_id"]: item for item in existing["evidence"]}
        evidence_by_id.update({item["evidence_id"]: item for item in event["evidence"]})
        existing["evidence"] = [evidence_by_id[key] for key in sorted(evidence_by_id)]

    def add_artifact(
        self,
        docx_path: str | Path,
        *,
        contract: Mapping[str, Any],
        capability_ids: Sequence[str] = (),
        profile_ids: Sequence[str] = (),
        candidate_deltas: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        manifest, config, state = self._load()
        if manifest["batch"]["status"] == "closed":
            raise BatchStateError("cannot add artifacts to a closed batch")
        expected = config["expected_artifacts"]
        if expected is not None and len(manifest["artifacts"]) >= expected:
            raise BatchStateError("artifact count exceeds declared expected_artifacts")
        artifact_path = Path(docx_path)
        invalid_capabilities = [
            item
            for item in capability_ids
            if not isinstance(item, str) or CAPABILITY_ID_RE.fullmatch(item) is None
        ]
        if invalid_capabilities:
            raise ValueError(f"invalid capability ids: {invalid_capabilities}")
        invalid_profiles = [
            item
            for item in profile_ids
            if not isinstance(item, str) or PROFILE_ID_RE.fullmatch(item) is None
        ]
        if invalid_profiles:
            raise ValueError(f"invalid profile ids: {invalid_profiles}")
        for delta in candidate_deltas:
            _validate_candidate_delta(delta)
        artifact_id = f"ART-{len(manifest['artifacts']) + 1:04d}"
        result = qa.audit_docx(artifact_path, qa.normalize_contract(contract), mode="check")
        report_paths = qa.write_reports(
            result,
            report_dir=self.reports_dir / manifest["batch"]["batch_id"],
        )
        manifest["artifacts"].append(
            {
                "artifact_id": artifact_id,
                "path": str(artifact_path),
                "capability_ids": sorted(set(capability_ids)),
                "profile_ids": sorted(set(profile_ids)),
                "qa_report_path": report_paths["json"],
                "qa_verdict": result["verdict"],
                "needs_word_review": result["needs_word_review"],
            }
        )
        manifest["capability_ids"] = sorted(set(manifest["capability_ids"]) | set(capability_ids))
        manifest["profile_ids"] = sorted(set(manifest["profile_ids"]) | set(profile_ids))
        config["qa_results"] += 1
        for delta in candidate_deltas:
            _, event = self._candidate_event(delta, artifact_id, artifact_path, state)
            if event is not None:
                self._merge_candidate(manifest, event)
        if expected is not None and len(manifest["artifacts"]) == expected:
            manifest["batch"]["status"] = "ready-for-close"
        self._save(manifest, config, state)
        return result

    def record_unsupported(
        self,
        *,
        artifact_id: str,
        requested_capability: str,
        candidate_delta: Mapping[str, Any],
    ) -> None:
        manifest, config, state = self._load()
        artifact = next((item for item in manifest["artifacts"] if item["artifact_id"] == artifact_id), None)
        if artifact is None:
            raise BatchStateError(f"unknown artifact_id: {artifact_id}")
        _, event = self._candidate_event(candidate_delta, artifact_id, Path(artifact["path"]), state)
        if event is None:
            self._save(manifest, config, state)
            return
        self._merge_candidate(manifest, event)
        candidate_id = event["candidate_id"]
        manifest["unsupported_events"].append(
            {
                "event_id": f"UNS-{len(manifest['unsupported_events']) + 1:04d}",
                "requested_capability": requested_capability,
                "failure_mode": "fail-fast",
                "candidate_id": candidate_id,
                "artifact_ids": [artifact_id],
            }
        )
        self._save(manifest, config, state)

    def record_local_extension(
        self,
        *,
        artifact_id: str,
        summary: str,
        implementation_path: str,
        candidate_delta: Mapping[str, Any],
    ) -> None:
        manifest, config, state = self._load()
        artifact = next((item for item in manifest["artifacts"] if item["artifact_id"] == artifact_id), None)
        if artifact is None:
            raise BatchStateError(f"unknown artifact_id: {artifact_id}")
        _, event = self._candidate_event(candidate_delta, artifact_id, Path(artifact["path"]), state)
        if event is None:
            self._save(manifest, config, state)
            return
        self._merge_candidate(manifest, event)
        manifest["local_extensions"].append(
            {
                "extension_id": f"EXT-{len(manifest['local_extensions']) + 1:04d}",
                "summary": summary,
                "implementation_path": implementation_path,
                "candidate_id": event["candidate_id"],
                "qa_review_required": True,
            }
        )
        self._save(manifest, config, state)

    def checkpoint_handoff(self) -> dict[str, int]:
        manifest, config, state = self._load()
        if manifest["batch"]["status"] == "closed":
            raise BatchStateError("batch is already closed")
        if manifest["knowledge_review"]["review_count"] != 0:
            raise BatchStateError("unfinished handoff cannot contain a completed review")
        self._save(manifest, config, state)
        return self.counters()

    def close(self, *, trigger: str = "observable-batch-close") -> dict[str, Any]:
        if trigger not in {"observable-batch-close", "user-forced-review", "stage-close"}:
            raise ValueError(f"unsupported close trigger: {trigger}")
        manifest, config, state = self._load()
        if manifest["batch"]["status"] == "closed":
            return {"counters": self.counters(), "promotion_proposals": [], "silent": True}
        if not manifest["artifacts"]:
            raise BatchStateError("cannot close an empty batch")
        if trigger == "observable-batch-close" and manifest["batch"]["status"] != "ready-for-close":
            raise BatchStateError("batch closure is not observable; checkpoint handoff instead")
        failed = [item["artifact_id"] for item in manifest["artifacts"] if item["qa_verdict"] != "PASS"]
        if failed:
            raise BatchStateError(f"all artifacts must pass before batch close: {failed}")

        for fingerprint, pending in sorted(state["pending_candidates"].items()):
            if fingerprint in state["reviewed_fingerprints"]:
                continue
            self._merge_candidate(manifest, self._manifest_candidate(pending, keep_artifacts=False))
        pending_fingerprints = sorted(state["pending_candidates"])
        pending_candidate_ids = sorted(
            state["pending_candidates"][fingerprint]["candidate_id"]
            for fingerprint in pending_fingerprints
        )
        manifest["batch"]["status"] = "closed"
        manifest["knowledge_review"] = {
            "status": "completed",
            "review_count": 1,
            "trigger": trigger,
            "reviewed_candidate_ids": pending_candidate_ids,
            "promoted_entry_ids": [],
        }
        proposals = [
            {
                "candidate_id": item["candidate_id"],
                "title": item["title"],
                "recommended_action": item["recommended_action"],
            }
            for item in manifest["candidate_events"]
            if item["candidate_id"] in pending_candidate_ids
            and item["recommended_action"] == "review-for-promotion"
        ]
        state.setdefault("reviewed_candidates", {})
        for fingerprint in pending_fingerprints:
            state["reviewed_candidates"][fingerprint] = state["pending_candidates"][fingerprint]
        state["reviewed_fingerprints"] = sorted(
            set(state["reviewed_fingerprints"]) | set(state["pending_candidates"])
        )
        state["pending_candidates"] = {}
        config["knowledge_reviews"] = 1
        aggregate = {
            "schema_version": SCHEMA_VERSION,
            "document_type": "thai-math-docx-batch-qa-report",
            "project_id": manifest["project_id"],
            "batch_id": manifest["batch"]["batch_id"],
            "qa_results": len(manifest["artifacts"]),
            "aggregate_reports": 1,
            "knowledge_reviews": 1,
            "intermediate_reviews": 0,
            "verdict_counts": {
                verdict: sum(item["qa_verdict"] == verdict for item in manifest["artifacts"])
                for verdict in ("PASS", "FAIL", "BLOCKED")
            },
            "needs_word_review_count": sum(item["needs_word_review"] for item in manifest["artifacts"]),
            "promotion_proposals": proposals,
            "silent_no_change": not proposals,
        }
        _write_json(self.aggregate_path, aggregate)
        config["aggregate_reports"] = 1
        self._save(manifest, config, state)
        return {"counters": self.counters(), "promotion_proposals": proposals, "silent": not proposals}

    def counters(self) -> dict[str, int]:
        _, config, _ = self._load()
        return {
            "qa_results": int(config["qa_results"]),
            "aggregate_reports": int(config["aggregate_reports"]),
            "knowledge_reviews": int(config["knowledge_reviews"]),
            "intermediate_reviews": int(config["intermediate_reviews"]),
        }
