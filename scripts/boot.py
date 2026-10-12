#!/usr/bin/env python3
"""Render assets/boot.svg: a terminal session that types itself out.

Pure SVG + SMIL (no JS, no external fonts) so GitHub's image proxy renders
and animates it. Every text run gets textLength, so columns line up no matter
which monospace font the viewer ends up with.

    python3 scripts/boot.py
"""
from html import escape
from pathlib import Path

W = 880
CH = 8.4          # monospace advance at 14px
LH = 23           # line height
X0 = 28           # left padding
TOP = 64          # first baseline
TYPE = 0.045      # seconds per typed char

BG, EDGE = "#0d1117", "#1f3a2c"
GREEN, TEXT, DIM, AMBER = "#00ff88", "#e6edf3", "#7d8590", "#f5a524"

# ("cmd", text) is typed after the prompt; ("out", [(col, text, color), ...])
# appears at once, like real output.
SESSION = [
    ("cmd", "whoami"),
    ("out", [(0, "kacper garbaciński. builds AI agents that keep working after he closes the laptop.", TEXT)]),
    ("cmd", "uptime"),
    ("out", [(0, "up 0x0A+ years", TEXT), (18, "0x08 projects shipped", TEXT), (43, "0x1B public repos", GREEN)]),
    ("cmd", "ls -l ~/agents --sort=stars"),
    ("out", [(0, "autoviralai", TEXT), (16, "★ 41", AMBER), (26, "writes posts, measures them, rewrites its own strategy", DIM)]),
    ("out", [(0, "genetic-snake", TEXT), (16, "★ 6", AMBER), (26, "learned Snake through evolution. my first agent.", DIM)]),
    ("out", [(0, "design-mirror", TEXT), (16, "★ 5", AMBER), (26, "pulls any site's design DNA into AI-ready prompts", DIM)]),
    ("cmd", "cat ~/.plan"),
    ("out", [(0, "agents that run in production, not in demos.", TEXT)]),
]


def text(x, y, s, color, extra=""):
    return (f'<text x="{x:.1f}" y="{y}" fill="{color}" textLength="{len(s) * CH:.1f}" '
            f'lengthAdjust="spacingAndGlyphs"{extra}>{escape(s)}</text>')


def main():
    parts, defs = [], []
    t, y = 0.6, TOP
    prompt = "$ "
    for i, (kind, body) in enumerate(SESSION):
        if kind == "cmd":
            n = len(body)
            px = X0 + len(prompt) * CH
            # prompt pops in, then the command reveals one char per step
            parts.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/>'
                         + text(X0, y, prompt.strip(), GREEN, ' font-weight="700"') + "</g>")
            steps = ";".join(f"{k * CH:.1f}" for k in range(n + 1))
            defs.append(f'<clipPath id="c{i}"><rect x="{px:.1f}" y="{y - 16}" width="0" height="{LH}">'
                        f'<animate attributeName="width" values="{steps}" calcMode="discrete" '
                        f'begin="{t + 0.25:.2f}s" dur="{(n + 1) * TYPE:.2f}s" fill="freeze"/></rect></clipPath>')
            parts.append(f'<g clip-path="url(#c{i})">' + text(px, y, body, TEXT) + "</g>")
            t += 0.25 + n * TYPE + 0.35
        else:
            runs = "".join(text(X0 + col * CH, y, s, c) for col, s, c in body)
            parts.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/>{runs}</g>')
            nxt = SESSION[i + 1][0] if i + 1 < len(SESSION) else None
            t += 0.12 if nxt == "out" else 0.6
        y += LH

    # final prompt with a blinking block cursor
    parts.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/>'
                 + text(X0, y, "$", GREEN, ' font-weight="700"')
                 + f'<rect x="{X0 + 2 * CH:.1f}" y="{y - 13}" width="{CH:.1f}" height="16" fill="{GREEN}">'
                 f'<animate attributeName="opacity" values="1;0" calcMode="discrete" dur="1s" '
                 f'begin="{t:.2f}s" repeatCount="indefinite"/></rect></g>')

    H = y + 30
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Terminal: kacper garbaciński builds AI agents. Goal: 1000 followers.">
<defs>{"".join(defs)}
<linearGradient id="glow" x1="0" x2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity="0"/><stop offset=".5" stop-color="{GREEN}" stop-opacity=".9"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient>
</defs>
<style>text{{font:14px ui-monospace,SFMono-Regular,Menlo,Consolas,"DejaVu Sans Mono",monospace;white-space:pre}}</style>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{BG}" stroke="{EDGE}" stroke-width="2"/>
<rect x="40" y="1" width="{W - 80}" height="2" fill="url(#glow)"/>
<circle cx="26" cy="22" r="6" fill="#ff5f57"/><circle cx="46" cy="22" r="6" fill="#febc2e"/><circle cx="66" cy="22" r="6" fill="#28c840"/>
{text(W / 2 - 22 * CH / 2, 27, "kgarbacinski@github: ~", DIM)}
<g opacity="0"><animate attributeName="opacity" values="0;1;0" dur="1.6s" repeatCount="indefinite"/>
<circle cx="{W - 70}" cy="22" r="4" fill="#ff3b3b"/></g>
{text(W - 60, 27, "REC", "#ff3b3b", ' font-weight="700"')}
<line x1="1" y1="40" x2="{W - 1}" y2="40" stroke="{EDGE}"/>
{"".join(parts)}
</svg>
'''
    out = Path(__file__).resolve().parent.parent / "assets" / "boot.svg"
    out.write_text(svg)
    print(f"wrote {out} ({len(svg)} bytes, plays {t:.1f}s)")


if __name__ == "__main__":
    main()
