#!/usr/bin/env python3
"""Render the profile README's SVG assets with live GitHub / PyPI numbers.

Everything visual on the profile is a hand-built SVG in ``assets/`` rather than a
third-party image service, so nothing on the page can rate-limit, time out, or
render an error string in place of a number. This script is the single source of
those files: it fetches star/fork counts and PyPI versions, then writes a light
and a dark variant of every asset (the README picks one with ``<picture>``).

    python3 .github/scripts/build_profile.py            # fetch live numbers
    python3 .github/scripts/build_profile.py --offline  # reuse assets/stats.json

The event-study chart in the hero is real output, not decoration. To regenerate
the numbers in ``EVENT_STUDY``:

    import statspai as sp
    mp = sp.datasets.mpdta()
    gt = sp.callaway_santanna(data=mp, y="lemp", t="year", i="countyreal", g="first_treat")
    print(sp.aggte(gt, type="dynamic").detail)
"""

import json
import os
import subprocess
import sys
import urllib.request
from html import escape

OWNER = "brycewang-stanford"
ASSETS = "assets"
STATS_CACHE = os.path.join(ASSETS, "stats.json")

# (repo, card kind, PyPI package or None, tag, description lines)
PROJECTS = [
    ("stata-code", "tool", "stata-code", None, [
        "Agent-native Stata bridge. Run DiD, IV and RDD and build",
        "publication-ready tables from Claude Code, Jupyter or",
        "VS Code, all on one result schema.",
    ]),
    ("StatsPAI", "tool", "statspai", None, [
        "Agent-native Python library for causal inference and",
        "applied econometrics: one API, machine-readable schemas,",
        "an MCP server, and R/Stata parity validation.",
    ]),
    ("Auto-Empirical-Research-Skills", "skills", None, "23,000+ skills", [
        "A curated collection of agent skills for empirical",
        "research across 8 social science disciplines.",
    ]),
    ("Awesome-Journal-Skills", "skills", None, "200+ journals", [
        "Journal-specific skill packs for AER, QJE, Nature, Cell",
        "and more, from topic selection to referee replies.",
    ]),
    ("Auto-Research-Skills", "skills", None, "idea to paper", [
        "A curated hub of autonomous-research skills and agents,",
        "from first idea to full paper.",
    ]),
    ("AER-Skills", "skills", None, "AER / AEJ", [
        "Skill stack for publishing in the AER: identification-first",
        "empirics, AEA-compliant replication, R&R rebuttals.",
    ]),
]

# Callaway-Sant'Anna dynamic ATT on StatsPAI's bundled mpdta replica (StatsPAI 1.39.2).
# (event time, att, ci_lower, ci_upper); event time -1 is the reference period.
EVENT_STUDY = [
    (-4, -0.004903, -0.033394, 0.023588),
    (-3, 0.009883, -0.011416, 0.031183),
    (-2, 0.007555, -0.009522, 0.024633),
    (-1, 0.0, 0.0, 0.0),
    (0, -0.033837, -0.048455, -0.019219),
    (1, -0.028031, -0.045459, -0.010603),
    (2, -0.045528, -0.074497, -0.016559),
    (3, -0.027734, -0.055891, 0.000424),
]

SKY, GREEN, AMBER, CARDINAL = "#0EA5E9", "#22C55E", "#F59E0B", "#8C1515"

THEMES = {
    "dark": dict(
        panel="#0B1220", panel2="#0F1A2E", border="#1F2A3D", text="#E6EDF3",
        muted="#8B98A9", faint="#3B4A60", grid="#172235", term="#070C16",
        pre="#7C8AA0", ground="#56657A", dino="#C9D4E2",
    ),
    "light": dict(
        panel="#FFFFFF", panel2="#F6F8FB", border="#D8DEE6", text="#0F172A",
        muted="#57667A", faint="#B4BECB", grid="#EDF1F6", term="#F3F6FA",
        pre="#8291A5", ground="#9AA7B7", dino="#475569",
    ),
}

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

