#!/usr/bin/env python3
"""Atualiza standings SBK a partir da Wikipedia (fallback quando API WSBK falha)."""
import json, re, html, urllib.request
from datetime import date

URL = "https://en.wikipedia.org/wiki/2026_Superbike_World_Championship"
DATA_FILE = "/home/jose/site-josealves/html/motogp-data.json"

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=20) as r:
    text = r.read().decode("utf-8")

tables = re.findall(r"<table[^>]*>(.*?)</table>", text, re.DOTALL)

standings_tbl = None
for t in tables:
    if "Bulega" in t and "Pts." in t:
        standings_tbl = t
        break

if standings_tbl is None:
    raise SystemExit("Não foi possível localizar a tabela de classificação na Wikipedia")

rows = re.findall(r"<tr[^>]*>(.*?)</tr>", standings_tbl, re.DOTALL)

# Equipa / fabricante / país / número (grid 2026)
TEAMS = {
    "Nicolò Bulega": ("Aruba.it Racing - Ducati", "Ducati", "IT", 11),
    "Iker Lecuona": ("Aruba.it Racing - Ducati", "Ducati", "ES", 7),
    "Sam Lowes": ("Elf Marc VDS Racing Team", "Ducati", "GB", 14),
    "Alex Lowes": ("Bimota by Kawasaki Racing Team", "Bimota", "GB", 22),
    "Yari Montella": ("Barni Spark Racing Team", "Ducati", "IT", 5),
    "Lorenzo Baldassarri": ("Team PATA GoEleven", "Ducati", "IT", 34),
    "Axel Bassani": ("Bimota by Kawasaki Racing Team", "Bimota", "IT", 47),
    "Álvaro Bautista": ("Superbike Advocates Racing", "Ducati", "ES", 19),
    "Miguel Oliveira": ("BMW Motorrad WorldSBK Team", "BMW", "PT", 88),
    "Garrett Gerloff": ("Kawasaki WorldSBK Team", "Kawasaki", "US", 31),
}

standings = []
for r in rows[2:]:
    cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.DOTALL)
    clean = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in cells]
    if len(clean) < 4 or not clean[0].isdigit():
        continue
    pos = int(clean[0])
    rider = clean[1]
    bike = clean[2]
    try:
        pts = int(clean[-1])
    except ValueError:
        continue
    team, constructor, country, number = TEAMS.get(rider, ("", bike, "", 0))
    races = [c for c in clean[3:-1] if c]
    wins = sum(1 for c in races if c == "1")
    standings.append({
        "position": pos,
        "rider": rider,
        "number": number,
        "country_iso": country,
        "team": team,
        "points": pts,
        "wins": wins,
    })
    if pos >= 10:
        break

# Rondas completas: pelo líder
br = rows[2]
bcells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", br, re.DOTALL)
bclean = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in bcells]
race_cells = bclean[3:-1]
races_done = sum(1 for c in race_cells if c)
rounds_complete = races_done // 3

# Atualizar JSON
data = json.load(open(DATA_FILE, encoding="utf-8"))
today = date.today().isoformat()
for i, ev in enumerate(data["sbk"]["calendar"], 1):
    if i <= rounds_complete:
        ev["status"] = "finished"
    elif i == rounds_complete + 1:
        ev["status"] = "next"
    else:
        ev["status"] = "upcoming"

data["sbk"]["standings"] = standings
data["sbk"]["updated"] = today

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"SBK atualizado: {today}, ~{rounds_complete} rondas completas")
print("Top 10:")
for s in standings:
    name = s["rider"]
    team = s["team"][:30]
    pts = s["points"]
    pos = s["position"]
    print(f"  {pos:2d}. {name:25s} ({team:30s}) — {pts:3d} pts")
