#!/usr/bin/env python3
"""
Build the namespaced native-embed artifacts for The Gala: Fire & Ice Edition:
  - styles-embed.css  (every class prefixed `ff-`, every selector scoped under `.ottff`)
  - embed-native.html (body extracted, classes prefixed, asset URLs absolute,
                      Meta Pixel stripped — parent Webflow page already has it,
                      wrapped in <div class="ottff">)
  - script-embed.js  (class selectors prefixed to match)

Mirrors the SF Fit Fest pattern (see ../Fit Fest Programming/site/*-embed.*).
"""

import re
from pathlib import Path

HERE = Path(__file__).parent
REPO_BASE = "https://gabrielgalarza.github.io/ott-gala"
PFX, SCOPE = "ff-", ".ottff"
REGISTER_URL = "https://events.sweatpals.com/4cf478e4"

RESET = """/* ===== Embed reset: isolate from host (Webflow) styles ===== */
.ottff { width:100%; display:block; font-family:"Inter",system-ui,sans-serif; color:#111; line-height:1.55; -webkit-font-smoothing:antialiased; }
.ottff *, .ottff *::before, .ottff *::after { box-sizing:border-box; font-family:inherit; }
.ottff h1,.ottff h2,.ottff h3,.ottff h4,.ottff h5,.ottff h6,.ottff figure { margin:0; }
.ottff p { margin:0 0 1em; }
.ottff ul,.ottff ol { margin:0; padding:0; list-style:none; }
.ottff a { text-decoration:none; color:inherit; }
.ottff button { background:none; border:0; font:inherit; }
.ottff img { max-width:100%; display:block; }
.ottff section,.ottff header,.ottff .ff-band,.ottff .ff-hero,.ottff .ff-nav { width:100%; max-width:100%; float:none; }
/* ===== Scoped + prefixed festival styles ===== */
"""


# --------------------------- CSS ---------------------------

def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def prefix_classes(css: str) -> str:
    # .foo / .foo-bar / .foo__bar / .foo--bar → .ff-...
    # Won't match .5em (5 not a letter/underscore).
    return re.sub(r"\.(-?[A-Za-z_][\w-]*)", lambda m: "." + PFX + m.group(1), css)


def scope_selector_list(sel: str) -> str:
    """Wrap each comma-separated selector with .ottff."""
    out = []
    for raw in sel.split(","):
        s = raw.strip()
        if not s:
            continue
        if s == "*":
            out.append(f"{SCOPE} *")
        elif s in (":root", "html", "body"):
            out.append(SCOPE)
        elif s.startswith(SCOPE):
            out.append(s)
        else:
            out.append(f"{SCOPE} {s}")
    return ", ".join(out)


def transform_block(css: str) -> str:
    """Walk the CSS top-level, scoping selector blocks and recursing into @media/@supports."""
    out = []
    i, n = 0, len(css)
    pending_start = 0  # start of the next selector-or-at-rule prelude

    while i < n:
        ch = css[i]
        if ch == "{":
            prelude = css[pending_start:i].strip()
            # find matching closing brace
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                j += 1
            inner = css[i + 1 : j - 1]

            if prelude.startswith("@"):
                head = prelude.split(None, 1)[0]
                if head == "@keyframes" or head == "@-webkit-keyframes":
                    # Don't touch keyframe selectors (from/to/0%/etc.) or prefix them.
                    out.append(f"{prelude} {{{inner}}}")
                elif head in ("@media", "@supports", "@container"):
                    out.append(f"{prelude} {{{transform_block(inner)}}}")
                else:
                    out.append(f"{prelude} {{{inner}}}")
            else:
                out.append(f"{scope_selector_list(prelude)} {{{inner}}}")

            i = j
            pending_start = i
            continue

        if ch == ";" and pending_start == i:
            # bare at-rule (e.g., @import) at top level — pass through
            out.append(css[pending_start : i + 1])
            i += 1
            pending_start = i
            continue

        i += 1

    # any trailing whitespace
    tail = css[pending_start:].strip()
    if tail:
        out.append(tail)
    return "\n".join(out)


def build_css() -> str:
    css = (HERE / "styles.css").read_text()
    css = strip_comments(css)
    css = prefix_classes(css)
    css = transform_block(css)
    return RESET + "\n" + css + "\n"


# --------------------------- HTML ---------------------------

def absolutize_url(u: str) -> str:
    if u.startswith(("http://", "https://", "//", "#", "mailto:", "tel:", "data:")):
        return u
    if u.startswith("/"):
        return REPO_BASE + u
    return f"{REPO_BASE}/{u}"


def prefix_class_attrs(html: str) -> str:
    def repl(m):
        tokens = m.group(2).split()
        prefixed = " ".join((PFX + t) if t else t for t in tokens)
        return f'{m.group(1)}"{prefixed}"'
    return re.sub(r'(\bclass=)"([^"]*)"', repl, html)


def absolutize_attrs(html: str) -> str:
    def src(m):
        return f'{m.group(1)}"{absolutize_url(m.group(2))}"'
    html = re.sub(r'(\bsrc=)"([^"]+)"', src, html)
    html = re.sub(r'(\bhref=)"([^"]+)"', src, html)
    return html


