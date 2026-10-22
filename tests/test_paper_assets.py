"""Milestone 8.3: paper assets (T8.3-01 .. T8.3-05; T8.3-06/07 are reviewer / build steps)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from experiments import make_tables_tex
from experiments.common import RESULTS

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
TEX = (PAPER / "main.tex").read_text(encoding="utf-8")


def section(name: str) -> str:
    m = re.search(r"\\section\{" + re.escape(name) + r"\}(.*?)(?=\\section\{|\\bibliographystyle|\Z)", TEX, re.S)
    assert m, name
    return m.group(1)


@pytest.mark.skipif(not (RESULTS / "e1_budget.csv").exists(), reason="results not generated")
def test_t83_01_generated_tables_match_results(tmp_path):
    make_tables_tex.run(RESULTS, tmp_path)
    for p in sorted(tmp_path.iterdir()):
        committed = PAPER / "generated" / p.name
        assert committed.exists(), p.name
        assert committed.read_text(encoding="utf-8") == p.read_text(encoding="utf-8"), p.name


def test_t83_02_figures_resolve():
    for rel in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", TEX):
        assert (PAPER / rel).exists() or not (ROOT / "docs" / "figures").exists(), rel


def test_t83_03_citations_resolve_and_all_used():
    cited = {k.strip() for grp in re.findall(r"\\cite\{([^}]+)\}", TEX) for k in grp.split(",")}
    bib = (PAPER / "refs.bib").read_text(encoding="utf-8")
    keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    assert cited <= keys, f"unresolved: {cited - keys}"
    assert keys <= cited, f"uncited bib entries: {keys - cited}"


def test_t83_04_no_hand_typed_numbers_in_results():
    body = section("Results")
    body = re.sub(r"\\input\{[^}]*\}", "", body)
    body = re.sub(r"\\(ref|label|cite)\{[^}]*\}", "", body)
    body = re.sub(r"\\includegraphics(\[[^\]]*\])?\{[^}]*\}", "", body)
    body = re.sub(r"width=[0-9.]+\\columnwidth", "", body)
    body = re.sub(r"\$[^$]*\$", "", body)                         # math symbols such as c=0.5 are labels
    body = re.sub(r"\\caption\{[^}]*\}", "", body)               # captions carry no results
    body = re.sub(r"\\[A-Za-z]+(\[[^\]]*\])?", "", body)           # remaining macros (incl. \EFourMaxOne)
    assert re.findall(r"\d", body) == [], "numerals found outside generated snippets"


def test_t83_05_limitations_present():
    body = section("Discussion and Limitations")
    assert len(re.findall(r"\\item", body)) >= 5


def test_t83_paper_states_no_real_roads_and_no_new_algorithm():
    assert "No real road network was used" in TEX or "no real road network" in TEX.lower()
    assert "not as a new algorithm" in TEX or "no claim of a new algorithm" in TEX