STAR = ("M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 "
        "2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79"
        "l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z")
FORK = ("M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 "
        "1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 "
        "2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 "
        "0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 "
        ".75.75 0 0 0 1.5 0Z")

REDUCED_MOTION = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


# ---------------------------------------------------------------- data

def fetch_stats():
    repos = {}
    for repo, _kind, pypi, _tag, _desc in PROJECTS:
        out = subprocess.check_output(["gh", "api", f"repos/{OWNER}/{repo}"], text=True)
        data = json.loads(out)
        entry = {"stars": data["stargazers_count"], "forks": data["forks_count"]}
        if pypi:
            with urllib.request.urlopen(f"https://pypi.org/pypi/{pypi}/json", timeout=30) as r:
                entry["version"] = json.load(r)["info"]["version"]
        repos[repo] = entry

    out = subprocess.check_output(
        ["gh", "api", "--paginate", f"users/{OWNER}/repos?per_page=100&type=owner",
         "--jq", ".[] | select(.fork == false) | .stargazers_count"],
        text=True,
    )
    total = sum(int(line) for line in out.split())
    return {"total_stars": total, "repos": repos}


def fmt(n):
    """Format a count the way GitHub does (e.g. 1330 -> '1.3k')."""
    if n >= 1000:
        return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k"
    return str(n)


# ---------------------------------------------------------------- hero

