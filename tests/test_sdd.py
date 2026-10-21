"""Tests for .agents/bin/sdd.py, run against throwaway git repositories.

Run from the repository root: python3 -m unittest discover -s tests
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1] / ".agents"
CLI = HARNESS / "bin" / "sdd.py"
ASSETS = {
    "spec": HARNESS / "skills" / "sdd-spec" / "assets" / "spec.md",
    "adr": HARNESS / "skills" / "sdd-adr" / "assets" / "adr.md",
    "idea": HARNESS / "skills" / "sdd-idea" / "assets" / "idea.md",
}

_spec = importlib.util.spec_from_file_location("sdd", CLI)
sdd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sdd)

CONFIG = f"""[tests]
paths = ["tests"]
slice = ['{sys.executable}', "-m", "unittest", "{{files}}"]
full = ['{sys.executable}', "-m", "unittest", "discover", "-s", "tests", "-t", "."]
"""
UNITS = """
[[units]]
name = "app"
paths = ["app"]

[[units]]
name = "web"
paths = ["web"]
"""
SPEC = """---
id: {id}
title: Greet users by name
status: draft   # draft | ready | red | green | done
capability: greeting
change: {change}
breaking: {breaking}
adrs: [{adrs}]
---

# Goal

Users can be greeted by name.

# Scope

## In

- Greeting by name

## Out

- Localization

# Boundaries

- **Input:** `greet(name)`
- **Output:** greeting text
- **Touches:** app/greet.py
- **Contracts:** none

# Acceptance criteria

- **AC-1:** Given the name "Ana", when greet is called, then it returns "Hello, Ana!".

# Open questions

-
"""
ACCEPTANCE_TEST = """import unittest

from app.greet import greet


class Acceptance(unittest.TestCase):
    def test_greets_by_name(self):  # {id}/AC-1
        self.assertEqual(greet("Ana"), "Hello, Ana!")
"""
CLOSE = """---
spec: {id}
closed: 2026-01-01
---

# Delivered vs specified

| AC   | Status    | Test                  | Notes |
|------|-----------|-----------------------|-------|
| AC-1 | delivered | `test_greets_by_name` |       |

# Merge

