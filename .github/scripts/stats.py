"""Live GitHub analytics for the profile README, in the DGS brand (light + dark SVG).

Writes analytics-{light,dark}.svg and calendar-{light,dark}.svg, rebuilt daily by the workflow.
Every number comes from the GitHub API at build time; nothing is hard-coded.
Usage: GITHUB_TOKEN=... python3 stats.py <out_dir> [login]      (standard library only)
"""

import base64
import datetime as dt
import json
import math
import os
import pathlib
import sys
import urllib.request

OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"
LOGIN = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("GITHUB_REPOSITORY_OWNER", "Abbishekk-DGS")
HERE = pathlib.Path(__file__).parent
W = 880
IST = dt.timedelta(hours=5, minutes=30)

THEMES = {
    "light": dict(bg="#FFFFFF", dot="#C3D3D2", line="#D5E5E2", ink="#0C1A19", muted="#47605C", faint="#7D918E",
                  title="#0C7A72", accent="#0C7A72", accent2="#14A394", org="#FF7A1A", track="#EAF3F1",
                  series=["#0C7A72", "#FF7A1A", "#5CC4BA", "#0C1A19", "#A9C9C5"],
                  tile=("#E4F0EE", "#CFE1DE", "#BDD3CF"),
                  ramp=[("#A8DFD8", "#82C7BF", "#6BB4AC"), ("#5CC4BA", "#3BA79C", "#2B9288"),
                        ("#14A394", "#0E8177", "#0B6E66"), ("#0C7A72", "#095E58", "#074B46")],
                  peak=("#FF7A1A", "#D9620F", "#B84F08")),
    "dark": dict(bg="#101E1D", dot="#7FE3DD", line="#28433F", ink="#F2FAF9", muted="#AFC4C0", faint="#7F9592",
                 title="#7FE3DD", accent="#7FE3DD", accent2="#B5F1EC", org="#FF7A1A", track="#1A302E",
                 series=["#7FE3DD", "#FF7A1A", "#2FA89E", "#F2FAF9", "#47605C"],
                 tile=("#1C3331", "#14292A", "#102322"),
                 ramp=[("#1F6F68", "#175650", "#124541"), ("#2FA89E", "#21857D", "#1A6C65"),
                       ("#5CCFC5", "#3FAAA1", "#318B84"), ("#9BEDE7", "#6CC9C2", "#55ADA6")],
                 peak=("#FF8F3D", "#E06A12", "#BF560B")),
}

ICONS = {
    "star": '<path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/>',
    "commit": '<circle cx="12" cy="12" r="3"/><line x1="3" x2="9" y1="12" y2="12"/><line x1="15" x2="21" y1="12" y2="12"/>',
    "repo": '<path d="M10 2v8l3-3 3 3V2"/><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "calendar": '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    "activity": '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
    "flame": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "pin": '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
    "up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
}


def gql(query, **variables):
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": query, "variables": variables}).encode(),
                                 headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]


def fetch():
    who = gql("query($l:String!){user(login:$l){id}}", l=LOGIN)["user"]["id"]
    return gql("""
    query($l:String!,$id:ID!){ user(login:$l){
      login name location websiteUrl createdAt followers{totalCount}
      repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){ totalCount nodes{
        name stargazerCount primaryLanguage{name}
        languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}
        defaultBranchRef{target{... on Commit{history(first:100,author:{id:$id}){totalCount nodes{committedDate}}}}}
      }}
      contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}
    }}""", l=LOGIN, id=who)["user"]


def summarise(u):
    repos = u["repositories"]["nodes"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    today = dt.date.today().isoformat()
    weeks = [[d for d in w["contributionDays"] if d["date"] <= today] for w in cal["weeks"]]
    days = [d for w in weeks for d in w]
    best = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        best = max(best, run)
    current = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"]:
            current += 1
        elif i:           # today with nothing yet doesn't break the streak
            break
    active = [d for d in days if d["contributionCount"]]
    bytes_, by_commit, hours, commits = {}, {}, [0] * 24, 0
    for r in repos:
        for e in r["languages"]["edges"]:
            bytes_[e["node"]["name"]] = bytes_.get(e["node"]["name"], 0) + e["size"]
        ref = r["defaultBranchRef"]
        if not ref:
            continue
        h = ref["target"]["history"]
        commits += h["totalCount"]
        if r["primaryLanguage"]:   # repos with no code language (e.g. this profile) don't count here
            n = r["primaryLanguage"]["name"]
            by_commit[n] = by_commit.get(n, 0) + h["totalCount"]
        for c in h["nodes"]:
            t = dt.datetime.fromisoformat(c["committedDate"].replace("Z", "+00:00")) + IST
            hours[t.hour] += 1
    peak = max(days, key=lambda d: d["contributionCount"]) if days else None
    return dict(
        login=u["login"], name=u["name"] or u["login"], location=u["location"], site=(u["websiteUrl"] or "").replace("https://", ""),
        since=dt.date.fromisoformat(u["createdAt"][:10]), followers=u["followers"]["totalCount"],
        repos=u["repositories"]["totalCount"], stars=sum(r["stargazerCount"] for r in repos), commits=commits,
        total=cal["totalContributions"], weeks=weeks, best=best, current=current, active=len(active), ndays=len(days),
        peak=peak, last=active[-1]["date"] if active else None, hours=hours,
        avg=(sum(d["contributionCount"] for d in active) / len(active)) if active else 0,
        bytes=top(bytes_), by_commit=top(by_commit),
    )


def top(counts, n=5):
    total = sum(counts.values()) or 1
    return [(k, v / total) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:n]]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