def hero(theme, stats):
    c = THEMES[theme]
    W, H = 1000, 400

    # Terminal: each line is revealed by a same-coloured cover that shrinks to the right.
    lines = [
        ('>>> ', 'gt = sp.callaway_santanna('),
        ('... ', '    data=mp, y="lemp", t="year",'),
        ('... ', '    i="countyreal", g="first_treat")'),
        ('>>> ', 'sp.aggte(gt, type="dynamic").plot()'),
    ]
    CH, TX, TY, LH = 8.2, 66, 233, 24  # char width, text x, first baseline, line height
    term, css, t = [], [], 0.5
    for i, (prompt, code) in enumerate(lines):
        n = len(prompt) + len(code)
        y = TY + i * LH
        dur = round(n * 0.022, 2)
        term.append(
            f'<text x="{TX}" y="{y}" textLength="{n * CH:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'xml:space="preserve"><tspan fill="{c["faint"]}">{escape(prompt)}</tspan>'
            f'<tspan fill="{c["text"]}">{escape(code)}</tspan></text>'
            f'<rect class="cv cv{i}" x="{TX}" y="{y - 15}" width="{n * CH + 4:.1f}" height="21" fill="{c["term"]}"/>'
        )
        css.append(f".cv{i}{{animation:type {dur}s steps({n}) {t:.2f}s backwards}}")
        t += dur + 0.12
    cur_x = TX + (len(lines[-1][0]) + len(lines[-1][1])) * CH + 3
    cur_y = TY + 3 * LH - 14
    typed = t  # when the chart starts drawing

    # Chart geometry.
    X0, X1, Y0, Y1 = 590, 948, 96, 318
    lo, hi = -0.08, 0.04

    def px(e):
        return X0 + 24 + (e + 4) * (X1 - X0 - 48) / 7

    def py(v):
        return Y1 - (v - lo) / (hi - lo) * (Y1 - Y0)

    grid = []
    for v in (-0.08, -0.04, 0.0, 0.04):
        y = py(v)
        zero = v == 0
        grid.append(
            f'<line x1="{X0}" x2="{X1}" y1="{y:.1f}" y2="{y:.1f}" stroke="{c["faint"] if zero else c["grid"]}" '
            f'stroke-width="1"/><text x="{X0 - 10}" y="{y + 4:.1f}" text-anchor="end">{v:+.2f}</text>'.replace("+0.00", "0")
        )
    ticks = "".join(
        f'<text x="{px(e):.1f}" y="{Y1 + 20}" text-anchor="middle">{e}</text>' for e, *_ in EVENT_STUDY
    )
    tx = px(-0.5)

    band = " ".join(f"{px(e):.1f},{py(u):.1f}" for e, _a, _l, u in EVENT_STUDY)
    band += " " + " ".join(f"{px(e):.1f},{py(l):.1f}" for e, _a, l, _u in reversed(EVENT_STUDY))
    path = "M" + " L".join(f"{px(e):.1f},{py(a):.1f}" for e, a, _l, _u in EVENT_STUDY)

    marks = []
    for i, (e, a, l, u) in enumerate(EVENT_STUDY):
        col = c["pre"] if e < 0 else SKY
        x = px(e)
        whisk = "" if e == -1 else (
            f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{py(u):.1f}" y2="{py(l):.1f}" stroke="{col}" stroke-width="2" '
            f'stroke-linecap="round"/>'
        )
        fill = c["panel"] if e == -1 else col
        marks.append(
            f'<g class="pt pt{i}">{whisk}<circle cx="{x:.1f}" cy="{py(a):.1f}" r="4.5" fill="{fill}" '
            f'stroke="{col}" stroke-width="2"/></g>'
        )
        css.append(f".pt{i}{{animation:pop .35s ease-out {typed + 0.25 + i * 0.14:.2f}s backwards}}")

    chips = [
        (f"{fmt(stats['total_stars'])} stars", AMBER),
        ("JOSS 2026", GREEN),
        ("Stanford REAP", CARDINAL if theme == "light" else "#E0626B"),
    ]
    chip_svg, cx = [], 48
    for label, col in chips:
        w = len(label) * 7.3 + 30
        chip_svg.append(
            f'<g transform="translate({cx},352)"><rect width="{w:.0f}" height="26" rx="13" fill="{c["panel2"]}" '
            f'stroke="{c["border"]}"/><circle cx="14" cy="13" r="3.5" fill="{col}"/>'
            f'<text x="24" y="17.5" font-family="{MONO}" font-size="12" fill="{c["muted"]}" '
            f'textLength="{len(label) * 7.3:.1f}" lengthAdjust="spacingAndGlyphs">{label}</text></g>'
        )
        cx += w + 8

    style = f"""
    .cv{{transform-box:fill-box;transform-origin:right center;transform:scaleX(0)}}
    @keyframes type{{from{{transform:scaleX(1)}}to{{transform:scaleX(0)}}}}
    @keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
    @keyframes show{{from{{opacity:0}}}}
    @keyframes draw{{from{{stroke-dashoffset:1}}}}
    @keyframes pop{{from{{opacity:0;transform:scale(.3)}}}}
    @keyframes rise{{from{{opacity:0;transform:translateY(8px)}}}}
    @keyframes drift{{from{{transform:translateX(-60px)}}to{{transform:translateX(60px)}}}}
    .cur{{animation:show .01s {typed:.2f}s backwards,blink 1.1s steps(1) {typed:.2f}s infinite}}
    .name{{animation:rise .7s ease-out .05s backwards}}
    .tag{{animation:rise .7s ease-out .2s backwards}}
    .es{{stroke-dasharray:1;animation:draw 1.2s ease-in-out {typed + 0.1:.2f}s backwards}}
    .band{{animation:show .9s ease-out {typed + 1.1:.2f}s backwards}}
    .note{{animation:show .8s ease-out {typed + 1.5:.2f}s backwards}}
    .pt{{transform-box:fill-box;transform-origin:center}}
    .glow{{animation:drift 9s ease-in-out infinite alternate}}
    {"".join(css)}
    {REDUCED_MOTION}"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">Bryce Wang: agent-native infrastructure for empirical research</title>
<desc id="d">A terminal runs a Callaway-Sant'Anna event study with StatsPAI and the resulting chart draws itself: flat pre-trends, then a negative effect after treatment.</desc>
<style>{style}</style>
<defs>
  <linearGradient id="brand" x1="0" x2="1"><stop offset="0" stop-color="{SKY}"/><stop offset=".5" stop-color="{GREEN}"/><stop offset="1" stop-color="{AMBER}"/></linearGradient>
  <radialGradient id="g1"><stop offset="0" stop-color="{SKY}" stop-opacity="{.20 if theme == "dark" else .12}"/><stop offset="1" stop-color="{SKY}" stop-opacity="0"/></radialGradient>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1" fill="{c["grid"]}"/></pattern>
  <clipPath id="clip"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16"/></clipPath>
</defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16" fill="{c["panel"]}" stroke="{c["border"]}"/>
<g clip-path="url(#clip)">
  <rect width="{W}" height="{H}" fill="url(#dots)"/>
  <ellipse class="glow" cx="770" cy="150" rx="330" ry="230" fill="url(#g1)"/>
  <rect width="{W}" height="4" fill="url(#brand)"/>
</g>

<text x="48" y="62" font-family="{MONO}" font-size="13" fill="{c["muted"]}" letter-spacing="1.5">DATA SCIENTIST, STANFORD REAP  /  FOUNDER, COPAPER.AI</text>
<text class="name" x="46" y="128" font-family="{SANS}" font-size="62" font-weight="800" fill="{c["text"]}" letter-spacing="-1.5">Bryce Wang</text>
<text class="tag" x="48" y="164" font-family="{SANS}" font-size="19" fill="{c["muted"]}">Agent-native infrastructure for <tspan fill="url(#brand)" font-weight="700">empirical research</tspan></text>

<rect x="48" y="192" width="430" height="140" rx="10" fill="{c["term"]}" stroke="{c["border"]}"/>
<g font-family="{MONO}" font-size="13.5">
{"".join(term)}
<rect class="cur" x="{cur_x:.1f}" y="{cur_y}" width="8" height="17" fill="{SKY}"/>
</g>
{"".join(chip_svg)}

<g font-family="{MONO}" font-size="11.5" fill="{c["muted"]}">
  <text x="{X0}" y="62" font-size="13" fill="{c["text"]}" font-weight="600">ATT by event time</text>
  <text x="{X1}" y="62" text-anchor="end">95% CI</text>
  {"".join(grid)}
  {ticks}
  <line x1="{tx:.1f}" x2="{tx:.1f}" y1="{Y0 - 6}" y2="{Y1}" stroke="{AMBER}" stroke-width="1.5" stroke-dasharray="4 5"/>
  <text x="{tx + 8:.1f}" y="{Y0 + 4}" fill="{AMBER}">treatment</text>
  <text class="note" x="{X1}" y="{H - 26}" text-anchor="end" fill="{c["faint"]}">real output: StatsPAI, Callaway-Sant'Anna on mpdta replica</text>
</g>
<polygon class="band" points="{band}" fill="{SKY}" opacity=".13"/>
<path class="es" d="{path}" pathLength="1" fill="none" stroke="{SKY}" stroke-width="2" stroke-linejoin="round" opacity=".55"/>
{"".join(marks)}
</svg>
"""


