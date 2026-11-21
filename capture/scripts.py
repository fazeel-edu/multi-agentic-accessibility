"""Browser-side scripts. Every capture runs the same scripts (FOCUS_SCRIPT_VERSION in capture.json)."""

import json

FOCUS_SCRIPT_VERSION = "1"
MAX_TAB_STEPS = 120

# Shared helper: canonical path, identical in scheme to tools.element.canonical_path.
_PATH = """
const cpath = (el) => {
  const parts = [];
  while (el && el.nodeType === 1) {
    const p = el.parentElement;
    let i = 1;
    if (p) for (const s of p.children) { if (s === el) break; if (s.tagName === el.tagName) i++; }
    parts.push(el.tagName.toLowerCase() + '[' + i + ']');
    el = p;
  }
  return '/' + parts.reverse().join('/');
};
"""

STYLE_PROPS = [
    "display",
    "visibility",
    "position",
    "z-index",
    "opacity",
    "overflow",
    "color",
    "background-color",
    "background-image",
    "font-size",
    "font-weight",
    "line-height",
    "text-decoration-line",
    "outline-style",
    "outline-width",
    "outline-color",
    "box-shadow",
    "border-top-style",
    "border-top-width",
    "border-top-color",
]

COMPUTED_STYLES = (
    "() => {"
    + _PATH
    + "const props = "
    + json.dumps(STYLE_PROPS)
    + """;
  const out = {};
  for (const el of document.querySelectorAll('html, body, body *')) {
    if (['SCRIPT', 'STYLE'].includes(el.tagName)) continue;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const rec = {};
    for (const p of props) rec[p] = cs.getPropertyValue(p);
    rec.rect = [Math.round(r.x + scrollX), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)];
    out[cpath(el)] = rec;
  }
  return out;
}"""
)

CONTRAST = (
    "() => {"
    + _PATH
    + """
  const parse = (c) => {
    const m = /rgba?\\(([^)]+)\\)/.exec(c);
    if (!m) return null;
    const [r, g, b, a = 1] = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number);
    return { r, g, b, a };
  };
  const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const lum = (c) => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const over = (f, b) => ({ r: f.r * f.a + b.r * (1 - f.a), g: f.g * f.a + b.g * (1 - f.a), b: f.b * f.a + b.b * (1 - f.a), a: 1 });
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    if (['SCRIPT', 'STYLE'].includes(el.tagName)) continue;
    const text = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).join(' ').trim();
    if (!text) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    let hidden = false;
    for (let p = el; p; p = p.parentElement) if (getComputedStyle(p).display === 'none') hidden = true;
    if (hidden) continue;
    const layers = [];
    let indeterminate = false;
    let source = 'canvas';
    for (let p = el; p; p = p.parentElement) {
      const s = getComputedStyle(p);
      if (s.backgroundImage !== 'none') indeterminate = true;
      const bg = parse(s.backgroundColor);
      if (bg && bg.a > 0) { layers.push(bg); if (bg.a === 1) { source = p === el ? 'element' : 'ancestor'; break; } }
    }
    let bg = { r: 255, g: 255, b: 255, a: 1 };
    for (const l of layers.reverse()) bg = over(l, bg);
    const fgRaw = parse(cs.color);
    if (!fgRaw) continue;
    const fg = over(fgRaw, bg);
    const hi = Math.max(lum(fg), lum(bg)), lo = Math.min(lum(fg), lum(bg));
    const ratio = (hi + 0.05) / (lo + 0.05);
    const size = parseFloat(cs.fontSize);
    const bold = parseInt(cs.fontWeight, 10) >= 700;
    const large = size >= 24 || (size >= 18.66 && bold);
    const need = large ? 3 : 4.5;
    out.push({
      path: cpath(el), text: text.slice(0, 60), color: cs.color, background: 'rgb(' + [bg.r, bg.g, bg.b].map(Math.round).join(', ') + ')',
      background_source: source, background_indeterminate: indeterminate, ratio: Math.round(ratio * 100) / 100,
      font_size_px: size, bold: bold, large_text: large, required: need, passes: ratio >= need,
    });
  }
  return out;
}"""
)

# Focus state of the active element after a key press.
FOCUS_STATE = (
    "() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => {"
    + _PATH
    + """
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) { resolve(null); return; }
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  const vw = innerWidth, vh = innerHeight;
  const pts = [[0.5, 0.5], [0.1, 0.1], [0.9, 0.1], [0.1, 0.9], [0.9, 0.9]].map(([fx, fy]) => [r.x + r.width * fx, r.y + r.height * fy]);
  let covered = 0, by = null, sampled = 0;
  for (const [x, y] of pts) {
    if (x < 0 || y < 0 || x >= vw || y >= vh) continue;
    sampled++;
    const top = document.elementFromPoint(x, y);
    if (top && top !== el && !el.contains(top) && !top.contains(el)) { covered++; by = by || cpath(top); }
  }
  const outline = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
  resolve({
    path: cpath(el), tag: el.tagName.toLowerCase(), id: el.id || null,
    name: (el.getAttribute('aria-label') || el.textContent || el.getAttribute('placeholder') || el.value || '').trim().slice(0, 60),
    rect_in_viewport: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
    in_viewport: r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw,
    focus_indicator: outline ? 'outline' : (cs.boxShadow !== 'none' ? 'box-shadow' : 'none'),
    sampled_points: sampled, obscured_points: covered, obscured_by: by,
    inside_dialog: !!el.closest('[role=dialog], [role=alertdialog], dialog'),
  });
})))
"""
)

# Dialogs currently visible, as canonical paths.
VISIBLE_DIALOGS = (
    "() => {"
    + _PATH
    + """
  return [...document.querySelectorAll('[role=dialog], [role=alertdialog], dialog')]
    .filter((d) => { const s = getComputedStyle(d); return s.display !== 'none' && s.visibility !== 'hidden' && !d.hidden; })
    .map(cpath);
}"""
)

# Non-submit buttons that could open something, as canonical paths.
CANDIDATE_OPENERS = (
    "() => {"
    + _PATH
    + """
  return [...document.querySelectorAll('button:not([type=submit]):not([disabled]), [role=button]')]
    .filter((b) => !b.closest('[role=dialog], [role=alertdialog], dialog'))
    .filter((b) => { const s = getComputedStyle(b); return s.display !== 'none' && s.visibility !== 'hidden'; })
    .slice(0, 20).map(cpath);
}"""
)
