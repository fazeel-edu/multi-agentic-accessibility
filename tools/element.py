"""element_key: the only selector normaliser (AD-15). Pure; no files, no browser.

Parses Capture HTML with one pinned parser (lxml.html, libxml2) and resolves a CSS
selector or XPath to a canonical key. Canonical path = tag plus 1-based `nth-of-type`
index at every level from the root, e.g. `/html[1]/body[1]/main[1]/img[2]`.
"""

from functools import lru_cache

from cssselect import GenericTranslator
from cssselect.parser import SelectorError
from lxml import etree, html

from contract.element_key import ElementKey, NodeKey, NodesKey, PageKey, UnresolvedKey

PARSER = "lxml.html"

_XPATH_STARTS = ("/", "(", "./", "../", ".//")
_TRANSLATOR = GenericTranslator()


@lru_cache(maxsize=8)
def _parse(capture_html: str) -> html.HtmlElement | None:
    if not capture_html.strip():
        return None
    try:
        # Encode so documents carrying an XML/encoding declaration still parse.
        data = capture_html.encode("utf-8", errors="replace")
        return html.document_fromstring(data, parser=_html_parser())
    except (etree.ParserError, etree.XMLSyntaxError):
        return None


def _html_parser() -> html.HTMLParser:
    return html.HTMLParser(encoding="utf-8", remove_comments=True, remove_pis=True)


def canonical_path(el: etree._Element) -> str:
    parts = []
    while el is not None:
        parent = el.getparent()
        if parent is None:
            parts.append(f"{el.tag}[1]")
        else:
            same = [s for s in parent if s.tag == el.tag]
            parts.append(f"{el.tag}[{same.index(el) + 1}]")
        el = parent
    return "/" + "/".join(reversed(parts))


def _is_xpath(selector: str) -> bool:
    return selector.startswith(_XPATH_STARTS)


def _to_xpath(selector: str) -> str:
    """XPath if it looks like one; else CSS, falling back to XPath when CSS cannot parse it
    (for example `descendant::a`). Relative XPath is evaluated from the root element."""
    if _is_xpath(selector):
        return selector
    try:
        return _TRANSLATOR.css_to_xpath(selector)
    except SelectorError:
        return selector


def _elements(root: html.HtmlElement, selector: str) -> list[etree._Element]:
    found = root.xpath(_to_xpath(selector))
    if not isinstance(found, list):  # number, boolean or string result
        return []
    elements = []
    for item in found:
        if isinstance(item, etree._Element):
            node = item
        else:  # attribute or text result: use the element that owns it
            node = item.getparent() if hasattr(item, "getparent") else None
        if node is not None and isinstance(node.tag, str):
            elements.append(node)
    return elements


def element_key(capture_html: str, selector: str | None) -> ElementKey:
    """Resolve `selector` against the Capture HTML.

    None means the problem has no element (page scope). Never raises on bad input:
    a selector that is invalid or matches nothing returns `unresolved`.
    """
    if selector is None:
        return PageKey()
    root = _parse(capture_html)
    if root is None or not selector.strip():
        return UnresolvedKey(raw=selector)
    try:
        elements = _elements(root, selector.strip())
    except (
        SelectorError,
        etree.LxmlError,
        ValueError,
        TypeError,
        NotImplementedError,
        RecursionError,
    ):
        return UnresolvedKey(raw=selector)
    paths = list(dict.fromkeys(canonical_path(e) for e in elements))
    if not paths:
        return UnresolvedKey(raw=selector)
    if len(paths) == 1:
        return NodeKey(path=paths[0])
    order = {canonical_path(e): i for i, e in enumerate(root.iter()) if isinstance(e.tag, str)}
    return NodesKey(paths=tuple(sorted(paths, key=order.__getitem__)))


def element_text(capture_html: str, selector: str) -> str | None:
    """Visible-ish text of the first element a selector resolves to; None if it resolves to none."""
    root = _parse(capture_html)
    if root is None or not selector.strip():
        return None
    try:
        elements = _elements(root, selector.strip())
    except (
        SelectorError,
        etree.LxmlError,
        ValueError,
        TypeError,
        NotImplementedError,
        RecursionError,
    ):
        return None
    if not elements:
        return None
    return " ".join(elements[0].text_content().split())


def visible_text(capture_html: str) -> str:
    """Readable text of the page: head, scripts, styles and hidden elements removed (their
    following text is kept), whitespace collapsed."""
    root = _parse(capture_html)
    if root is None:
        return ""
    for bad in root.xpath(
        "//head|//script|//style|//template|//noscript|//*[@hidden]|//*[@aria-hidden='true']"
    ):
        if bad.getparent() is not None:
            bad.drop_tree()  # lxml.html: removes the node, keeps its tail text
    return "\n".join(line for line in (" ".join(t.split()) for t in root.itertext()) if line)
