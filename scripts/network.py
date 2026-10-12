#!/usr/bin/env python3
"""Render assets/network.svg: follower count, weekly growth, newest followers.

Runs daily from .github/workflows/network.yml. State lives in
data/followers.json so "newest" means "first seen by this script", which
doesn't depend on the order the followers API happens to return.

Avatars are inlined as data: URIs. GitHub's image proxy won't fetch
external images from inside an SVG, so linking them would render blanks.

    GITHUB_TOKEN=... python3 scripts/network.py
"""
import base64
import json
import os
import urllib.request
from datetime import date, timedelta
from html import escape
from pathlib import Path

USER = "kgarbacinski"
SHOW = 8

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "followers.json"
OUT = ROOT / "assets" / "network.svg"

W, CH = 880, 8.4
BG, EDGE = "#0d1117", "#1f3a2c"
GREEN, TEXT, DIM = "#00ff88", "#e6edf3", "#7d8590"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": f"{USER}-network"})
    if tok := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def all_followers():
    out, page = [], 1
    while True:
        batch = api(f"/users/{USER}/followers?per_page=100&page={page}")
        out += [{"login": u["login"], "id": u["id"]} for u in batch]
        if len(batch) < 100:
            return out
        page += 1


def avatar(uid):
    url = f"https://avatars.githubusercontent.com/u/{uid}?s=96"
    with urllib.request.urlopen(url, timeout=30) as r:
        mime = r.headers.get_content_type() or "image/png"
        return f"data:{mime};base64,{base64.b64encode(r.read()).decode()}"


def update_state(followers, today):
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    current = {f["login"]: f for f in followers}
    seen = state.get("seen")
    recent = state.get("recent", [])
    if seen is None:
        # first run: trust API order (newest first) for the initial gallery
        seen = list(current)
        recent = [{**f, "at": today} for f in followers[:SHOW]]
    else:
        known = set(seen)
        fresh = [f for f in followers if f["login"] not in known]
        seen += [f["login"] for f in fresh]
        recent = [{**f, "at": today} for f in fresh] + recent
    # unfollowers drop out of the gallery
    recent = [r for r in recent if r["login"] in current][:SHOW * 3]
    history = state.get("history", {})
    history[today] = len(followers)
    history = dict(sorted(history.items())[-120:])
    state = {"seen": seen, "recent": recent, "history": history}
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1) + "\n")
    return state


def growth(history):
    """'+N in the last 7 days' once a week of history exists."""
    pts = sorted(history.items())
    last_day, last = date.fromisoformat(pts[-1][0]), pts[-1][1]
    week_ago = [n for d, n in pts if date.fromisoformat(d) <= last_day - timedelta(days=7)]
    if not week_ago:
        return f"growth tracked since {pts[0][0]}"
    delta = last - week_ago[-1]
    return f"{delta:+d} in the last 7 days"


def t(x, y, s, color, size=14, extra="", anchor=None):
    w = len(s) * CH * size / 14
    a = f' text-anchor="{anchor}"' if anchor else ""
    return (f'<text x="{x:.1f}" y="{y}" fill="{color}" font-size="{size}" textLength="{w:.1f}" '
            f'lengthAdjust="spacingAndGlyphs"{a}{extra}>{escape(s)}</text>')


def render(count, recent, growth_line, today):
    gy, r = 156, 26
    gallery = []
    for i, f in enumerate(recent[:SHOW]):
        cx = 28 + r + i * 92
        try:
            href = avatar(f["id"])
        except Exception:
            href = ""
        login = f["login"] if len(f["login"]) <= 10 else f["login"][:9] + "…"
        gallery.append(
            f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{0.4 + i * 0.12:.2f}s" dur=".3s" fill="freeze"/>'
            f'<clipPath id="a{i}"><circle cx="{cx}" cy="{gy}" r="{r}"/></clipPath>'
            f'<circle cx="{cx}" cy="{gy}" r="{r + 2}" fill="{EDGE}"/>'
            + (f'<image href="{href}" x="{cx - r}" y="{gy - r}" width="{2 * r}" height="{2 * r}" clip-path="url(#a{i})"/>' if href else "")
            + t(cx, gy + r + 20, "@" + login, TEXT, 12, anchor="middle") + "</g>")
    # one open seat at the end of the row
    cx = 28 + r + min(len(recent), SHOW) * 92
    if cx + r < W - 20:
        gallery.append(
            f'<g><circle cx="{cx}" cy="{gy}" r="{r}" fill="none" stroke="{GREEN}" stroke-width="2" stroke-dasharray="5 5">'
            f'<animateTransform attributeName="transform" type="rotate" from="0 {cx} {gy}" to="360 {cx} {gy}" dur="12s" repeatCount="indefinite"/></circle>'
            + t(cx, gy + 7, "+", GREEN, 22, ' font-weight="700"', anchor="middle")
            + t(cx, gy + r + 20, "you", GREEN, 12, anchor="middle") + "</g>")

    H = 246
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{count} engineers following the work. Newest followers shown below.">
<style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"DejaVu Sans Mono",monospace;white-space:pre}}</style>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{BG}" stroke="{EDGE}" stroke-width="2"/>
<rect x="28" y="24" width="96" height="24" rx="12" fill="none" stroke="{GREEN}"/>
{t(76, 41, "NETWORK", GREEN, 13, ' font-weight="700"', anchor="middle")}
{t(140, 42, "engineers following the work", TEXT, 18, ' font-weight="700"')}
{t(W - 28, 46, str(count), GREEN, 30, ' font-weight="700"', anchor="end")}
{t(28, 82, "$ tail /var/log/followers", GREEN, 13)}
{t(W - 28, 82, f"0x{count:03X}   {growth_line}", DIM, 12, anchor="end")}
<line x1="28" y1="98" x2="{W - 28}" y2="98" stroke="{EDGE}"/>
{"".join(gallery)}
{t(W - 28, H - 14, f"newest first, refreshed {today} by a GitHub Action", "#4b5563", 11, anchor="end")}
</svg>
'''


def main():
    today = date.today().isoformat()
    followers = all_followers()
    state = update_state(followers, today)
    count = len(followers)
    OUT.write_text(render(count, state["recent"], growth(state["history"]), today))
    print(f"{count} followers, gallery: {', '.join(r['login'] for r in state['recent'][:SHOW])}")


if __name__ == "__main__":
    main()
