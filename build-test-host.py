#!/usr/bin/env python3
"""Generate test-host.html: simulated-Webflow harness around the embed body.

Reads embed-native.html, rewrites the absolute CSS/JS URLs to local paths so
the test can run via file:// without a server, and wraps in a hostile-CSS host
matching the brief's verification spec.
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
REPO_BASE = "https://gabrielgalarza.github.io/ott-gala"

HOST_STYLES = """
/* Simulated worst-case Webflow CSS bleed */
body { font-family: Arial; margin:0; padding:24px; background:#fafafa; }
h1,h2 { font-family: 'Times New Roman', serif }
h3,a { font-family: Georgia, serif }
a { text-decoration: underline; color: #06c }
p { margin: 22px 0 }
.nav { flex-direction: column; background: #f0a }
.btn { width: 44px; display: block; border-radius: 999px; padding: 9px }
.container { max-width: 820px }
.card { background: red; border: 4px solid lime }
.hero { flex-direction: column }
.band { background: teal }
.w-embed { padding: 16px; border: 2px dashed #888; }
"""

def main():
    embed = (HERE / "embed-native.html").read_text()
    # rewrite absolute CSS/JS URLs to local files
    embed = embed.replace(f"{REPO_BASE}/styles-embed.css", "styles-embed.css")
    embed = embed.replace(f"{REPO_BASE}/script-embed.js", "script-embed.js")

    out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Test host (simulated Webflow CSS bleed)</title>
<style>{HOST_STYLES}</style>
</head>
<body>
<h1>Host page heading (outside embed - should be Times serif)</h1>
<h2>Outside .ottff heading - also Times serif</h2>
<p>Host paragraph outside the embed. Should have margin 22px 0 and Arial body font.</p>

<div class="w-embed">
{embed}
</div>

<h2>Another host heading after the embed - Times serif again</h2>
</body>
</html>
"""
    (HERE / "test-host.html").write_text(out)
    print("Wrote test-host.html")

if __name__ == "__main__":
    main()
