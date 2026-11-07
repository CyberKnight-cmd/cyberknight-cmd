"""Generate self-hosted stats + top-languages SVG cards using the GitHub GraphQL API."""
import json, os, sys, urllib.request
from html import escape

USER = os.environ.get("USERNAME", "CyberKnight-cmd")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = "profile-stats"

Q = """query($login:String!,$after:String){user(login:$login){
 name followers{totalCount}
 contributionsCollection{totalCommitContributions restrictedContributionsCount totalPullRequestContributions totalIssueContributions}
 pullRequests{totalCount} issues{totalCount}
 repositories(first:100,after:$after,ownerAffiliations:OWNER,isFork:false){
  pageInfo{hasNextPage endCursor}
  nodes{stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}"""

def gql(after=None):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": Q, "variables": {"login": USER, "after": after}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req))
    if "errors" in d: sys.exit(d["errors"])
    return d["data"]["user"]

user, repos, after = None, [], None
while True:
    u = gql(after); user = user or u
    r = u["repositories"]; repos += r["nodes"]
    if not r["pageInfo"]["hasNextPage"]: break
    after = r["pageInfo"]["endCursor"]

c = user["contributionsCollection"]
stars = sum(r["stargazerCount"] for r in repos)
langs = {}
for r in repos:
    for e in r["languages"]["edges"]:
        n = e["node"]["name"]; langs.setdefault(n, [0, e["node"]["color"] or "#888"])[0] += e["size"]
top = sorted(langs.items(), key=lambda x: -x[1][0])[:8]
total = sum(v[0] for _, v in top) or 1

BG, PINK, YEL, TXT, MUT = "#0D1117", "#F75590", "#F8D866", "#C9D1D9", "#8B949E"
FONT = "font-family:'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif"
H = 195

def card(w, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{H}" viewBox="0 0 {w} {H}">'
            f'<style>text{{{FONT}}}.f{{opacity:0;animation:f .6s ease forwards}}@keyframes f{{to{{opacity:1}}}}</style>'
            f'<rect width="{w}" height="{H}" rx="10" fill="{BG}"/>'
            f'<text x="25" y="35" fill="{PINK}" font-size="18" font-weight="700">{escape(title)}</text>{body}</svg>')

name = escape(user["name"] or USER)
stats = [("⭐", "Total Stars", stars),
         ("📝", "Commits (this year)", c["totalCommitContributions"] + c["restrictedContributionsCount"]),
         ("🔀", "Pull Requests", user["pullRequests"]["totalCount"]),
         ("🐞", "Issues", user["issues"]["totalCount"]),
         ("👥", "Followers", user["followers"]["totalCount"])]
body = "".join(
    f'<g class="f" style="animation-delay:{i*120}ms"><text x="25" y="{70+i*25}" fill="{YEL}" font-size="14">{ic}</text>'
    f'<text x="50" y="{70+i*25}" fill="{TXT}" font-size="14" font-weight="600">{lb}:</text>'
    f'<text x="230" y="{70+i*25}" fill="#FFF" font-size="14" font-weight="700">{v:,}</text></g>'
    for i, (ic, lb, v) in enumerate(stats))
body += (f'<circle cx="370" cy="115" r="45" fill="none" stroke="#30363D" stroke-width="6"/>'
         f'<circle cx="370" cy="115" r="45" fill="none" stroke="{PINK}" stroke-width="6" stroke-dasharray="283" '
         f'stroke-dashoffset="70" transform="rotate(-90 370 115)" stroke-linecap="round"/>'
         f'<text x="370" y="123" fill="#FFF" font-size="22" font-weight="800" text-anchor="middle">{len(repos)}</text>'
         f'<text x="370" y="180" fill="{MUT}" font-size="11" text-anchor="middle">repos</text>')
os.makedirs(OUT, exist_ok=True)
open(f"{OUT}/stats.svg", "w").write(card(450, f"{name}'s GitHub Stats", body))

W = 350; x = 25; bar = ""
for n, (s, col) in top:
    bw = (W - 50) * s / total
    bar += f'<rect x="{x:.1f}" y="52" width="{bw:.1f}" height="8" fill="{col}"/>'; x += bw
bar = f'<clipPath id="c"><rect x="25" y="52" width="{W-50}" height="8" rx="4"/></clipPath><g clip-path="url(#c)">{bar}</g>'
for i, (n, (s, col)) in enumerate(top):
    cx, cy = 25 + (i % 2) * 160, 85 + (i // 2) * 25
    bar += (f'<g class="f" style="animation-delay:{i*100}ms"><circle cx="{cx+5}" cy="{cy-4}" r="5" fill="{col}"/>'
            f'<text x="{cx+16}" y="{cy}" fill="{TXT}" font-size="12">{escape(n)} {100*s/total:.1f}%</text></g>')
open(f"{OUT}/top-langs.svg", "w").write(card(W, "Most Used Languages", bar))
print("ok", stars, len(repos), [n for n, _ in top])
