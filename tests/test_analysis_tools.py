import asyncio
import json

import pytest

from auditors.role_auditor.sdk_tools import build_role_server, role_tools
from auditors.role_auditor.tool_table import ROLE_TOOLS, SERVER_NAME, allowed_tool_names
from contract.enums import Role
from tests.conftest import make_capture
from tools import axe_reader, contrast, focus_trace, readability
from tools.element import element_key, element_text
from tools.registry import TOOLS

# --- contrast ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("fg", "bg", "ratio"),
    [
        ("#000", "#fff", 21.0),
        ("#ffffff", "#ffffff", 1.0),
        ("#767676", "#fff", 4.54),
        ("rgb(153, 153, 153)", "rgb(255,255,255)", 2.85),
    ],
)
def test_contrast_ratio_known_values(fg, bg, ratio):
    assert contrast.contrast_ratio(fg, bg) == ratio


def test_contrast_check_uses_large_text_threshold():
    assert contrast.check("#9b9b9b", "#fff")["passes"] is False
    assert contrast.check("#767676", "#fff", 16)["passes"] is True
    assert contrast.check("#949494", "#fff", 24)["passes"] is True  # 3.03:1, large text needs 3:1
    assert contrast.check("#949494", "#fff", 16)["passes"] is False
    assert contrast.check("#949494", "#fff", 19, bold=True)["large_text"] is True


@pytest.mark.parametrize("bad", ["red", "#12", "rgb(300,0,0)", "", "hsl(1,2%,3%)"])
def test_unsupported_colours_raise(bad):
    with pytest.raises(ValueError):
        contrast.parse_color(bad)


def test_failing_rows_report_the_t3_defect_on_the_fixture(fixture_capture):
    rows = contrast.failing_rows(fixture_capture)
    assert [r["ratio"] for r in rows] == [2.78]
    assert contrast.failing_rows(fixture_capture, "#shipping-note") == rows
    assert contrast.failing_rows(fixture_capture, "#hero") == []


# --- readability ------------------------------------------------------------


def test_readability_orders_plain_below_dense_text():
    plain = readability.score("The cat sat on the mat. It was happy.")
    dense = readability.score(
        "Notwithstanding aforementioned stipulations, indemnification obligations necessitate comprehensive documentation."
    )
    assert plain["reading_ease"] > 80
    assert dense["reading_ease"] < 0
    assert plain["grade_level"] < dense["grade_level"]
    assert plain["words"] == 9 and plain["sentences"] == 2


def test_readability_of_empty_text():
    assert readability.score("") == {
        "words": 0,
        "sentences": 0,
        "reading_ease": None,
        "grade_level": None,
    }
    assert readability.score("123 !!!")["words"] == 0


def test_element_text_reads_a_selector():
    html = make_capture().html
    assert element_text(html, "#phone-msg") == "Invalid"
    assert element_text(html, "#nope") is None
    assert element_text(html, "") is None


# --- axe reader and focus trace on the real fixture -------------------------


def test_axe_reader_returns_the_stored_violation(fixture_capture):
    rows = axe_reader.violations(fixture_capture)
    assert [r["rule_id"] for r in rows] == ["color-contrast"]
    assert rows[0]["nodes"][0]["selector"] == "#shipping-note"
    assert "wcag143" in rows[0]["tags"]
    assert axe_reader.violations(fixture_capture, "image-alt") == []
    assert axe_reader.needs_review(fixture_capture) == []


def test_focus_trace_summary_shows_t7_and_t8_on_the_fixture(fixture_capture):
    s = focus_trace.summarize(fixture_capture)
    hidden = {element_key(fixture_capture.html, f"#more-{n}").path for n in (1, 2, 3)}
    assert hidden <= set(s["obscured"])
    assert [x["id"] for x in s["tab_forward"] if x["id"]][:2] == ["size-btn", "more-1"]
    probe = next(p for p in s["dialogs"]["probes"] if p["opened"])
    assert probe["focus_after_open"]["inside_dialog"] is False
    assert s["tab_forward_ended"] in {"left_document", "revisit", "cap"}


def test_tools_work_on_an_empty_capture():
    c = make_capture()
    assert axe_reader.violations(c) == [] and focus_trace.summarize(c)["tab_forward"] == []
    assert contrast.failing_rows(c) == []


# --- registry and SDK wrappers ---------------------------------------------


def run(spec_name, capture, **args):
    return json.loads(TOOLS[spec_name].run(capture, args))


def test_registry_tools_return_json_and_report_bad_input():
    c = make_capture()
    assert run("contrast_check", c, foreground="#9b9b9b", background="#fff")["ratio"] == 2.78
    assert "error" in run("contrast_check", c, foreground="red", background="#fff")
    assert run("readability", c, selector="#phone-msg")["words"] == 1
    assert "error" in run("readability", c, selector="#nope")
    assert "error" in run("readability", c)


def test_every_role_tool_exists_in_the_registry():
    assert {n for names in ROLE_TOOLS.values() for n in names} <= set(TOOLS)
    assert set(ROLE_TOOLS) == set(Role)


def test_each_role_server_holds_only_that_roles_tools():
    c = make_capture()
    for role, names in ROLE_TOOLS.items():
        assert [t.name for t in role_tools(role, c)] == list(names)
        server = build_role_server(role, c)
        assert (server is None) == (not names)
        if server:
            assert server["type"] == "sdk" and server["name"] == SERVER_NAME
    assert allowed_tool_names(Role.KEYBOARD) == [
        f"mcp__{SERVER_NAME}__{n}" for n in ROLE_TOOLS[Role.KEYBOARD]
    ]
    assert allowed_tool_names(Role.INCLUSIVE_DESIGN) == []


def test_least_tools_per_role():
    assert "focus_trace" not in ROLE_TOOLS[Role.SCREEN_READER]
    assert "contrast_check" not in ROLE_TOOLS[Role.KEYBOARD]
    assert ROLE_TOOLS[Role.COGNITIVE] == ("readability",)
    assert not any("axe" in t for t in ROLE_TOOLS[Role.COLOUR_VISUAL])


def test_sdk_handler_returns_text_content_and_flags_errors():
    c = make_capture()
    tool = next(t for t in role_tools(Role.COLOUR_VISUAL, c) if t.name == "contrast_check")
    ok = asyncio.run(tool.handler({"foreground": "#000", "background": "#fff"}))
    assert json.loads(ok["content"][0]["text"])["ratio"] == 21.0 and "is_error" not in ok
    bad = asyncio.run(tool.handler({"foreground": "#000"}))  # background missing
    assert bad["is_error"] is True and "error" in bad["content"][0]["text"]


def test_tools_make_no_browser_or_network_calls(monkeypatch):
    import socket

    def boom(*a, **k):
        raise AssertionError("network access from an analysis tool")

    monkeypatch.setattr(socket.socket, "connect", boom)
    c = make_capture()
    for name in TOOLS:
        TOOLS[name].run(c, {"foreground": "#000", "background": "#fff", "text": "Hello there."})