# ---------------------------------------------------------------- cards

def card(theme, repo, kind, tag, desc, s):
    c = THEMES[theme]
    W, H = 490, 190
    accent = SKY if kind == "tool" else AMBER
    right = f"PyPI v{s['version']}" if "version" in s else tag
    rw = len(right) * 6.7 + 20
    name_size = 20 if len(repo) <= 24 else 17.5
    body = "".join(
        f'<text x="24" y="{84 + i * 20}" font-family="{SANS}" font-size="13.5" fill="{c["muted"]}">{escape(line)}</text>'
        for i, line in enumerate(desc)
    )
    stars, forks = fmt(s["stars"]), fmt(s["forks"])
    install = (
        f'<text x="{W - 24}" y="{H - 26}" text-anchor="end" fill="{c["faint"]}">pip install {s["pypi"]}</text>'
        if "pypi" in s else ""
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(repo)}: {stars} stars, {forks} forks">
<defs><linearGradient id="a" x1="0" x2="1"><stop offset="0" stop-color="{accent}"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>
<clipPath id="c"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12"/></clipPath></defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="{c["panel"]}" stroke="{c["border"]}"/>
<rect width="4" height="{H}" fill="url(#a)" clip-path="url(#c)"/>
<text x="24" y="46" font-family="{SANS}" font-size="{name_size}" font-weight="700" fill="{c["text"]}">{escape(repo)}</text>
<rect x="{W - 20 - rw:.0f}" y="28" width="{rw:.0f}" height="24" rx="12" fill="{c["panel2"]}" stroke="{c["border"]}"/>
<text x="{W - 20 - rw / 2:.1f}" y="44.5" text-anchor="middle" font-family="{MONO}" font-size="11.5" fill="{accent}" textLength="{len(right) * 6.7:.1f}" lengthAdjust="spacingAndGlyphs">{escape(right)}</text>
{body}
<g font-family="{MONO}" font-size="13" fill="{c["text"]}">
  <path transform="translate(24,{H - 39})" d="{STAR}" fill="{AMBER}"/>
  <text x="46" y="{H - 26}" font-weight="600">{stars}</text>
  <path transform="translate(104,{H - 39})" d="{FORK}" fill="{c["muted"]}"/>
  <text x="126" y="{H - 26}" fill="{c["muted"]}">{forks}</text>
  {install}
