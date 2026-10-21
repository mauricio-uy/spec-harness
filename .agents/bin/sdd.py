#!/usr/bin/env python3
"""spec-harness CLI: lifecycle gates, status and releases for spec-driven slices.

Commands (run from anywhere inside the repository):
  status [SLICE]            list open slices, or show one slice and its next gate
  check SLICE               verify the gate to the next status (runs tests when needed)
  advance SLICE             check the gate and move the slice to the next status
  reopen SLICE              send a slice back to draft and unfreeze its acceptance tests
  next-id {idea,slice,adr}  print the next free ID
  release SLICE [--apply] [--trailer TEXT]...
                            plan (or apply) changelog entries, release commit and tags

Optional configuration in .agents/config.toml:
  [tests]
  paths = ["tests"]         # where to look for acceptance test tags (default: whole repo)
  slice = "pytest {files}"  # runs the slice's acceptance test files
  full = "pytest"           # runs the full suite

  [[units]]                 # release units (default: one unit at the repository root)
  name = "api"
  paths = ["services/api"]

Commands may be strings or argument lists. Requires Python 3.11+ and git.
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    sys.exit("error: Python 3.11+ is required")

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tomllib
from datetime import date
from pathlib import Path

STATUSES = ["draft", "ready", "red", "green", "done"]
NEXT_SKILL = {"draft": "sdd-spec", "ready": "sdd-red", "red": "sdd-green", "green": "sdd-close"}
# change type -> (conventional commit type, changelog category, version bump)
CHANGES = {
    "added": ("feat", "Added", "minor"),
    "changed": ("feat", "Changed", "minor"),
    "deprecated": ("feat", "Deprecated", "minor"),
    "removed": ("feat", "Removed", "minor"),
    "fixed": ("fix", "Fixed", "patch"),
    "security": ("fix", "Security", "patch"),
}
PLACEHOLDERS = (
    "S-XXX", "I-XXX", "ADR-XXX", "YYYY-MM-DD", "<short title>", "<capability>", "<who",
    "<context>", "<action>", "<observable result>", "<test name>", "<unit>",
)
SKIP_DIRS = {".git", ".agents", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target"}
FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
AC_RE = re.compile(r"^\s*-\s*(~~)?\s*\*\*AC-(\d+):\*\*\s*(.*)$", re.M)
CHANGELOG_HEADER = """# Changelog