def style():
    css = ""
    for key, fam, fallback in (("hg400", "H4", "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"),
                               ("hg700", "H7", "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"),
                               ("jb400", "J4", "ui-monospace,Menlo,Consolas,monospace")):
        b = base64.b64encode((HERE / "fonts" / f"{key}.woff2").read_bytes()).decode()
        css += (f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b}) format('woff2')}}"
                f".{fam}{{font-family:'{fam}',{fallback}}}")
    return css


class Canvas:
    def __init__(self, theme):
        self.t, self.p = THEMES[theme], []

    def text(self, x, y, s, size=13, fill="ink", cls="H4", anchor="start"):
        self.p.append(f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-size="{size}" fill="{self.t.get(fill, fill)}" '
                      f'text-anchor="{anchor}">{esc(s)}</text>')

    def icon(self, name, x, y, size=15, color="accent"):
        self.p.append(f'<g transform="translate({x:.1f},{y:.1f}) scale({size/24:.4f})" fill="none" stroke="{self.t.get(color, color)}" '
                      f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')

    def card(self, x, y, w, h):
        cid = f"c{int(x)}x{int(y)}"
        self.p.append(f'<rect x="{x+.5}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="12" fill="{self.t["bg"]}" stroke="{self.t["line"]}"/>'
                      f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12"/></clipPath>'
                      f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#dots)" clip-path="url(#{cid})"/>')

    def svg(self, h, label):
        t = self.t
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{esc(label)}">'
                f'<title>{esc(label)}</title><style>{style()}</style><defs><pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse">'
                f'<circle cx="2" cy="2" r="1" fill="{t["dot"]}" fill-opacity="{.55 if t["bg"] == "#FFFFFF" else .07}"/></pattern></defs>'
                + "".join(self.p) + "</svg>\n")


def smooth(pts):
    """Monotone-ish Catmull-Rom path that never dips below the baseline between points."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        lim = max(p1[1], p2[1])
        d += f"C{c1[0]:.1f},{min(c1[1], lim):.1f} {c2[0]:.1f},{min(c2[1], lim):.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def nice_ticks(mx, n=4):
    if mx <= 0:
        return [0, 1]
    step = max(1, math.ceil(mx / n))
    return list(range(0, mx + step, step))


def profile_card(c, s, x, y, w, h):
    t = c.t
    c.card(x, y, w, h)
    c.text(x + 26, y + 40, s["login"], 21, "title", "H7")
    rows = [("activity", f'{s["total"]} contributions in the last year'),
            ("repo", f'{s["repos"]} public repos'),
            ("calendar", f'On GitHub since {s["since"].strftime("%b %Y")}'),
            ("pin", " · ".join(v for v in (s["location"], s["site"]) if v))]
    for i, (ic, txt) in enumerate(rows):
        ry = y + 72 + i * 28
        c.icon(ic, x + 26, ry - 12, 15)
        c.text(x + 49, ry, txt, 13.5, "muted")
    # weekly area chart
    vals = [sum(d["contributionCount"] for d in w_) for w_ in s["weeks"]]
    gx0, gx1, gy0, gy1 = x + 340, x + w - 46, y + 44, y + h - 40
    ticks = nice_ticks(max(vals) if vals else 0)
    top_ = ticks[-1]
    step = (gx1 - gx0) / max(len(vals) - 1, 1)
    pts = [(gx0 + i * step, gy1 - v / top_ * (gy1 - gy0)) for i, v in enumerate(vals)]
    c.p.append(f'<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["accent"]}" stop-opacity=".55"/>'
               f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity=".05"/></linearGradient></defs>')
    for v in ticks:
        ty = gy1 - v / top_ * (gy1 - gy0)
        c.p.append(f'<line x1="{gx0}" x2="{gx1}" y1="{ty:.1f}" y2="{ty:.1f}" stroke="{t["line"]}" stroke-opacity=".7"/>')
        c.text(gx1 + 8, ty + 3.5, v, 10, "faint", "J4")
    path = smooth(pts)
    c.p.append(f'<path d="{path}L{gx1:.1f},{gy1:.1f}L{gx0:.1f},{gy1:.1f}Z" fill="url(#area)"/>'
               f'<path d="{path}" fill="none" stroke="{t["accent"]}" stroke-width="2" stroke-linejoin="round"/>')
    if vals and max(vals):
        px, py = pts[vals.index(max(vals))]
        c.p.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{t["org"]}" stroke="{t["bg"]}" stroke-width="1.5"/>')
        c.text(px - 9, py + 4, f"{max(vals)} in a week", 11, "muted", "H4", "end")
    seen = None
    for i, w_ in enumerate(s["weeks"]):
        if not w_:
            continue
        m = dt.date.fromisoformat(w_[0]["date"])
        if m.month != seen and m.day <= 7 and m.month % 2 == 1:
            c.text(gx0 + i * step, gy1 + 17, m.strftime("%b"), 10, "faint", "J4", "middle")
        seen = m.month if m.day <= 7 else seen
    c.text(gx0, y + 28, "Contributions per week", 12, "muted")


def donut(c, title, data, x, y, w, h):
    t = c.t
    c.card(x, y, w, h)
    c.text(x + 26, y + 38, title, 18, "title", "H7")
    cx, cy, r = x + w - 92, y + h / 2 + 12, 48
    circ = 2 * math.pi * r
    c.p.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["track"]}" stroke-width="20"/>')
    off = 0
    for i, (_, frac) in enumerate(data):
        seg = frac * circ
        c.p.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["series"][i]}" stroke-width="20" '
                   f'stroke-dasharray="{max(seg-1.2, .8):.2f} {circ:.2f}" stroke-dashoffset="{-off:.2f}" transform="rotate(-90 {cx} {cy})"/>')
        off += seg
    for i, (name, frac) in enumerate(data):
        ly = y + 72 + i * 25
        c.p.append(f'<rect x="{x+26}" y="{ly-10}" width="11" height="11" rx="2.5" fill="{t["series"][i]}"/>')
        c.text(x + 45, ly, name, 13.5, "muted")
        pct = f"{frac*100:.0f}%" if frac >= .01 else "<1%"
        c.text(x + 172, ly, pct, 11.5, "faint", "J4", "end")


def hours_card(c, s, x, y, w, h):
    t = c.t
    c.card(x, y, w, h)
    c.text(x + 26, y + 38, "Commits by hour", 18, "title", "H7")
    c.text(x + w - 22, y + 36, "IST, UTC +5:30", 10.5, "faint", "J4", "end")
    vals = s["hours"]
    gx0, gx1, gy0, gy1 = x + 50, x + w - 24, y + 58, y + h - 36
    ticks = nice_ticks(max(vals))
    bw = (gx1 - gx0) / 24
    for v in ticks:
        ty = gy1 - v / ticks[-1] * (gy1 - gy0)
        c.p.append(f'<line x1="{gx0}" x2="{gx1}" y1="{ty:.1f}" y2="{ty:.1f}" stroke="{t["line"]}" stroke-opacity=".7"/>')
        c.text(gx0 - 8, ty + 3.5, v, 10, "faint", "J4", "end")
    peak = max(vals)
    for i, v in enumerate(vals):
        if v:
            bh = v / ticks[-1] * (gy1 - gy0)
            col = t["org"] if v == peak else t["accent"]
            c.p.append(f'<rect x="{gx0+i*bw+1.5:.1f}" y="{gy1-bh:.1f}" width="{bw-3:.1f}" height="{bh:.1f}" rx="2" fill="{col}"/>')
    for hr in (0, 6, 12, 18, 23):
        c.text(gx0 + (hr + .5) * bw, gy1 + 17, hr, 10, "faint", "J4", "middle")


def stats_card(c, s, x, y, w, h):
    c.card(x, y, w, h)
    c.text(x + 26, y + 38, "Stats", 18, "title", "H7")
    rows = [("star", "Stars earned", s["stars"]), ("commit", "Public commits", s["commits"]),
            ("repo", "Public repos", s["repos"]), ("users", "Followers", s["followers"]),
            ("calendar", "Active days, 1 yr", s["active"])]
    for i, (ic, lab, val) in enumerate(rows):
        ry = y + 68 + i * 24.5
        c.icon(ic, x + 26, ry - 12, 15)
        c.text(x + 49, ry, lab, 13.5, "muted")
        c.text(x + 216, ry, val, 13.5, "ink", "H7", "end")
    size = 112
    c.p.append(f'<g transform="translate({x+w-size-30},{y+h/2-size/2+10}) scale({size/24})">{(HERE/"mark.svgfrag").read_text()}</g>')


def analytics(s, theme):
    c = Canvas(theme)
    gap, half = 14, (W - 14) / 2
    profile_card(c, s, 0, 0, W, 214)
    y2 = 214 + gap
    donut(c, "Languages by code", s["bytes"], 0, y2, half, 208)
    hours_card(c, s, half + gap, y2, half, 208)
    y3 = y2 + 208 + gap
    stats_card(c, s, 0, y3, half, 208)
    donut(c, "Languages by commit", s["by_commit"], half + gap, y3, half, 208)
    alt = (f'GitHub analytics for {s["login"]}: {s["total"]} contributions in the last year, {s["commits"]} public commits, '
           f'{s["repos"]} public repos, {s["stars"]} stars, {s["followers"]} followers. Languages by code: '
           + ", ".join(f"{n} {f*100:.0f}%" for n, f in s["bytes"]) + ".")
    return c.svg(int(y3 + 208), alt)


def calendar(s, theme):
    """Isometric contribution strip, oldest top-left to newest bottom-right. Height = contributions that day."""
    c = Canvas(theme)
    t = c.t
    H = 430
    c.card(0, 0, W, H)
    u = 10.5
    cx, cy = u * .866, u * .5
    ox, oy = 92, 62

    def iso(wk, day, z=0.0):
        return (ox + (wk - day) * cx, oy + (wk + day) * cy - z)

    def face(pts, col):
        return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="{col}"/>'

    cells = []
    for wk, days in enumerate(s["weeks"]):
        for d in days:
            dow = dt.date.fromisoformat(d["date"]).isoweekday() % 7
            cells.append((wk, dow, d["contributionCount"], d["date"]))
    peak_n = max((n for *_, n, _ in cells), default=1) or 1
    pad = .08
    flat, towers = [], []
    for wk, dow, n, date in sorted(cells, key=lambda k: k[0] + k[1]):
        a, b = wk + pad, wk + 1 - pad
        p, q = dow + pad, dow + 1 - pad
        if not n:
            z = 2.2
            top_, lft, rgt = t["tile"]
        else:
            z = 7 + 62 * math.sqrt(n / peak_n)
            lvl = 0 if n <= 1 else 1 if n <= 3 else 2 if n <= 6 else 3
            top_, lft, rgt = t["peak"] if n == peak_n else t["ramp"][lvl]
        # visible faces: left (+day side) and right (+week side)
        shape = (face([iso(a, q, z), iso(b, q, z), iso(b, q), iso(a, q)], lft)
                 + face([iso(b, p, z), iso(b, q, z), iso(b, q), iso(b, p)], rgt)
                 + face([iso(a, p, z), iso(b, p, z), iso(b, q, z), iso(a, q, z)], top_))
        (towers if n else flat).append(shape)
    c.p.extend(flat)
    c.p.extend(towers)

    # top right: streaks and per-day numbers
    rx = 620
    def block(y, head, rows):
        c.text(rx, y, head, 15, "title", "H7")
        for i, (ic, txt) in enumerate(rows):
            ry = y + 28 + i * 25
            c.icon(ic, rx, ry - 12, 15, "faint")
            c.text(rx + 24, ry, txt, 13.5, "muted")
    if s["current"]:
        latest = ("flame", f'Current streak {s["current"]} day{"s" if s["current"] != 1 else ""}')
    else:
        latest = ("calendar", "Last active " + dt.date.fromisoformat(s["last"]).strftime("%-d %b") if s["last"] else "No activity yet")
    block(50, "Commit streaks", [latest, ("star", f'Best streak {s["best"]} day{"s" if s["best"] != 1 else ""}')])
    block(144, "Contributions per day", [("up", f'Highest in a day {s["peak"]["contributionCount"] if s["peak"] else 0}'),
                                          ("activity", f'Average on active days {s["avg"]:.1f}')])
    # bottom left: the headline figure
    c.text(36, H - 74, s["total"], 44, "title", "H7")
    c.text(36, H - 48, "contributions in the last year", 13.5, "muted")
    c.text(36, H - 28, f'{s["active"]} active days · peak in orange', 11.5, "faint")
    c.text(W - 24, H - 22, "Updated " + dt.date.today().strftime("%-d %b %Y"), 10, "faint", "J4", "end")
    alt = (f'3D contribution calendar for the last year: {s["total"]} contributions over {s["active"]} active days, '
           f'best streak {s["best"]} days, highest {s["peak"]["contributionCount"] if s["peak"] else 0} in a day.')
    return c.svg(H, alt)


if __name__ == "__main__":
    s = summarise(fetch())
    os.makedirs(OUT, exist_ok=True)
    for theme in THEMES:
        (pathlib.Path(OUT) / f"analytics-{theme}.svg").write_text(analytics(s, theme))
        (pathlib.Path(OUT) / f"calendar-{theme}.svg").write_text(calendar(s, theme))
    print(json.dumps({k: v for k, v in s.items() if k not in ("weeks",)}, default=str))
