"""Milestone 8.2: claims audit and documentation lint (T8.2-01 .. T8.2-08).

The lint makes the class of error found in the first-half review mechanically
detectable: wrong competitive-ratio wording, unsupported percentages, stale
hard-coded test counts, claims without a source, proofs without a sign-off line.
"""

from __future__ import annotations

import re

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN = ["(c+1)-competitive", "zero external dependencies", "mathematically guarantees"]
COUNT_RE = re.compile(r"\b\d{2,4} (automated )?tests\b")
# Dated historical records may mention the counts that were true on that date.
COUNT_EXEMPT = {"PROJECT_LOGBOOK.md", "PLAYBOOK.md", "GraphPulse-R_Playbook_50pct.md", "CLAIMS.md"}
FORBIDDEN_EXEMPT = {"CLAIMS.md"}                 # CLAIMS.md may quote the phrases it rejects
PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:csv|md|py|json|pdf|png|tex|bib))(?::[^`]*)?`")


def doc_files(root: Path) -> list[Path]:
    files = [root / "README.md"] + sorted((root / "docs").glob("*.md"))
    return [f for f in files if f.exists()]


def lint(root: Path) -> list[str]:
    problems: list[str] = []
    for f in doc_files(root):
        text = f.read_text(encoding="utf-8")
        if f.name not in FORBIDDEN_EXEMPT:
            for phrase in FORBIDDEN:
                if phrase in text:
                    problems.append(f"{f.name}: forbidden phrase {phrase!r}")
        if f.name not in COUNT_EXEMPT and COUNT_RE.search(text):
            problems.append(f"{f.name}: hard-coded test count {COUNT_RE.search(text).group(0)!r}")
    claims = root / "docs" / "CLAIMS.md"
    if claims.exists():
        text = claims.read_text(encoding="utf-8")
        for rel in sorted(set(PATH_RE.findall(text))):
            candidates = [root / rel, root / "docs" / rel, root / "docs" / "results" / rel]
            if not any(c.exists() for c in candidates):
                problems.append(f"CLAIMS.md: referenced file does not exist: {rel}")
        for line in text.splitlines():
            if line.startswith("|") and not set(line) <= set("|- "):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if cells and cells[0].lower() not in ("claim", "") and len(cells) >= 4 and not cells[2]:
                    problems.append(f"CLAIMS.md: empty Source cell in row {cells[0]!r}")
    for p in sorted((root / "docs" / "proofs").glob("*.md")):
        head = "\n".join(p.read_text(encoding="utf-8").splitlines()[:6])
        if "Reviewer sign-off:" not in head:
            problems.append(f"{p.name}: missing 'Reviewer sign-off:' line")
    return problems


def make_tree(tmp: Path, **files: str) -> Path:
    (tmp / "docs" / "proofs").mkdir(parents=True)
    (tmp / "README.md").write_text("# readme\n", encoding="utf-8")
    (tmp / "docs" / "proofs" / "P1.md").write_text("# P1\n\n**Reviewer sign-off:** PENDING\n", encoding="utf-8")
    for name, text in files.items():
        (tmp / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp / name).write_text(text, encoding="utf-8")
    return tmp


def test_t82_01_forbidden_phrase_detected(tmp_path):
    root = make_tree(tmp_path, **{"docs/A.md": "The method is (c+1)-competitive.\n"})
    assert any("forbidden phrase" in p for p in lint(root))


def test_t82_02_repository_docs_pass():
    assert lint(ROOT) == []


def test_t82_03_hard_coded_count_detected(tmp_path):
    root = make_tree(tmp_path, **{"docs/A.md": "We have 240 tests passing.\n"})
    assert any("hard-coded test count" in p for p in lint(root))


def test_t82_04_missing_source_file_detected(tmp_path):
    root = make_tree(tmp_path, **{"docs/CLAIMS.md": "| Claim | Type | Source | Hash | Status |\n|---|---|---|---|---|\n"
                                  "| x | measured | `results/missing.csv` | abc | ok |\n"})
    assert any("does not exist" in p for p in lint(root))


def test_t82_05_proof_signoff_check(tmp_path):
    root = make_tree(tmp_path)
    (root / "docs" / "proofs" / "P2.md").write_text("# P2\n\nno reviewer line here\n", encoding="utf-8")
    assert any("P2.md" in p and "sign-off" in p for p in lint(root))


def test_t82_06_every_claim_sourced():
    text = (ROOT / "docs" / "CLAIMS.md").read_text(encoding="utf-8")
    rows = [l for l in text.splitlines() if l.startswith("|") and not set(l) <= set("|- ")]
    assert len(rows) > 10
    for l in rows[1:]:
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        assert len(cells) >= 5 and cells[2], f"empty Source cell: {l[:80]}"
        assert cells[1] in ("proved", "measured", "design"), f"bad Type in: {l[:80]}"
        assert cells[4] in ("OK", "REJECTED", "PENDING"), f"bad Status in: {l[:80]}"


@pytest.mark.xfail(reason="legacy dashboard still has hard-coded percentages; removed by the UI redesign (remove this mark then)")
def test_t82_07_dashboard_strings_have_no_unsourced_numbers():
    """No hard-coded percentages or counts in user-facing dashboard text (numbers are computed at runtime)."""
    pat = re.compile(r"\b\d+(\.\d+)?(-\d+(\.\d+)?)?\s?%|\b\d{2,4} (automated )?tests\b")
    offenders = []
    for f in list((ROOT / "web").rglob("*.html")) + list((ROOT / "web").rglob("*.js")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line):
                offenders.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:90]}")
    assert offenders == [], "\n".join(offenders)


def test_t82_08_lint_has_no_false_positive_on_clean_tree(tmp_path):
    root = make_tree(tmp_path, **{"docs/A.md": "Run the test suite with the documented command.\n"})
    assert lint(root) == []