All notable changes are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
"""

ROOT = Path()
AGENTS = Path()


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def find_root() -> Path:
    cwd = Path.cwd().resolve()
    for directory in (cwd, *cwd.parents):
        if (directory / ".agents").is_dir():
            return directory
    fail("no .agents directory found in this or any parent directory")


def load_config() -> dict:
    path = AGENTS / "config.toml"
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and result.returncode:
        fail(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout if result.returncode == 0 else ""


# --- spec documents ---------------------------------------------------------

def parse_value(value: str):
    if value in ("true", "false"):
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        return [item.strip() for item in value[1:-1].split(",") if item.strip()]
    return value


def strip_yaml_comment(line: str) -> str:
    return re.sub(r"(^|\s)#.*", "", line).rstrip()


def parse_front(text: str) -> tuple[dict, str]:
    match = FRONT_RE.match(text)
    if not match:
        return {}, text
    data = {}
    for line in match.group(1).splitlines():
        key, sep, value = strip_yaml_comment(line).partition(":")
        if sep and not line.startswith((" ", "\t")):
            data[key.strip()] = parse_value(value.strip())
    return data, text[match.end():]


def set_front(path: Path, key: str, value) -> None:
    text = path.read_text(encoding="utf-8")
    match = FRONT_RE.match(text) or fail(f"{path} has no front matter")
    block = match.group(1)
    rendered = str(value).lower() if isinstance(value, bool) else str(value)
    pattern = re.compile(rf"^({re.escape(key)}:[ \t]*)([^#\n]*?)([ \t]*#.*)?$", re.M)
    if pattern.search(block):
        block = pattern.sub(lambda m: f"{m.group(1)}{rendered}{m.group(3) or ''}", block, count=1)
    else:
        block += f"\n{key}: {rendered}"
    path.write_text(f"---\n{block}\n---\n{text[match.end():]}", encoding="utf-8")


def sections(body: str) -> dict[str, str]:
    found: dict[str, list[str]] = {}
    current = None
    for line in COMMENT_RE.sub("", body).splitlines():
        heading = re.match(r"#{1,6}\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1)
            found[current] = []
        elif current:
            found[current].append(line)
    return {name: "\n".join(lines) for name, lines in found.items()}


def content(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() not in ("", "-")]


def placeholders(text: str) -> list[str]:
    match = FRONT_RE.match(text)
    front = "\n".join(strip_yaml_comment(l) for l in match.group(1).splitlines()) if match else ""
    visible = front + COMMENT_RE.sub("", text[match.end():] if match else text)
    return [p for p in PLACEHOLDERS if p in visible]


def active_acs(body: str) -> list[tuple[int, str]]:
    criteria = sections(body).get("Acceptance criteria", "")
    return [(int(n), text) for strike, n, text in AC_RE.findall(criteria) if not strike]


class Slice:
    def __init__(self, slice_id: str):
        self.id = slice_id.upper()
        candidates = [
            d for parent in ("changes", "archive") if (AGENTS / parent).is_dir()
            for d in (AGENTS / parent).iterdir()
            if d.is_dir() and (d.name == self.id or d.name.startswith(self.id + "-"))
        ]
        if not candidates:
            fail(f"slice {self.id} not found in .agents/changes or .agents/archive")
        self.dir = candidates[0]
        self.spec = self.dir / "spec.md"
        self.reload()

    def reload(self) -> None:
        self.text = self.spec.read_text(encoding="utf-8")
        self.front, self.body = parse_front(self.text)
        self.status = self.front.get("status", "draft")
        self.acs = active_acs(self.body)

    def goal(self) -> str:
        lines = content(sections(self.body).get("Goal", ""))
        return lines[0] if lines else self.front.get("title", self.id)


# --- tests -------------------------------------------------------------------

def walk(base: Path):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if path.stat().st_size <= 1_000_000:
                yield path


def tagged_tests(sl: Slice, config: dict) -> dict[int, set[str]]:
    """Map each AC number to the test files that reference `S-XXX/AC-n`."""
    tag = re.compile(rf"\b{re.escape(sl.id)}/AC-(\d+)\b")
    found: dict[int, set[str]] = {}
    for base in config.get("tests", {}).get("paths", ["."]):
        for path in walk(ROOT / base):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for n in set(tag.findall(text)):
                found.setdefault(int(n), set()).add(path.relative_to(ROOT).as_posix())
    return found


def all_files(found: dict[int, set[str]]) -> list[str]:
    return sorted(set().union(*found.values())) if found else []


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def run_tests(config: dict, kind: str, files: list[str] = ()) -> tuple[int | None, str]:
    command = config.get("tests", {}).get(kind)
    if not command:
        return None, f"tests.{kind} is not configured in .agents/config.toml"
    args = shlex.split(command, posix=os.name != "nt") if isinstance(command, str) else [str(a) for a in command]
    args = [item for arg in args for item in (files if arg == "{files}" else [arg])]
    args[0] = shutil.which(args[0]) or args[0]
    print("$ " + " ".join(args), flush=True)
    try:
        return subprocess.run(args, cwd=ROOT).returncode, ""
    except OSError as error:
        return None, f"cannot run tests.{kind}: {error}"


# --- gates -------------------------------------------------------------------

def gate_ready(sl: Slice, config: dict, run: bool) -> list[str]:
    errors = []
    front = sl.front
    for key in ("id", "title", "capability", "change"):
        if not front.get(key):
            errors.append(f"front matter: '{key}' is missing")
    if front.get("id") and front["id"] != sl.id:
        errors.append(f"front matter: id is {front['id']}, expected {sl.id}")
    if front.get("change") and front["change"] not in CHANGES:
        errors.append(f"front matter: change must be one of {', '.join(CHANGES)}")
    if not isinstance(front.get("breaking"), (bool, list)):
        errors.append("front matter: breaking must be true, false or a list of release units")
    found = sections(sl.body)
    for name in ("Goal", "In", "Out"):
        if not content(found.get(name, "")):
            errors.append(f"section '{name}' is empty")
    for label in ("Input", "Output", "Touches", "Contracts"):
        match = re.search(rf"\*\*{label}:\*\*[ \t]*(\S.*)?", found.get("Boundaries", ""))
        if not match or not match.group(1):
            errors.append(f"boundary '{label}' is empty (write 'none' if nothing applies)")
    if not 1 <= len(sl.acs) <= 6:
        errors.append(f"{len(sl.acs)} active acceptance criteria; expected 1-6 (split the slice if more)")
    for n, text in sl.acs:
        if not re.search(r"\bgiven\b.+\bwhen\b.+\bthen\b", text, re.I):
            errors.append(f"AC-{n} is not written as Given/When/Then")
    if content(found.get("Open questions", "")):
        errors.append("open questions remain")
    errors += [f"placeholder left in spec.md: {p}" for p in placeholders(sl.text)]
    return errors


def gate_red(sl: Slice, config: dict, run: bool) -> list[str]:
    errors = []
    found = tagged_tests(sl, config)
    active = {n for n, _ in sl.acs}
    for n in sorted(active - set(found)):
        errors.append(f"AC-{n} has no acceptance test tagged {sl.id}/AC-{n}")
    for n in sorted(set(found) - active):
        errors.append(f"tests reference {sl.id}/AC-{n}, which is not an active criterion")
    if run and not errors:
        code, error = run_tests(config, "slice", all_files(found))
        if error:
            errors.append(error)
        elif code == 0:
            errors.append("acceptance tests pass; they must fail before implementation")
    return errors


def gate_green(sl: Slice, config: dict, run: bool) -> list[str]:
    errors = []
    frozen_path = sl.dir / ".frozen.json"
    if not frozen_path.exists():
        return ["no frozen acceptance tests (.frozen.json); advance the slice from ready first"]
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    for path, expected in frozen.items():
        if not (ROOT / path).exists():
            errors.append(f"frozen acceptance test removed: {path}")
        elif digest(path) != expected:
            errors.append(f"frozen acceptance test modified: {path}")
    for path in sorted(set(all_files(tagged_tests(sl, config))) - set(frozen)):
        errors.append(f"acceptance test added after freeze: {path} (reopen the slice to change acceptance tests)")
    if run and not errors:
        for kind, files in (("slice", list(frozen)), ("full", [])):
            code, error = run_tests(config, kind, files)
            if error or code != 0:
                errors.append(error or f"tests.{kind} failed")
                break
    return errors


def gate_done(sl: Slice, config: dict, run: bool) -> list[str]:
    errors = []
    close = sl.dir / "close.md"
    if not close.exists():
        errors.append("close.md is missing")
    else:
        text = close.read_text(encoding="utf-8")
        errors += [f"placeholder left in close.md: {p}" for p in placeholders(text)]
        errors += [f"close.md does not account for AC-{n}" for n, _ in sl.acs if not re.search(rf"\bAC-{n}\b", text)]
        if re.search(r"^\s*-\s*\[ \]", COMMENT_RE.sub("", text), re.M):
            errors.append("close.md has unchecked merge items")
    living = AGENTS / "specs" / f"{sl.front.get('capability')}.md"
    if not living.exists():
        errors.append(f"living spec {living.relative_to(ROOT).as_posix()} is missing")
    else:
        text = living.read_text(encoding="utf-8")
        errors += [f"{sl.id}/AC-{n} is not merged into {living.name}" for n, _ in sl.acs if f"{sl.id}/AC-{n}" not in text]
    return errors


GATES = {"draft": gate_ready, "ready": gate_red, "red": gate_green, "green": gate_done}


def next_status(sl: Slice) -> str:
    if sl.status not in STATUSES:
        fail(f"{sl.id} has unknown status '{sl.status}'")
    if sl.status == "done":
        fail(f"{sl.id} is already done")
    return STATUSES[STATUSES.index(sl.status) + 1]


def report(sl: Slice, errors: list[str]) -> int:
    print(f"{sl.id}: {sl.status} -> {next_status(sl)}")
    for error in errors:
        print(f"  FAIL {error}")
    print("  gate passed" if not errors else f"  {len(errors)} problem(s)")
    return 1 if errors else 0


# --- commands ----------------------------------------------------------------

def cmd_status(args, config) -> int:
    if args.slice:
        sl = Slice(args.slice)
        print(f"{sl.id} {sl.front.get('title', '')}")
        print(f"  status:     {sl.status}")
        print(f"  folder:     {sl.dir.relative_to(ROOT).as_posix()}")
        print(f"  capability: {sl.front.get('capability', '')}")
        print(f"  criteria:   {', '.join(f'AC-{n}' for n, _ in sl.acs) or 'none'}")
        if sl.status == "done":
            return 0
        print(f"  next skill: {NEXT_SKILL[sl.status]}")
        report(sl, GATES[sl.status](sl, config, run=False))
        return 0
    changes = AGENTS / "changes"
    slices = sorted(d for d in changes.iterdir() if d.is_dir()) if changes.is_dir() else []
    if not slices:
        print("no open slices")
    for d in slices:
        sl = Slice(re.match(r"S-\d+", d.name).group(0))
        print(f"{sl.id:<7} {sl.status:<6} {sl.front.get('title', ''):<40} -> {NEXT_SKILL.get(sl.status, '')}")
    return 0


def cmd_check(args, config) -> int:
    sl = Slice(args.slice)
    next_status(sl)
    return report(sl, GATES[sl.status](sl, config, run=True))


def cmd_advance(args, config) -> int:
    sl = Slice(args.slice)
    target = next_status(sl)
    if report(sl, GATES[sl.status](sl, config, run=True)):
        return 1
    if target == "ready" and (ROOT / ".git").exists():
        head = git("rev-parse", "HEAD", check=False).strip()
        if head:
            set_front(sl.spec, "base", head)
    if target == "red":
        frozen = {path: digest(path) for path in all_files(tagged_tests(sl, config))}
        (sl.dir / ".frozen.json").write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
    set_front(sl.spec, "status", target)
    if target == "done":
        archive = AGENTS / "archive"
        archive.mkdir(exist_ok=True)
        shutil.move(str(sl.dir), str(archive / sl.dir.name))
    print(f"{sl.id} is now {target}")
    return 0


def cmd_reopen(args, config) -> int:
    sl = Slice(args.slice)
    if sl.dir.parent.name == "archive":
        fail(f"{sl.id} is closed; start a new slice instead")
    (sl.dir / ".frozen.json").unlink(missing_ok=True)
    set_front(sl.spec, "status", "draft")
    print(f"{sl.id} is now draft; acceptance tests are unfrozen")
    return 0


def cmd_next_id(args, config) -> int:
    prefix, folders = {"idea": ("I", ["ideas"]), "slice": ("S", ["changes", "archive"]), "adr": ("ADR", ["adr"])}[args.kind]
    numbers = [
        int(m.group(1)) for folder in folders if (AGENTS / folder).is_dir()
        for path in (AGENTS / folder).iterdir() if (m := re.match(rf"{prefix}-(\d+)", path.name))
    ]
    print(f"{prefix}-{max(numbers, default=0) + 1:03d}")
    return 0


def latest_version(unit: str) -> tuple[int, int, int]:
    prefix = re.escape(f"{unit}/v" if unit else "v")
    versions = [
        tuple(int(x) for x in m.groups()) for tag in git("tag", "--list", check=False).splitlines()
        if (m := re.fullmatch(prefix + r"(\d+)\.(\d+)\.(\d+)", tag.strip()))
    ]
    return max(versions, default=(0, 0, 0))


def bump(version: tuple[int, int, int], level: str) -> tuple[int, int, int]:
    major, minor, patch = version
    if level == "major" and major > 0:
        return major + 1, 0, 0
    if level in ("major", "minor"):
        return major, minor + 1, 0
    return major, minor, patch + 1


def changed_files(base: str | None) -> list[str]:
    tracked = git("diff", "--name-only", base or "HEAD", check=False).splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard", check=False).splitlines()
    return tracked + untracked


def inside(path: str, unit_path: str) -> bool:
    unit_path = unit_path.strip("/")
    return unit_path in ("", ".") or path == unit_path or path.startswith(unit_path + "/")


def write_changelog(path: Path, version: str, category: str, entry: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else CHANGELOG_HEADER
    section = f"## [{version}] - {date.today().isoformat()}\n\n### {category}\n\n{entry}\n"
    match = re.search(r"^## \[(?!Unreleased\])", text, re.M)
    if match:
        text = text[:match.start()] + section + "\n" + text[match.start():]
    else:
        text = text.rstrip("\n") + "\n\n" + section
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def cmd_release(args, config) -> int:
    sl = Slice(args.slice)
    if sl.status != "done":
        fail(f"{sl.id} is {sl.status}; release requires done")
    change = sl.front.get("change")
    if change not in CHANGES:
        fail(f"{sl.id} has an invalid change type")
    commit_type, category, level = CHANGES[change]
    breaking = sl.front.get("breaking", False)
    units = config.get("units") or [{"name": "", "paths": ["."]}]
    if isinstance(breaking, list):
        unknown = set(breaking) - {u.get("name", "") for u in units}
        if unknown:
            fail(f"breaking lists unknown release units: {', '.join(sorted(unknown))}")
    files = changed_files(sl.front.get("base"))
    plan = []
    for unit in units:
        name, paths = unit.get("name", ""), unit.get("paths", ["."])
        if name and not any(inside(f, p) for f in files for p in paths):
            continue
        unit_breaking = breaking is True or (isinstance(breaking, list) and name in breaking)
        version = ".".join(map(str, bump(latest_version(name), "major" if unit_breaking else level)))
        plan.append({
            "name": name or "(root)",
            "breaking": unit_breaking,
            "version": version,
            "tag": f"{name}/v{version}" if name else f"v{version}",
            "changelog": ROOT / paths[0] / "CHANGELOG.md",
        })

    title = sl.front.get("title", sl.id)
    subject = title if title[:2].isupper() else title[:1].lower() + title[1:]
    bang = "!" if any(p["breaking"] for p in plan) else ""
    trailers = ([f"BREAKING CHANGE: {sl.goal()}"] if bang else []) + [f"Slice: {sl.id}"] + args.trailer
    message = f"{commit_type}({sl.front.get('capability')}){bang}: {subject}\n\n{sl.goal()}\n\n" + "\n".join(trailers) + "\n"

    print(message)
    if not plan:
        print("no release unit affected: commit only, no tags")
    for p in plan:
        print(f"  {p['name']:<12} {p['tag']:<20} {p['changelog'].relative_to(ROOT).as_posix()}")
    if not args.apply:
        print("\ndry run: pass --apply to write changelogs, commit staged changes and tag")
        return 0

    for p in plan:
        link = Path(os.path.relpath(sl.spec, p["changelog"].parent)).as_posix()
        prefix = "**BREAKING:** " if p["breaking"] else ""
        write_changelog(p["changelog"], p["version"], category, f"- {prefix}{sl.goal()} ([{sl.id}]({link}))")
        git("add", str(p["changelog"]))
    subprocess.run(["git", "commit", "-q", "-F", "-"], cwd=ROOT, input=message, text=True, check=True)
    for p in plan:
        git("tag", "-a", p["tag"], "-m", f"{title} ({sl.id})")
    print(f"committed {git('rev-parse', '--short', 'HEAD').strip()} and tagged {', '.join(p['tag'] for p in plan) or 'nothing'}")
    return 0


def main() -> int:
    global ROOT, AGENTS
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status").add_argument("slice", nargs="?")
    for name in ("check", "advance", "reopen"):
        commands.add_parser(name).add_argument("slice")
    commands.add_parser("next-id").add_argument("kind", choices=["idea", "slice", "adr"])
    release = commands.add_parser("release")
    release.add_argument("slice")
    release.add_argument("--apply", action="store_true")
    release.add_argument("--trailer", action="append", default=[])
    args = parser.parse_args()

    ROOT = find_root()
    AGENTS = ROOT / ".agents"
    handlers = {
        "status": cmd_status, "check": cmd_check, "advance": cmd_advance, "reopen": cmd_reopen,
        "next-id": cmd_next_id, "release": cmd_release,
    }
    return handlers[args.command](args, load_config())


if __name__ == "__main__":
    sys.exit(main())