</g>
</svg>
"""


# ---------------------------------------------------------------- product banner

def copaper(theme):
    c = THEMES[theme]
    W, H = 1000, 170
    stages = ["raw data", "identification", "estimation", "robustness", "manuscript"]
    X0, X1, Y = 500, 936, 78
    step = (X1 - X0) / (len(stages) - 1)
    nodes = []
    for i, label in enumerate(stages):
        x = X0 + i * step
        last = i == len(stages) - 1
        nodes.append(
            f'<circle class="n n{i}" cx="{x:.1f}" cy="{Y}" r="{7 if last else 5}" fill="{GREEN if last else c["panel"]}" '
            f'stroke="{GREEN if last else SKY}" stroke-width="2"/>'
            f'<text x="{x:.1f}" y="{Y + (30 if i % 2 == 0 else -18)}" text-anchor="middle" '
            f'fill="{c["text"] if last else c["muted"]}">{label}</text>'
        )
    pulses = "".join(f".n{i}{{animation:ping 6s ease-out {i * 1.05:.2f}s infinite}}" for i in range(len(stages)))
    style = f"""
    @keyframes run{{0%{{transform:translateX(0);opacity:0}}6%{{opacity:1}}70%{{transform:translateX({X1 - X0}px);opacity:1}}76%,100%{{transform:translateX({X1 - X0}px);opacity:0}}}}
    @keyframes ping{{0%,6%{{stroke-width:2}}3%{{stroke-width:7}}}}
    .dot{{animation:run 6s linear infinite;opacity:0}}
    {pulses}
    {REDUCED_MOTION}"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="CoPaper.AI: from raw data to publishable manuscript">