- [x] ACs merged into the living capability spec
- [x] Runbook n/a
- [x] Debt n/a
"""
LIVING = "# Greeting\n\n- **{id}/AC-1:** Given a name, when greet is called, then it greets.\n"
STUB = "def greet(name):\n    raise NotImplementedError\n"
IMPLEMENTATION = 'def greet(name):\n    return f"Hello, {name}!"\n'


class Repo:
    def __init__(self, root: Path):
        self.root = root
        self.git("init", "-q")
        for key, value in (("user.email", "test@example.com"), ("user.name", "Test"),
                           ("commit.gpgsign", "false"), ("tag.gpgsign", "false")):
            self.git("config", key, value)
        self.write(".agents/config.toml", CONFIG)
        self.write("app/__init__.py", "")
        self.write("app/greet.py", STUB)
        self.write("tests/__init__.py", "")
        self.git("add", "-A")
        self.git("commit", "-qm", "init")

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8")

    def exists(self, relative: str) -> bool:
        return (self.root / relative).exists()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout

    def sdd(self, *args: str) -> tuple[int, str]:
        result = subprocess.run([sys.executable, str(CLI), *args], cwd=self.root, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr


class HarnessTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.repo = Repo(Path(tmp.name))

    def ok(self, *args: str) -> str:
        code, out = self.repo.sdd(*args)
        self.assertEqual(code, 0, out)
        return out

    def fails(self, *args: str) -> str:
        code, out = self.repo.sdd(*args)
        self.assertNotEqual(code, 0, out)
        return out

    def new_slice(self, sid="S-001", change="added", breaking="false", adrs="") -> str:
        folder = f".agents/docs/changes/{sid}-greet"
        self.repo.write(f"{folder}/spec.md", SPEC.format(id=sid, change=change, breaking=breaking, adrs=adrs))
        return folder

    def write_test(self, sid="S-001") -> str:
        path = f"tests/test_{sid.lower().replace('-', '')}.py"
        self.repo.write(path, ACCEPTANCE_TEST.format(id=sid))
        return path

    def to_red(self, sid="S-001") -> None:
        self.ok("advance", sid)
        self.write_test(sid)
        self.ok("advance", sid)

    def to_done(self, sid="S-001") -> None:
        self.to_red(sid)
        self.repo.write("app/greet.py", IMPLEMENTATION)
        self.ok("advance", sid)
        self.repo.write(f".agents/docs/changes/{sid}-greet/close.md", CLOSE.format(id=sid))
        self.repo.write(".agents/docs/specs/greeting.md", LIVING.format(id=sid))
        self.ok("advance", sid)

    def write_adr(self, adr: str, supersedes: str = "") -> None:
        text = ASSETS["adr"].read_text(encoding="utf-8").replace("ADR-XXX", adr).replace("<short title>", f"Decision {adr}")
        if supersedes:
            text = re.sub(r"^supersedes:\s*", f"supersedes: {supersedes} ", text, flags=re.M)
        self.repo.write(f".agents/docs/adr/{adr}-decision.md", text)


class FrontMatterTest(unittest.TestCase):
    def test_parses_values_and_ignores_comments(self):
        front, body = sdd.parse_front("---\nstatus: ready   # a | b\nbreaking: false\nadrs: [ADR-001, ADR-002]\nempty:   # note\n---\nbody\n")
        self.assertEqual(front, {"status": "ready", "breaking": False, "adrs": ["ADR-001", "ADR-002"], "empty": ""})
        self.assertEqual(body, "body\n")

    def test_set_front_keeps_comments_aligned(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.md"
            path.write_text("---\nstatus: proposed   # proposed | accepted\nsuperseded_by:     # set by the CLI\n---\n", encoding="utf-8")
            sdd.set_front(path, "status", "superseded")
            sdd.set_front(path, "superseded_by", "ADR-002")
            sdd.set_front(path, "base", "abc")
            lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[1], "status: superseded # proposed | accepted")
        self.assertEqual(lines[2], "superseded_by: ADR-002 # set by the CLI")
        self.assertEqual(lines[3], "base: abc")

    def test_bump_follows_semver_with_zero_major_rule(self):
        self.assertEqual(sdd.bump((0, 3, 1), "major"), (0, 4, 0))
        self.assertEqual(sdd.bump((1, 2, 3), "major"), (2, 0, 0))
        self.assertEqual(sdd.bump((1, 2, 3), "minor"), (1, 3, 0))
        self.assertEqual(sdd.bump((1, 2, 3), "patch"), (1, 2, 4))

    def test_changelog_puts_newest_release_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "CHANGELOG.md"
            sdd.write_changelog(path, "0.1.0", "Added", "- first")
            sdd.write_changelog(path, "0.2.0", "Fixed", "- second")
            text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Changelog"))
        self.assertLess(text.index("## [0.2.0]"), text.index("## [0.1.0]"))


class LifecycleTest(HarnessTest):
    def test_next_id_counts_open_and_archived_slices(self):
        self.assertEqual(self.ok("next-id", "slice").strip(), "S-001")
        self.new_slice("S-001")
        self.assertEqual(self.ok("next-id", "slice").strip(), "S-002")

    def test_unfilled_template_fails_ready_gate(self):
        self.repo.write(".agents/docs/changes/S-001-x/spec.md", ASSETS["spec"].read_text(encoding="utf-8"))
        out = self.fails("check", "S-001")
        self.assertIn("placeholder left in spec.md", out)
        self.assertIn("section 'Goal' is empty", out)

    def test_open_questions_block_ready(self):
        folder = self.new_slice()
        self.repo.write(f"{folder}/spec.md", self.repo.read(f"{folder}/spec.md").replace("# Open questions\n\n-", "# Open questions\n\n- Which locale?"))
        self.assertIn("open questions remain", self.fails("advance", "S-001"))

    def test_ready_records_base_commit(self):
        folder = self.new_slice()
        self.ok("advance", "S-001")
        front, _ = sdd.parse_front(self.repo.read(f"{folder}/spec.md"))
        self.assertEqual(front["status"], "ready")
        self.assertEqual(front["base"], self.repo.git("rev-parse", "HEAD").strip())

    def test_red_requires_tagged_tests_that_fail(self):
        folder = self.new_slice()
        self.ok("advance", "S-001")
        self.assertIn("AC-1 has no acceptance test", self.fails("check", "S-001"))
        self.write_test()
        self.repo.write("app/greet.py", IMPLEMENTATION)
        self.assertIn("they must fail before implementation", self.fails("check", "S-001"))
        self.repo.write("app/greet.py", STUB)
        self.ok("advance", "S-001")
        self.assertTrue(self.repo.exists(f"{folder}/.frozen.json"))

    def test_green_rejects_modified_frozen_test(self):
        self.new_slice()
        self.to_red()
        self.repo.write("app/greet.py", IMPLEMENTATION)
        test = self.write_test()
        self.repo.write(test, self.repo.read(test) + "# tampered\n")
        self.assertIn("frozen acceptance test modified", self.fails("check", "S-001"))
        self.write_test()
        self.ok("advance", "S-001")

    def test_done_requires_close_and_living_spec_then_archives(self):
        self.new_slice()
        self.to_red()
        self.repo.write("app/greet.py", IMPLEMENTATION)
        self.ok("advance", "S-001")
        out = self.fails("check", "S-001")
        self.assertIn("close.md is missing", out)
        self.assertIn("living spec", out)
        self.repo.write(".agents/docs/changes/S-001-greet/close.md", CLOSE.format(id="S-001"))
        self.repo.write(".agents/docs/specs/greeting.md", LIVING.format(id="S-001"))
        self.ok("advance", "S-001")
        self.assertFalse(self.repo.exists(".agents/docs/changes/S-001-greet"))
        self.assertIn("status: done", self.repo.read(".agents/docs/archive/S-001-greet/spec.md"))

    def test_reopen_unfreezes_acceptance_tests(self):
        folder = self.new_slice()
        self.to_red()
        self.ok("reopen", "S-001")
        self.assertFalse(self.repo.exists(f"{folder}/.frozen.json"))
        self.assertIn("status: draft", self.repo.read(f"{folder}/spec.md"))


class ReleaseTest(HarnessTest):
    def test_release_root_unit(self):
        self.new_slice()
        self.to_done()
        self.repo.git("add", "-A")
        self.ok("release", "S-001", "--apply", "--trailer", "Reviewed-by: Someone")
        self.assertIn("v0.1.0", self.repo.git("tag", "--list").split())
        changelog = self.repo.read("CHANGELOG.md")
        self.assertIn("## [0.1.0]", changelog)
        self.assertIn("### Added", changelog)
        self.assertIn("(.agents/docs/archive/S-001-greet/spec.md)", changelog)
        message = self.repo.git("log", "-1", "--format=%B")
        self.assertTrue(message.startswith("feat(greeting): greet users by name"))
        self.assertIn("Slice: S-001", message)
        self.assertIn("Reviewed-by: Someone", message)

    def test_release_bumps_only_affected_units(self):
        self.repo.write(".agents/config.toml", CONFIG + UNITS)
        self.repo.git("tag", "app/v1.0.0")
        self.new_slice(change="changed", breaking="[app]")
        self.to_done()
        out = self.ok("release", "S-001")
        self.assertIn("app/v2.0.0", out)
        self.assertNotIn("web/", out)
        self.assertIn("feat(greeting)!:", out)
        self.repo.git("add", "-A")
        self.ok("release", "S-001", "--apply")
        self.assertIn("**BREAKING:**", self.repo.read("app/CHANGELOG.md"))

    def test_release_requires_done(self):
        self.new_slice()
        self.assertIn("release requires done", self.fails("release", "S-001"))


class AdrTest(HarnessTest):
    def test_ready_rejects_missing_adr(self):
        self.new_slice(adrs="ADR-009")
        self.assertIn("ADR-009 does not exist", self.fails("check", "S-001"))

    def test_red_requires_accepted_adr(self):
        self.write_adr("ADR-001")
        self.new_slice(adrs="ADR-001")
        self.ok("advance", "S-001")
        self.write_test()
        self.assertIn("ADR-001 is proposed", self.fails("check", "S-001"))
        self.ok("accept", "ADR-001")
        self.ok("advance", "S-001")

    def test_accept_supersedes_and_status_warns(self):
        self.write_adr("ADR-001")
        self.ok("accept", "ADR-001")
        self.new_slice(adrs="ADR-001")
        self.write_adr("ADR-002", supersedes="ADR-001")
        self.ok("accept", "ADR-002")
        front, _ = sdd.parse_front(self.repo.read(".agents/docs/adr/ADR-001-decision.md"))
        self.assertEqual((front["status"], front["superseded_by"]), ("superseded", "ADR-002"))
        self.assertIn("follows ADR-001, superseded by ADR-002", self.ok("status"))
        self.assertIn("ADR-001 is superseded", self.fails("check", "S-001"))
        self.assertIn("only proposed ADRs can be accepted", self.fails("accept", "ADR-001"))


class IndexTest(HarnessTest):
    def test_init_appends_block_once_and_keeps_content(self):
        self.repo.write("AGENTS.md", "# Mine\n\nKeep me.\n")
        self.ok("init")
        self.ok("init")
        text = self.repo.read("AGENTS.md")
        self.assertEqual(text.count(sdd.AGENTS_BEGIN), 1)
        self.assertTrue(text.startswith("# Mine\n\nKeep me.\n"))
        self.ok("index", "--check")

    def test_init_replaces_outdated_block(self):
        self.repo.write("AGENTS.md", f"before\n{sdd.AGENTS_BEGIN}\nold text\n{sdd.AGENTS_END}\nafter\n")
        self.ok("init")
        text = self.repo.read("AGENTS.md")
        self.assertNotIn("old text", text)
        self.assertTrue(text.startswith("before\n") and text.endswith("after\n"))

    def test_index_check_detects_stale_index(self):
        self.ok("init")
        self.new_slice()
        self.assertIn("stale", self.fails("index", "--check"))
        self.ok("index")
        self.assertIn("[S-001](changes/S-001-greet/spec.md) draft", self.repo.read(".agents/docs/index.md"))
        self.ok("index", "--check")

    def test_index_lists_open_ideas_from_template(self):
        text = ASSETS["idea"].read_text(encoding="utf-8").replace("I-XXX", "I-001").replace("<short title>", "Onboarding")
        self.repo.write(".agents/docs/ideas/I-001-onboarding.md", text)
        self.ok("index")
        self.assertIn("- [I-001](ideas/I-001-onboarding.md) Onboarding · 1 pending candidate\n", self.repo.read(".agents/docs/index.md"))

    def test_index_links_context_documents(self):
        self.repo.write(".agents/docs/overview.md", "# System\n")
        self.repo.write(".agents/docs/glossary.md", "# Glossary\n")
        self.ok("index")
        index = self.repo.read(".agents/docs/index.md")
        self.assertIn("- [overview](overview.md)", index)
        self.assertIn("- [glossary](glossary.md)", index)


class LintTest(HarnessTest):
    def setUp(self):
        super().setUp()
        self.ok("init")

    def test_clean_project_passes(self):
        self.ok("lint")

    def test_reports_broken_links_and_unknown_ids(self):
        self.repo.write(".agents/docs/overview.md", "# System\n\nSee [the plan](missing.md) and ADR-007.\n")
        self.repo.write("app/notes.py", "# Implements S-042\n")
        self.ok("index")
        out = self.fails("lint")
        self.assertIn(".agents/docs/overview.md:3: broken link missing.md", out)
        self.assertIn("unknown reference ADR-007", out)
        self.assertIn("app/notes.py:1: unknown reference S-042", out)

    def test_ignores_code_fences_and_comments(self):
        self.repo.write(".agents/docs/overview.md", "# System\n\n```\n[x](missing.md) S-999\n```\n\n<!-- ADR-777 -->\n")
        self.ok("index")
        self.ok("lint")

    def test_traceability_between_living_spec_and_tests(self):
        self.new_slice()
        self.to_done()
        self.ok("lint")
        test = "tests/test_s001.py"
        original = self.repo.read(test)
        self.repo.write(test, original.replace("S-001/AC-1", "S-001/AC-9"))
        out = self.fails("lint")
        self.assertIn("S-001/AC-1 has no test tagged with it", out)
        self.assertIn("test references S-001/AC-9, which is neither in the living spec nor in an open slice", out)

    def test_warns_on_glossary_aliases(self):
        self.repo.write(".agents/docs/glossary.md", "# Glossary\n\n| Term | Definition | In code | Avoid |\n|---|---|---|---|\n| Account | A billable organization | `Account` | customer, client |\n")
        self.repo.write(".agents/docs/overview.md", "# System\n\nEach customer has users.\n")
        self.ok("index")
        out = self.ok("lint")
        self.assertIn("warning: .agents/docs/overview.md:3: 'customer' is a glossary alias; use 'Account'", out)


if __name__ == "__main__":
    unittest.main()
