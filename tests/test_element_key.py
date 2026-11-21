import json
from pathlib import Path

import pytest

from contract.element_key import NodeKey, NodesKey, PageKey, UnresolvedKey
from tools.element import canonical_path, element_key

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = (ROOT / "data/pages/fixture-01.html").read_text()
GT = json.loads((ROOT / "data/ground_truth/fixture-01.draft.json").read_text())

LIST = "<html><body><ul><li>a</li><li>b</li><p>x</p><li>c</li></ul></body></html>"


def test_canonical_path_uses_nth_of_type():
    assert element_key(LIST, "li:nth-child(4)") == NodeKey(path="/html[1]/body[1]/ul[1]/li[3]")
    assert element_key(LIST, "p") == NodeKey(path="/html[1]/body[1]/ul[1]/p[1]")
    assert element_key(LIST, "html") == NodeKey(path="/html[1]")


def test_css_and_xpath_to_same_node_give_equal_keys():
    css = element_key(FIXTURE, "#hero")
    assert css == element_key(FIXTURE, '//img[@id="hero"]')
    assert css == element_key(FIXTURE, "/html/body/main/section[1]/img[1]")
    assert css == element_key(FIXTURE, "main > section:first-child > img:first-of-type")
    assert css == element_key(FIXTURE, "  #hero  ")
    assert isinstance(css, NodeKey)


def test_equal_across_attribute_order_comments_and_whitespace():
    a = '<html><body><!-- c --><p class="x" id="p">hi</p></body></html>'
    b = '<html>\n<body>\n<p id="p" class="x">hi</p>\n</body>\n</html>'
    assert element_key(a, "#p") == element_key(b, "#p")


def test_selector_matching_nothing_is_unresolved():
    key = element_key(FIXTURE, "#does-not-exist")
    assert key == UnresolvedKey(raw="#does-not-exist")
    assert element_key(FIXTURE, "//table") == UnresolvedKey(raw="//table")


@pytest.mark.parametrize("bad", ["div[", "((", "", "   ", "a:hover::before", "//*[", "1 + 1"])
def test_bad_selectors_never_raise_and_are_unresolved(bad):
    assert isinstance(element_key(FIXTURE, bad), UnresolvedKey)


def test_unresolved_never_equals_a_node_key():
    node = element_key(FIXTURE, "#hero")
    assert element_key(FIXTURE, "#nope") != node
    assert element_key(FIXTURE, "#nope").kind == "unresolved"


def test_none_selector_is_page_scope():
    assert element_key(FIXTURE, None) == PageKey()


def test_multiple_matches_become_nodes_in_document_order():
    key = element_key(FIXTURE, "section#reviews a")
    assert isinstance(key, NodesKey) and len(key.paths) == 6
    assert key == element_key(FIXTURE, "//section[@id='reviews']//a")
    assert list(key.paths) == sorted(key.paths, key=lambda p: FIXTURE_ORDER[p])


def test_xpath_attribute_and_text_results_map_to_owning_element():
    assert element_key(FIXTURE, "//*[@id='hero']/@alt") == element_key(FIXTURE, "#hero")
    assert element_key(FIXTURE, "//*[@id='phone-msg']/text()") == element_key(FIXTURE, "#phone-msg")


def test_xpath_returning_non_nodes_is_unresolved():
    assert isinstance(element_key(FIXTURE, "count(//a)"), UnresolvedKey)


def test_empty_or_garbage_html_is_unresolved():
    assert isinstance(element_key("", "p"), UnresolvedKey)
    assert isinstance(element_key("   ", "p"), UnresolvedKey)


def test_fixture_ground_truth_selectors_all_resolve():
    keys = {}
    for item in GT["items"]:
        key = element_key(FIXTURE, item["selector"])
        assert isinstance(key, NodeKey), item["selector"]
        keys[(item["defect"], item["selector"])] = key
    t2 = [k for (d, _), k in keys.items() if d == "T2"]
    assert len(set(t2)) == 5  # five Click here links stay five distinct items
    for sel in GT["controls"] + GT["decoys"]:
        assert not isinstance(element_key(FIXTURE, sel), UnresolvedKey), sel


def test_keys_are_hashable_and_json_roundtrip():
    key = element_key(FIXTURE, "#hero")
    assert {key: 1}[element_key(FIXTURE, '//img[@id="hero"]')] == 1
    assert NodeKey.model_validate_json(key.model_dump_json()) == key


def _order():
    from tools.element import _parse

    root = _parse(FIXTURE)
    return {canonical_path(e): i for i, e in enumerate(root.iter()) if isinstance(e.tag, str)}


FIXTURE_ORDER = _order()


def test_xpath_forms_without_a_leading_slash_are_understood():
    assert element_key(FIXTURE, "descendant::img[@id='hero']") == element_key(FIXTURE, "#hero")


def test_lone_surrogates_do_not_raise():
    assert isinstance(element_key("<p>\ud800</p>", "p"), NodeKey)
    assert isinstance(element_key(FIXTURE, "\ud800"), UnresolvedKey)
