from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


SCRIPT = Path(__file__).parents[1] / "scripts/repair_soffice_runtime.py"
SPEC = importlib.util.spec_from_file_location("repair_soffice_runtime", SCRIPT)
assert SPEC and SPEC.loader
repair = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = repair
SPEC.loader.exec_module(repair)

FIXTURE_SCRIPT = Path(__file__).parents[1] / "scripts/create_smoke_fixture.py"
FIXTURE_SPEC = importlib.util.spec_from_file_location("create_smoke_fixture", FIXTURE_SCRIPT)
assert FIXTURE_SPEC and FIXTURE_SPEC.loader
fixture = importlib.util.module_from_spec(FIXTURE_SPEC)
sys.modules[FIXTURE_SPEC.name] = fixture
FIXTURE_SPEC.loader.exec_module(fixture)


def make_executable(path: Path, text: str = "#!/bin/sh\nexit 0\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)
    return path


class LauncherDiscoveryTests(unittest.TestCase):
    def test_current_renderer_selects_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            override = make_executable(root / "bin/override/soffice")
            make_executable(root / "bin/soffice")
            renderer = root / "render_docx.py"
            renderer.write_text('runtime_bins.append(os.path.join(root, "bin", "override"))')

            found, source, _ = repair.discover_launcher(root, renderer=renderer)

            self.assertEqual(found, Path(os.path.abspath(override)))
            self.assertEqual(source, "renderer")

    def test_legacy_topology_remains_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = make_executable(root / "bin/soffice")

            found, source, _ = repair.discover_launcher(root)

            self.assertEqual(found, Path(os.path.abspath(legacy)))
            self.assertEqual(source, "legacy")

    def test_explicit_launcher_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            explicit = make_executable(root / "custom/soffice")
            make_executable(root / "bin/override/soffice")

            found, source, _ = repair.discover_launcher(root, explicit=explicit)

            self.assertEqual(found, Path(os.path.abspath(explicit)))
            self.assertEqual(source, "explicit")


class WrapperTests(unittest.TestCase):
    def test_relative_target_tracks_launcher_depth(self) -> None:
        root = Path("/runtime/dependencies")
        target = repair.native_target(root)
        override_text = repair.wrapper_text(root / "bin/override/soffice", target)
        legacy_text = repair.wrapper_text(root / "bin/soffice", target)

        self.assertIn("../../native/libreoffice-headless", override_text)
        self.assertIn("../native/libreoffice-headless", legacy_text)
        self.assertNotIn("poppler/etc/fonts", override_text)

    def test_wrapper_embeds_real_user_font_dir_and_filters_duplicate_profile(self) -> None:
        root = Path("/runtime/dependencies")
        text = repair.wrapper_text(
            root / "bin/override/soffice", repair.native_target(root),
            user_home=Path("/Users/field-user"),
        )
        self.assertIn("<dir>/Users/field-user/Library/Fonts</dir>", text)
        self.assertIn("-env:UserInstallation=*)", text)
        self.assertNotIn("<dir>${HOME}/Library/Fonts</dir>", text)

    def test_second_application_is_noop_and_creates_no_new_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launcher = make_executable(root / "bin/override/soffice", "#!/bin/sh\necho old\n")
            target = make_executable(repair.native_target(root))
            first = repair.plan_wrapper_change(launcher, target, "2026-08-26")

            repair.apply_wrapper_change(launcher, first)
            second = repair.plan_wrapper_change(launcher, target, "2026-08-26")

            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            backups = list(launcher.parent.glob("soffice.orig-runtime-fix-*") )
            self.assertEqual(len(backups), 1)
            self.assertEqual(stat.S_IMODE(launcher.stat().st_mode), 0o755)

    def test_symlink_launcher_is_replaced_without_overwriting_native_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = make_executable(repair.native_target(root), "#!/bin/sh\necho native\n")
            launcher = root / "bin/override/soffice"
            launcher.parent.mkdir(parents=True)
            launcher.symlink_to(target)
            native_before = target.read_bytes()

            found, _, _ = repair.discover_launcher(root)
            plan = repair.plan_wrapper_change(found, target, "2026-08-26")
            repair.apply_wrapper_change(found, plan)

            self.assertEqual(found, launcher)
            self.assertFalse(launcher.is_symlink())
            self.assertEqual(target.read_bytes(), native_before)
            backup = Path(str(plan["backup"]))
            self.assertTrue(backup.is_symlink())
            self.assertEqual(os.readlink(backup), str(target))


class ClassificationTests(unittest.TestCase):
    def test_missing_pymupdf_is_rasterizer_failure(self) -> None:
        self.assertEqual(
            repair.classify_failure_log("PyMuPDF is required to rasterise: pip install pymupdf"),
            "E",
        )

    def test_missing_pymupdf_does_not_authorize_libreoffice_repair(self) -> None:
        failure = repair.classify_failure_log("No module named 'fitz'")
        self.assertNotIn(failure, {"A", "B", "C", "D"})
        self.assertEqual(repair.status_for(failure, []), "RASTERIZER_MISSING")

    def test_launch_success_does_not_override_thai_failure(self) -> None:
        failure = repair.classify(
            Path("/tmp/soffice"), {}, {"ok": True},
            {"ok": False, "failure_class": "D"},
        )
        self.assertEqual(failure, "D")

    def test_repair_cli_does_not_mutate_launcher_for_rasterizer_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launcher = make_executable(
                root / "bin/override/soffice", "#!/bin/sh\necho LibreOfficeDev 26.8\n"
            )
            make_executable(repair.native_target(root))
            failure_log = root / "renderer.log"
            failure_log.write_text("PyMuPDF is required to rasterise")
            before = launcher.read_bytes()
            argv = [
                "repair_soffice_runtime.py", "--repair", "--dependency-root", str(root),
                "--failure-log", str(failure_log), "--json",
            ]
            output = io.StringIO()
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", output):
                result = repair.main()

            report = json.loads(output.getvalue())
            self.assertEqual(result, 2)
            self.assertEqual(report["status"], "RASTERIZER_MISSING")
            self.assertEqual(report["actions"], [])
            self.assertEqual(launcher.read_bytes(), before)
            self.assertEqual(list(launcher.parent.glob("*.orig-runtime-fix-*")), [])

    def test_thai_failure_cannot_be_cleared_by_version_check_alone(self) -> None:
        reported = repair.classify_failure_log("no Thai font was embedded")
        final = reported if reported == "D" else None
        self.assertEqual(final, "D")

    def test_pdftoppm_is_discovered_even_when_pymupdf_is_preferred(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tool = make_executable(root / "bin/override/pdftoppm")
            self.assertEqual(repair.find_poppler_tool(root, "pdftoppm"), tool)
            with mock.patch.object(repair.importlib.util, "find_spec", return_value=None):
                self.assertEqual(repair.rasterizer(root), ("pdftoppm", tool))


class DylibSafetyTests(unittest.TestCase):
    def test_unmapped_reference_blocks_all_patching(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            poppler = root / "poppler"
            poppler.mkdir()
            (poppler / "liblcms2.2.dylib").write_bytes(b"x")
            refs = {
                str(root / "binary"): [
                    "/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib",
                    "/opt/homebrew/opt/unknown/lib/libunknown.dylib",
                ]
            }
            with mock.patch.object(repair, "run") as run_mock:
                planned, unmapped = repair.patch_homebrew_refs(refs, poppler, dry_run=False)

            self.assertEqual(len(planned), 1)
            self.assertEqual(len(unmapped), 1)
            run_mock.assert_not_called()


class KnowledgeTests(unittest.TestCase):
    def test_same_day_different_bundle_is_not_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "knowledge.md"
            base = {
                "date": "2026-08-26", "bundle_version": "26.1", "active_launcher": "/a",
                "failure_class": "B", "status": "REPAIRED_DYLIB",
            }
            repair.append_knowledge(path, base)
            repair.append_knowledge(path, {**base, "bundle_version": "26.2"})
            repair.append_knowledge(path, base)

            text = path.read_text()
            self.assertEqual(text.count("<!-- soffice-runtime-fix:"), 2)
            self.assertIn('"bundle_version": "26.1"', text)
            self.assertIn('"bundle_version": "26.2"', text)


class SmokeFixtureTests(unittest.TestCase):
    def test_fixture_contains_thai_and_editable_omml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "thai-omml-smoke.docx"
            fixture.create_fixture(output)

            self.assertTrue(zipfile.is_zipfile(output))
            with zipfile.ZipFile(output) as package:
                document = package.read("word/document.xml").decode()
                styles = package.read("word/styles.xml").decode()
            self.assertRegex(document, repair.THAI_RANGE)
            self.assertIn("Latin 123", document)
            self.assertIn("<m:oMath>", document)
            self.assertIn("TH Sarabun New", styles)


if __name__ == "__main__":
    unittest.main()
