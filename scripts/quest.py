#!/usr/bin/env python3
"""Render assets/quest.svg: the 1000-followers quest bar + newest followers.

Runs daily from .github/workflows/quest.yml. State lives in
data/followers.json so "newest" means "first seen by this script", which
doesn't depend on the order the followers API happens to return.

Avatars are inlined as data: URIs. GitHub's image proxy won't fetch
external images from inside an SVG, so linking them would render blanks.

    GITHUB_TOKEN=... python3 scripts/quest.py
"""
import base64
import json
import os
import urllib.request
from datetime import date, timedelta
from html import escape
from pathlib import Path

USER = "kgarbacinski"
GOAL = 1000
MILESTONES = (250, 500, 750)
REWARD = "at 1000 I open-source the prompt library behind AutoViralAI's 800-like post"
SHOW = 8

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "followers.json"
OUT = ROOT / "assets" / "quest.svg"

W, CH = 880, 8.4
BG, EDGE = "#0d1117", "#1f3a2c"
GREEN, TEXT, DIM, AMBER, EMPTY = "#00ff88", "#e6edf3", "#7d8590", "#f5a524", "#1b2620"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": f"{USER}-quest"})
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


def eta(history, count):
    """Followers/day over the last 30 days of history -> 'yyyy-mm'."""
    pts = sorted(history.items())
    pts = [p for p in pts if date.fromisoformat(p[0]) >= date.fromisoformat(pts[-1][0]) - timedelta(days=30)]
    if count >= GOAL:
        return "quest complete"
    if len(pts) < 3:
        return "ETA: collecting data, check back in a few days"
    days = (date.fromisoformat(pts[-1][0]) - date.fromisoformat(pts[0][0])).days or 1
    rate = (pts[-1][1] - pts[0][1]) / days
    if rate <= 0:
        return "ETA: never at this pace. the follow button is right there"
    when = date.fromisoformat(pts[-1][0]) + timedelta(days=(GOAL - count) / rate)
    return f"ETA: {when:%b %Y} at {rate:.1f}/day. you can make it sooner"


def t(x, y, s, color, size=14, extra="", anchor=None):
    w = len(s) * CH * size / 14
    a = f' text-anchor="{anchor}"' if anchor else ""
    return (f'<text x="{x:.1f}" y="{y}" fill="{color}" font-size="{size}" textLength="{w:.1f}" '
            f'lengthAdjust="spacingAndGlyphs"{a}{extra}>{escape(s)}</text>')


def render(count, recent, eta_line, today):
    pct = min(count / GOAL, 1)
    bx, by, bw, bh = 28, 104, W - 56, 26
    segs, n = [], 50
    sw = bw / n
    lit = round(pct * n)
    for k in range(n):
        on = k < lit
        fill = GREEN if on else EMPTY
        # lit cells power on left to right
        anim = (f'<animate attributeName="opacity" from="0" to="1" begin="{0.3 + k * 0.03:.2f}s" dur=".2s" fill="freeze"/>'
                if on else "")
        segs.append(f'<rect x="{bx + k * sw + 1:.1f}" y="{by}" width="{sw - 2:.1f}" height="{bh}" rx="2" '
                    f'fill="{fill}" opacity="{0 if on else 1}">{anim}</rect>')
    ticks = []
    for m in MILESTONES:
        mx = bx + bw * m / GOAL
        hit = count >= m
        ticks.append(f'<line x1="{mx:.1f}" y1="{by - 6}" x2="{mx:.1f}" y2="{by + bh + 6}" stroke="{AMBER if hit else DIM}" stroke-dasharray="3 3"/>')
        ticks.append(t(mx, by + bh + 22, str(m), AMBER if hit else DIM, 12, anchor="middle"))
    ticks.append(t(bx + bw, by + bh + 22, f"{GOAL} unlock", GREEN, 12, anchor="end"))

    gy, r = 236, 26
    gallery = []
    for i, f in enumerate(recent[:SHOW]):
        cx = 28 + r + i * 92
        try:
            href = avatar(f["id"])
        except Exception:
            href = ""
        login = f["login"] if len(f["login"]) <= 10 else f["login"][:9] + "…"
        gallery.append(
            f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{1.9 + i * 0.12:.2f}s" dur=".3s" fill="freeze"/>'
            f'<clipPath id="a{i}"><circle cx="{cx}" cy="{gy}" r="{r}"/></clipPath>'
            f'<circle cx="{cx}" cy="{gy}" r="{r + 2}" fill="{EDGE}"/>'
            + (f'<image href="{href}" x="{cx - r}" y="{gy - r}" width="{2 * r}" height="{2 * r}" clip-path="url(#a{i})"/>' if href else "")
            + t(cx, gy + r + 20, "@" + login, TEXT, 12, anchor="middle") + "</g>")
    # the empty slot is the call to action
    cx = 28 + r + min(len(recent), SHOW) * 92
    if cx + r < W - 20:
        gallery.append(
            f'<g><circle cx="{cx}" cy="{gy}" r="{r}" fill="none" stroke="{GREEN}" stroke-width="2" stroke-dasharray="5 5">'
            f'<animateTransform attributeName="transform" type="rotate" from="0 {cx} {gy}" to="360 {cx} {gy}" dur="12s" repeatCount="indefinite"/></circle>'
            + t(cx, gy + 7, "+", GREEN, 22, ' font-weight="700"', anchor="middle")
            + t(cx, gy + r + 20, "you?", GREEN, 12, anchor="middle") + "</g>")

    H = 320
    head = f"{count} / {GOAL}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Quest: {count} of {GOAL} followers. Newest followers shown below.">
<style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"DejaVu Sans Mono",monospace;white-space:pre}}</style>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{BG}" stroke="{EDGE}" stroke-width="2"/>
<rect x="28" y="24" width="96" height="24" rx="12" fill="none" stroke="{GREEN}"/>
{t(76, 41, "QUEST 01", GREEN, 13, ' font-weight="700"', anchor="middle")}
{t(140, 42, "reach 1000 followers", TEXT, 18, ' font-weight="700"')}
{t(W - 28, 44, head, GREEN, 26, ' font-weight="700"', anchor="end")}
{t(28, 78, REWARD, DIM, 13)}
{t(W - 28, 78, f"0x{count:03X} / 0x{GOAL:03X}", DIM, 12, anchor="end")}
{"".join(segs)}
<rect x="{bx}" y="{by}" width="60" height="{bh}" fill="#ffffff" opacity=".18">
<animate attributeName="x" values="{bx};{bx + bw * pct - 60:.1f}" dur="2.4s" begin="2s" repeatCount="indefinite"/>
<animate attributeName="opacity" values="0;.22;0" dur="2.4s" begin="2s" repeatCount="indefinite"/></rect>
{"".join(ticks)}
{t(28, 184, "$ tail /var/log/followers", GREEN, 13)}
{t(W - 28, 184, eta_line, DIM, 12, anchor="end")}
{"".join(gallery)}
{t(W - 28, H - 14, f"refreshed {today} by a cron job. it is not watching you. mostly.", "#4b5563", 11, anchor="end")}
</svg>
'''


def main():
    today = date.today().isoformat()
    followers = all_followers()
    state = update_state(followers, today)
    count = len(followers)
    OUT.write_text(render(count, state["recent"], eta(state["history"], count), today))
    print(f"{count}/{GOAL}, gallery: {', '.join(r['login'] for r in state['recent'][:SHOW])}")


if __name__ == "__main__":
    main()