<style>{style}</style>
<defs><linearGradient id="b" x1="0" x2="1"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>
<clipPath id="c"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14"/></clipPath></defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{c["panel"]}" stroke="{c["border"]}"/>
<rect width="{W}" height="4" fill="url(#b)" clip-path="url(#c)"/>
<text x="40" y="52" font-family="{MONO}" font-size="12" fill="{c["muted"]}" letter-spacing="1.5">PRODUCT</text>
<text x="40" y="92" font-family="{SANS}" font-size="32" font-weight="800" fill="{c["text"]}" letter-spacing="-.5">CoPaper.AI</text>
<text x="40" y="122" font-family="{SANS}" font-size="15.5" fill="{c["muted"]}">From raw data to publishable manuscript.</text>
<text x="40" y="145" font-family="{MONO}" font-size="12" fill="{SKY}">copaper.ai</text>
<line x1="{X0}" x2="{X1}" y1="{Y}" y2="{Y}" stroke="{c["faint"]}" stroke-width="2" stroke-dasharray="2 7" stroke-linecap="round"/>
<g font-family="{MONO}" font-size="12">{"".join(nodes)}</g>
<circle class="dot" cx="{X0}" cy="{Y}" r="4" fill="{AMBER}"/>
<text x="{X1 + 8}" y="{H - 26}" text-anchor="end" font-family="{SANS}" font-size="13" fill="{c["muted"]}">An AI research co-author for analysis, reproducibility and writing.</text>
</svg>
"""


# ---------------------------------------------------------------- footer

DINO = [
    "............#########.",
    "...........###########",
    "...........##.########",
    "...........###########",
    "...........###########",
    "...........###########",
    "...........######.....",
    "...........#########..",
    "#.........######......",
    "#........#######......",
    "##......###########...",
    "###....#########..#...",
    "################......",
    "################......",
    ".##############.......",
    "..############........",
    "...##########.........",
    "....########..........",
]
LEGS = [
    [".....###.##...........", ".....##...#...........", ".....#....##..........", ".....##..............."],
    [".....###.##...........", ".....##...#...........", ".....##...#...........", "..........##.........."],
]
CACTUS = [
    "...##...",
    "...##..#",
    "#..##..#",
    "#..##..#",
    "#..##.##",
    "##.####.",
    ".####...",
    "...##...",
    "...##...",
    "...##...",
    "...##...",
]


def pixels(rows, s, fill):
    """Run-length encode a pixel map into <rect>s of size s."""
    out = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x] == "#":
                x2 = x
                while x2 < len(row) and row[x2] == "#":
                    x2 += 1
                out.append(f'<rect x="{x * s}" y="{y * s}" width="{(x2 - x) * s}" height="{s}"/>')
                x = x2
            else:
                x += 1
    return f'<g fill="{fill}" shape-rendering="crispEdges">{"".join(out)}</g>'


def footer(theme, stats):
    c = THEMES[theme]
    W, H, G = 1000, 150, 112          # G = ground y
    S = 2.5                            # pixel size
    DX = 120                           # dino x
    dino_h = (len(DINO) + 4) * S
    hazards = ["endogeneity", "weak instruments", "pre-trends", "p-hacking"]
    # One hazard every 3s at 300 px/s; each reaches the dino 3.1s after it starts,
    # so with a 0.55s offset it passes under the peak of the jump (a 3s loop, peak at 0.6s).
    obstacles, css = [], []
    for i, label in enumerate(hazards):
        obstacles.append(
            f'<g class="ob ob{i}"><g transform="translate(0,{G - len(CACTUS) * 3})">{pixels(CACTUS, 3, c["ground"])}</g>'
            f'<text x="12" y="{G + 20}" text-anchor="middle">{label}</text></g>'
        )
        css.append(f".ob{i}{{animation-delay:{i * 3 + 0.55}s}}")
    specks = "".join(
        f'<rect x="{x}" y="{G + dy}" width="{w}" height="1.5"/>'
        for x, dy, w in [(40, 5, 10), (150, 8, 4), (270, 4, 6), (390, 9, 12), (520, 5, 4),
                         (610, 8, 8), (760, 4, 5), (880, 9, 10), (960, 6, 4)]
    )
    score = f"{stats['total_stars']:05d}"
    style = f"""
    @keyframes walk{{0%{{transform:translateX(1050px)}}33.333%,100%{{transform:translateX(-150px)}}}}
    @keyframes jump{{0%,6.67%{{transform:translateY(0);animation-timing-function:cubic-bezier(.2,.7,.4,1)}}20%{{transform:translateY(-48px);animation-timing-function:cubic-bezier(.6,0,.8,.3)}}33.33%,100%{{transform:translateY(0)}}}}
    @keyframes scroll{{to{{transform:translateX(-1000px)}}}}
    @keyframes legA{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
    @keyframes legB{{0%,49%{{opacity:0}}50%,100%{{opacity:1}}}}
    .ob{{transform:translateX(1050px);animation:walk 12s linear infinite backwards}}
    .dino{{animation:jump 3s linear infinite}}
    .la{{animation:legA .22s steps(1) infinite}}
    .lb{{opacity:0;animation:legB .22s steps(1) infinite}}
    .gr{{animation:scroll 3.3333s linear infinite}}
    {"".join(css)}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.ob1{{transform:translateX(560px)}}}}"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="A pixel dinosaur runs and jumps over cacti labelled endogeneity, weak instruments, pre-trends and p-hacking">