def ascii_encode(s: str) -> str:
    return s.encode("ascii", "xmlcharrefreplace").decode("ascii")


def build_body() -> str:
    """The scoped markup alone — no <link>/<script> tags. Fetched at runtime by the loader."""
    return f'<div class="ottff">\n{extract_body()}\n</div>\n'


def build_loader() -> str:
    """Tiny paste-once snippet: pulls markup, CSS and JS from Pages at page load."""
    return f"""<!-- The Gala: Fire &amp; Ice Edition - live embed. Paste once; it self-updates from the repo. -->
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="{REPO_BASE}/styles-embed.css" />
<div id="ott-embed"></div>
<script>
(function () {{
  var BASE = "{REPO_BASE}";
  var mount = document.getElementById("ott-embed");
  if (!mount) return;
  fetch(BASE + "/embed-body.html", {{ cache: "no-cache" }})
    .then(function (r) {{
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.text();
    }})
    .then(function (html) {{
      mount.innerHTML = html;
      var s = document.createElement("script");
      s.src = BASE + "/script-embed.js";
      s.async = false;
      document.body.appendChild(s);
    }})
    .catch(function (err) {{
      mount.innerHTML =
        '<p style="font-family:Inter,system-ui,sans-serif;text-align:center;padding:48px 20px;font-size:16px;">' +
        'The Gala: Fire &amp; Ice Edition &#183; Sat Oct 17 &#183; W San Francisco Rooftop<br />' +
        '<a href="{REGISTER_URL}" style="text-decoration:underline;font-weight:600;">Register &#8594;</a></p>';
      if (window.console) console.error("OTT embed failed to load:", err);
    }});
}})();
</script>
"""


def extract_body() -> str:
    html = (HERE / "index.html").read_text()
    body_m = re.search(r"<body[^>]*>(.*)</body>", html, flags=re.S | re.I)
    if not body_m:
        raise SystemExit("Could not find <body> in index.html")
    body = body_m.group(1)

    # Drop trailing site-local <script src="script.js"> (we replace with absolute embed script)
    body = re.sub(r'\s*<script[^>]+src="script\.js"[^>]*></script>', "", body, flags=re.I)
    # Drop any noscript fallback referencing Meta Pixel (defensive — pixel lives in <head>, not body)
    body = re.sub(r'\s*<noscript>[^<]*facebook\.com/tr[^<]*</noscript>', "", body, flags=re.I | re.S)

    body = prefix_class_attrs(body)
    body = absolutize_attrs(body)
    body = ascii_encode(body)
    return body.strip()


def build_html() -> str:
    fonts = (
        '<link href="https://fonts.googleapis.com/css2?'
        'family=Archivo+Black&family=Inter:wght@400;500;600;700;800;900&display=swap" '
        'rel="stylesheet" />'
    )
    css_link = f'<link rel="stylesheet" href="{REPO_BASE}/styles-embed.css" />'
    js_tag = f'<script src="{REPO_BASE}/script-embed.js"></script>'

    return (
        "<!-- The Gala: Fire &amp; Ice Edition - namespaced NATIVE embed (prefixed classes) -->\n"
        f"{fonts}\n{css_link}\n"
        '<div class="ottff">\n'
        f"{extract_body()}\n\n"
        f"{js_tag}\n"
        "</div>\n"
    )


# --------------------------- JS ---------------------------

# Explicit class-token rewrites for the script. Patterns are exact string
# replacements so we don't accidentally touch unrelated tokens.
JS_RAW_CLASS_NAMES = [
    # classList.contains / .toggle / .add / .remove
    ("'is-open'", "'ff-is-open'"),
]

JS_SELECTORS = [
    # CSS selectors used inside the script — prefix each class in the selector string.
    (".rail__nav", ".ff-rail__nav"),
    (".card__title", ".ff-card__title"),
    (".rail__viewport", ".ff-rail__viewport"),
    (".rail__track", ".ff-rail__track"),
    (".rail__nav--prev", ".ff-rail__nav--prev"),
    (".rail__nav--next", ".ff-rail__nav--next"),
    (".card--rail", ".ff-card--rail"),
    (".partner, .stat, .aud, .vendor", ".ff-partner, .ff-stat, .ff-aud, .ff-vendor"),
    (".nav__links a", ".ff-nav__links a"),
    (".hero__ctas a", ".ff-hero__ctas a"),
    (".rsvp-trigger", ".ff-rsvp-trigger"),
]


def build_js() -> str:
    js = (HERE / "script.js").read_text()
    for old, new in JS_RAW_CLASS_NAMES:
        js = js.replace(old, new)
    for old, new in JS_SELECTORS:
        js = js.replace(old, new)
    return js


# --------------------------- main ---------------------------

def main():
    (HERE / "styles-embed.css").write_text(build_css())
    (HERE / "embed-native.html").write_text(build_html())
    (HERE / "embed-body.html").write_text(build_body())
    (HERE / "webflow-embed.html").write_text(build_loader())
    (HERE / "script-embed.js").write_text(build_js())
    print("Wrote styles-embed.css, embed-native.html, embed-body.html, "
          "webflow-embed.html, script-embed.js")


if __name__ == "__main__":
    main()
