"""Sanity checks for the hand-built T1-T9 fixture page and its draft ground truth."""

import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from contract.enums import IssueType, Role, Severity
from store.config import load

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "data/pages/fixture-01.html").read_text()
GT = json.loads((ROOT / "data/ground_truth/fixture-01.draft.json").read_text())


class Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = Counter()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if "id" in a:
            self.ids[a["id"]] += 1


parsed = Collect()
parsed.feed(PAGE)


def ratio(fg, bg):
    def lum(h):
        c = [int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_nine_defects_present_in_ground_truth():
    assert {i["defect"] for i in GT["items"]} == {f"T{n}" for n in range(1, 10)}
    assert Counter(i["defect"] for i in GT["items"])["T2"] == 5  # five repeated links, five items


def test_ground_truth_fields_valid_against_contract_enums_and_matrix():
    matrix = {c.criterion: c for c in load().config.matrix.criteria}
    for item in GT["items"]:
        assert Severity(item["severity"])
        assert IssueType(item["issue_type"])
        assert Role(item["affected_user_group"])
        assert all(Role(r) for r in item["expected_roles"])
        assert all(c in matrix for c in item["acceptable_criteria"])
        assert item["issue_type"] == matrix[item["acceptable_criteria"][0]].type.value
    assert all(c in matrix for c in GT["no_issue_criteria"])


def test_id_selectors_resolve_to_exactly_one_element():
    for item in GT["items"]:
        sel = item["selector"]
        if re.fullmatch(r"#[\w-]+", sel):
            assert parsed.ids[sel[1:]] == 1, sel


def test_defects_are_in_the_page():
    assert 'alt="image123.png"' in PAGE
    assert PAGE.count(">Click here</a>") == 5
    assert 2.7 < ratio("#9b9b9b", "#ffffff") < 2.9 and "color: #9b9b9b" in PAGE
    full = next(a for t, a in parsed.tags if a.get("id") == "fullname")
    assert "placeholder" in full and "aria-label" not in full
    assert not re.search(r'<label[^>]*for="fullname"', PAGE)
    assert 'class="field-alert"' in PAGE and '<p id="phone-msg">Invalid</p>' in PAGE
    assert 'role="dialog"' in PAGE and ".focus()" not in PAGE  # modal never moves focus
    assert (
        "position: sticky" in PAGE and "scroll-padding" not in PAGE and "scroll-margin" not in PAGE
    )
    assert [m for m in ("Info", "More", "Stuff") if f"<h2>{m}</h2>" in PAGE] == [
        "Info",
        "More",
        "Stuff",
    ]


def test_controls_and_decoys_present_and_clean():
    ids = parsed.ids
    assert ids["fit-photo"] == 1 and ids["email"] == 1 and re.search(r'for="email"', PAGE)
    fit = next(a for t, a in parsed.tags if a.get("id") == "fit-photo")
    assert len(fit["alt"]) > 10
    assert 'aria-hidden="true"' in PAGE and 'focusable="false"' in PAGE  # decorative icon hidden
    assert 'alt="" width="640"' in PAGE  # decorative image, correct empty alt
    assert '<html lang="en">' in PAGE and 'href="#main"' in PAGE


def test_page_does_not_leak_defects():
    assert "<!--" not in PAGE
    for word in ("defect", "bug", "violation", "T1", "WCAG"):
        assert word not in PAGE
