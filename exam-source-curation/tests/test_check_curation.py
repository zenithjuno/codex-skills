from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_curation as checker

SHA = "a" * 64


def record(rid: str, **over) -> dict:
    base = {
        "id": rid,
        "source_location": ["p1"],
        "audit_ref": f"source-audit/{rid.split('-')[0]}-review.md",
        "audit_status": "pass",
        "primary_topic": "เซต",
        "pattern_label": "ใช้หลักบวกลบแก้การนับซ้อนของสามเซต",
        "core_decision": "หักส่วนที่ถูกนับซ้ำก่อนรวม",
        "method_signature": "เขียนแผนภาพ; ใช้หลักบวกลบสามเซต",
        "supporting_topics": [],
        "prerequisites": ["แผนภาพเวนน์"],
        "recognition_cue": "ให้จำนวนส่วนร่วมหลายชั้น",
        "distinctive_feature": "นับเฉพาะบริเวณใน A",
        "likely_error": "ลืมคืนส่วนร่วมสามเซต",
        "load": {"concept": 2, "procedure": 1, "reading": 1, "reason": "ต้องคุมการนับซ้ำ"},
        "sequence_role": "single-topic",
        "candidate_signal": {"status": "possible", "reason": "แนวตัดสินใจชัดหลังปูแผนภาพ"},
    }
    base.update(over)
    return base


def base_config() -> dict:
    def s(sid, **over):
        d = {"id": sid, "file": f"{sid}.pdf", "sha256": SHA, "role": "primary",
             "provenance": "official", "status": "canonical", "has_answer_key": True,
             "item_count": 2}
        d.update(over)
        return d
    return {
        "project": "demo",
        "denominator": ["A1", "A2"],
        "sets": [
            s("A1"), s("A2"),
            s("C1", role="supplementary", item_count=1),
            s("A2b", status="variant", variant_of="A2", provenance="tutor-compiled",
              has_answer_key=False),
        ],
    }


def base_records() -> dict[str, list[dict]]:
    return {
        "A1": [record("A1-Q01"), record("A1-Q02", stimulus="A1-G1")],
        "A2": [record("A2-Q01"),
               record("A2-Q02", audit_status="flag-answer",
                      candidate_signal={"status": "uncertain", "reason": "เฉลยต้นฉบับผิด"})],
        "C1": [record("C1-Q01")],
    }


def base_state() -> dict:
    return {
        "families": [{"id": "F01", "label": "นับซ้อนสามเซต",
                      "items": ["A1-Q01", "A2-Q01"], "supporting": ["C1-Q01"]}],
        "selection": [
            {"unit": "A1-Q01", "role": "core", "family": "F01", "slot": "ch01"},
            {"unit": "A2-Q01", "role": "contrast", "family": "F01", "contrast_with": "A1-Q01"},
            {"unit": "A1-G1", "role": "bridge", "slot": "ch01"},
            {"unit": "A2-Q02", "role": "reject-flagged"},
        ],
        "foundation_targets": [
            {"id": "B01", "need": "ชี้บริเวณ A−(B∪C)", "supports": ["A1-Q01"], "priority": "must"},
        ],
    }