<style>{style}</style>
<defs><clipPath id="v"><rect width="{W}" height="{H}"/></clipPath>
<linearGradient id="f" x1="0" x2="1"><stop offset="0" stop-color="{c["ground"]}" stop-opacity="0"/><stop offset=".12" stop-color="{c["ground"]}"/><stop offset=".88" stop-color="{c["ground"]}"/><stop offset="1" stop-color="{c["ground"]}" stop-opacity="0"/></linearGradient>
<linearGradient id="m" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".1" stop-color="#fff"/><stop offset=".9" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<mask id="fade"><rect width="{W}" height="{H}" fill="url(#m)"/></mask></defs>
<g clip-path="url(#v)" mask="url(#fade)">
  <rect x="0" y="{G}" width="{W}" height="1.5" fill="{c["ground"]}"/>
  <g class="gr" fill="{c["ground"]}">{specks}<g transform="translate(1000,0)">{specks}</g></g>
  <g font-family="{MONO}" font-size="11.5" fill="{c["muted"]}">{"".join(obstacles)}</g>
  <g transform="translate({DX},{G - dino_h + 1})"><g class="dino">
    {pixels(DINO, S, c["dino"])}
    <g class="la" transform="translate(0,{len(DINO) * S})">{pixels(LEGS[0], S, c["dino"])}</g>
    <g class="lb" transform="translate(0,{len(DINO) * S})">{pixels(LEGS[1], S, c["dino"])}</g>
  </g></g>
</g>
<text x="{W - 110}" y="28" text-anchor="end" font-family="{MONO}" font-size="13" fill="{c["muted"]}" letter-spacing="1">HI {score}</text>
<text x="{W - 110}" y="44" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{c["faint"]}">total GitHub stars</text>
</svg>
"""


# ---------------------------------------------------------------- main

def write(name, svg):
    with open(os.path.join(ASSETS, name), "w", encoding="utf-8") as f:
        f.write(svg)


def main():
    os.makedirs(ASSETS, exist_ok=True)
    if "--offline" in sys.argv:
        with open(STATS_CACHE, encoding="utf-8") as f:
            stats = json.load(f)
    else:
        stats = fetch_stats()
        with open(STATS_CACHE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, sort_keys=True)
            f.write("\n")

    for theme in THEMES:
        write(f"hero-{theme}.svg", hero(theme, stats))
        write(f"copaper-{theme}.svg", copaper(theme))
        write(f"footer-{theme}.svg", footer(theme, stats))
        for repo, kind, pypi, tag, desc in PROJECTS:
            s = dict(stats["repos"][repo])
            if pypi:
                s["pypi"] = pypi
            write(f"card-{repo}-{theme}.svg", card(theme, repo, kind, tag, desc, s))

    print(f"total stars: {stats['total_stars']}")
    for repo, s in stats["repos"].items():
        print(f"{repo}: {s}")


if __name__ == "__main__":
    main()