class CurationProject:
    def __init__(self, config=None, records=None, state=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = config if config is not None else base_config()
        self.records = records if records is not None else base_records()
        self.state = state if state is not None else base_state()

    def write(self) -> Path:
        (self.root / "records").mkdir(exist_ok=True)
        (self.root / "source-audit").mkdir(exist_ok=True)
        for sid, recs in self.records.items():
            lines = [json.dumps(r, ensure_ascii=False) for r in recs]
            (self.root / "records" / f"{sid}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            heads = "".join(f"## {r['id']}\n\nคำตอบอิสระ ...\n\n" for r in recs)
            (self.root / "source-audit" / f"{sid}-review.md").write_text(heads, encoding="utf-8")
        (self.root / "curation-state.json").write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
        path = self.root / "curation-config.json"
        path.write_text(json.dumps(self.config, ensure_ascii=False), encoding="utf-8")
        return path

    def run(self, *args) -> tuple[int, str]:
        path = self.write()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = checker.main([args[0], str(path), *args[1:]])
        return code, out.getvalue()

    def close(self):
        self.tmp.cleanup()


class Base(unittest.TestCase):
    def project(self, **kw) -> CurationProject:
        proj = CurationProject(**kw)
        self.addCleanup(proj.close)
        return proj

    def assertFails(self, proj, command, fragment, *extra):
        code, out = proj.run(command, *extra)
        self.assertEqual(1, code, out)
        self.assertIn(fragment, out)


class ValidProjectTests(Base):
    def test_every_command_passes(self):
        proj = self.project()
        for command in ("config", "records", "families", "table", "trace"):
            code, out = proj.run(command)
            self.assertEqual(0, code, f"{command}: {out}")

    def test_table_computes_evidence_without_weak_warning(self):
        code, out = self.project().run("table")
        self.assertEqual(0, code, out)
        self.assertIn("| 2/2 |", out)
        self.assertIn("`C1-Q01`", out)
        self.assertNotIn("หลักฐานอ่อน", out)

    def test_table_warns_when_denominator_is_not_official(self):
        config = base_config()
        config["sets"][1]["provenance"] = "tutor-compiled"
        code, out = self.project(config=config).run("table")
        self.assertEqual(0, code, out)
        self.assertIn("หลักฐานอ่อน", out)


class ConfigTests(Base):
    def test_variant_must_point_to_canonical(self):
        config = base_config()
        config["sets"][3]["variant_of"] = "A2b"
        self.assertFails(self.project(config=config), "config", "variant_of must name another canonical set")

    def test_denominator_rejects_supplementary_and_variant(self):
        config = base_config()
        config["denominator"] = ["A1", "C1", "A2b"]
        proj = self.project(config=config)
        self.assertFails(proj, "config", "'C1' must be a canonical primary set")
        self.assertFails(proj, "config", "'A2b' must be a canonical primary set")

    def test_placeholder_hash_fails(self):
        config = base_config()
        config["sets"][0]["sha256"] = "<64 hex>"
        self.assertFails(self.project(config=config), "config", "sha256")


class RecordTests(Base):
    def edit(self, sid, index, **over):
        recs = copy.deepcopy(base_records())
        recs[sid][index].update(over)
        return self.project(records=recs)

    def test_generic_reason_fails(self):
        self.assertFails(self.edit("A1", 0, core_decision="ใช้สูตร"), "records", "is generic")

    def test_pattern_label_cannot_repeat_topic(self):
        self.assertFails(self.edit("A1", 0, pattern_label="เซต"), "records", "repeats primary_topic")

    def test_possible_signal_rejects_load_three(self):
        load = {"concept": 3, "procedure": 1, "reading": 1, "reason": "หลายชั้น"}
        self.assertFails(self.edit("A1", 0, load=load), "records", "load 3 requires")

    def test_possible_signal_rejects_flag(self):
        self.assertFails(self.edit("A1", 0, audit_status="flag-question"), "records", "audit flag requires")

    def test_missing_and_null_fields(self):
        recs = copy.deepcopy(base_records())
        del recs["A1"][0]["likely_error"]
        self.assertFails(self.project(records=recs), "records", "missing fields ['likely_error']")
        self.assertFails(self.edit("A1", 0, recognition_cue=None), "records", "null values")

    def test_audit_heading_required(self):
        proj = self.edit("A1", 0)
        proj.write()
        (proj.root / "source-audit" / "A1-review.md").write_text("## A1-Q02\n", encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = checker.main(["records", str(proj.root / "curation-config.json")])
        self.assertEqual(1, code)
        self.assertIn("lacks a '## A1-Q01' heading", out.getvalue())

    def test_coverage_and_partial(self):
        recs = copy.deepcopy(base_records())
        recs["A2"].pop()
        proj = self.project(records=recs)
        self.assertFails(proj, "records", "missing ['A2-Q02']")
        code, out = proj.run("records", "--partial")
        self.assertEqual(0, code, out)

    def test_set_filter_checks_one_set(self):
        recs = copy.deepcopy(base_records())
        recs["A2"][0]["core_decision"] = "คำนวณ"
        proj = self.project(records=recs)
        code, out = proj.run("records", "--set", "A1")
        self.assertEqual(0, code, out)
        self.assertFails(proj, "records", "is generic", "--set", "A2")

    def test_stimulus_cannot_span_sets(self):
        self.assertFails(self.edit("A2", 0, stimulus="A1-G1"), "records", "items span several sets")


class FamilyTests(Base):
    def test_duplicate_collapses_recurrence(self):
        recs = copy.deepcopy(base_records())
        recs["A2"][0]["duplicate_of"] = "A1-Q01"
        self.assertFails(self.project(records=recs), "families", "fewer than 2 denominator sets")

    def test_supplementary_item_cannot_count(self):
        state = base_state()
        state["families"][0]["items"].append("C1-Q01")
        state["families"][0]["supporting"] = []
        self.assertFails(self.project(state=state), "families", "outside the denominator")

    def test_item_in_two_families(self):
        state = base_state()
        state["families"].append({"id": "F02", "label": "x", "items": ["A1-Q01", "A2-Q01"]})
        self.assertFails(self.project(state=state), "families", "already belongs to family F01")


class TraceTests(Base):
    def test_teaching_role_needs_pass(self):
        state = base_state()
        state["selection"][3]["role"] = "core"
        self.assertFails(self.project(state=state), "trace", "needs every item to pass audit")

    def test_reject_flagged_needs_flag(self):
        state = base_state()
        state["selection"][0]["role"] = "reject-flagged"
        self.assertFails(self.project(state=state), "trace", "reject-flagged needs an audit flag")

    def test_target_must_support_learner_facing_unit(self):
        state = base_state()
        state["foundation_targets"][0]["supports"] = ["A2-Q02"]
        self.assertFails(self.project(state=state), "trace", "not a selected learner-facing unit")

    def test_unknown_unit_and_family_membership(self):
        state = base_state()
        state["selection"].append({"unit": "A9-Q01", "role": "core"})
        self.assertFails(self.project(state=state), "trace", "not an item id or stimulus group")
        state = base_state()
        state["selection"][2]["family"] = "F01"
        self.assertFails(self.project(state=state), "trace", "not a member of family F01")

    def test_contrast_and_drop_duplicate_links(self):
        state = base_state()
        del state["selection"][1]["contrast_with"]
        self.assertFails(self.project(state=state), "trace", "contrast needs contrast_with")
        state = base_state()
        state["selection"][2] = {"unit": "A1-G1", "role": "drop-duplicate", "same_as": "A2-Q02"}
        self.assertFails(self.project(state=state), "trace", "drop-duplicate needs same_as")

    def test_family_without_selection_is_a_note(self):
        state = base_state()
        state["selection"] = [state["selection"][2]]
        state["foundation_targets"] = []
        code, out = self.project(state=state).run("trace")
        self.assertEqual(0, code, out)
        self.assertIn("NOTE family F01", out)


if __name__ == "__main__":
    unittest.main()
