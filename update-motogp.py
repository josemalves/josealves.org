"""
update-motogp.py — Busca dados reais do campeonato MotoGP via API PulseLive
e dados do WorldSBK (calendário hardcoded + tentativa de scraping standings).
Grava os resultados em motogp-data.json para o site consumir.

Uso: python update-motogp.py
"""
import json
import urllib.request
import re
from datetime import date

BASE = "https://api.motogp.pulselive.com/motogp/v1"
YEAR = 2026

# Calendário WorldSBK 2026 — 12 rondas (dados estáveis, hardcoded)
SBK_CALENDAR_2026 = [
    {"round": 1,  "name": "Australian Round",    "circuit": "Phillip Island",  "country_iso": "AU", "date_start": "2026-02-20", "date_end": "2026-02-22"},
    {"round": 2,  "name": "Portuguese Round",     "circuit": "Portimão",        "country_iso": "PT", "date_start": "2026-03-27", "date_end": "2026-03-29"},
    {"round": 3,  "name": "Dutch Round",          "circuit": "Assen",           "country_iso": "NL", "date_start": "2026-04-17", "date_end": "2026-04-19"},
    {"round": 4,  "name": "Hungarian Round",      "circuit": "Balaton Park",    "country_iso": "HU", "date_start": "2026-05-01", "date_end": "2026-05-03"},
    {"round": 5,  "name": "Czech Round",          "circuit": "Most",            "country_iso": "CZ", "date_start": "2026-05-15", "date_end": "2026-05-17"},
    {"round": 6,  "name": "Aragón Round",         "circuit": "Aragón",          "country_iso": "ES", "date_start": "2026-05-29", "date_end": "2026-05-31"},
    {"round": 7,  "name": "Emilia-Romagna Round", "circuit": "Misano",          "country_iso": "SM", "date_start": "2026-06-12", "date_end": "2026-06-14"},
    {"round": 8,  "name": "UK Round",             "circuit": "Donington Park",  "country_iso": "GB", "date_start": "2026-07-10", "date_end": "2026-07-12"},
    {"round": 9,  "name": "French Round",         "circuit": "Magny-Cours",     "country_iso": "FR", "date_start": "2026-09-04", "date_end": "2026-09-06"},
    {"round": 10, "name": "Italian Round",        "circuit": "Cremona",         "country_iso": "IT", "date_start": "2026-09-25", "date_end": "2026-09-27"},
    {"round": 11, "name": "Estoril Round",        "circuit": "Estoril",         "country_iso": "PT", "date_start": "2026-10-09", "date_end": "2026-10-11"},
    {"round": 12, "name": "Spanish Round",        "circuit": "Jerez",           "country_iso": "ES", "date_start": "2026-10-16", "date_end": "2026-10-18"},
]


def api_get(path):
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def find_season_uuid():
    seasons = api_get("/results/seasons")
    for s in seasons:
        if s["year"] == YEAR:
            return s["id"]
    raise RuntimeError(f"Temporada {YEAR} não encontrada na API")


def find_category_uuid(season_uuid):
    cats = api_get(f"/results/categories?seasonUuid={season_uuid}")
    for c in cats:
        if "MotoGP" in c["name"]:
            return c["id"]
    raise RuntimeError("Categoria MotoGP não encontrada na API")


def fetch_calendar(season_uuid):
    events = api_get(f"/results/events?seasonUuid={season_uuid}")
    calendar = []
    for ev in events:
        if ev.get("test"):
            continue
        calendar.append({
            "name": ev.get("sponsored_name") or ev["name"],
            "short_name": ev.get("short_name", ""),
            "circuit": ev.get("circuit", {}).get("place", ""),
            "circuit_name": ev.get("circuit", {}).get("name", ""),
            "country_iso": ev.get("country", {}).get("iso", ""),
            "country_name": ev.get("country", {}).get("name", ""),
            "date_start": ev.get("date_start", ""),
            "date_end": ev.get("date_end", ""),
            "finished": ev.get("status") == "FINISHED",
        })
    calendar.sort(key=lambda e: e["date_start"])
    return calendar


def fetch_standings(season_uuid, category_uuid):
    data = api_get(
        f"/results/standings?seasonUuid={season_uuid}&categoryUuid={category_uuid}"
    )
    standings = []
    for entry in data.get("classification", [])[:10]:
        rider = entry.get("rider", {})
        team = entry.get("team", {})
        standings.append({
            "position": entry["position"],
            "rider": rider.get("full_name", "?"),
            "number": rider.get("number", 0),
            "country_iso": rider.get("country", {}).get("iso", ""),
            "team": team.get("name", "?"),
            "constructor": entry.get("constructor", {}).get("name", ""),
            "points": entry.get("points", 0),
            "wins": entry.get("race_wins", 0),
            "podiums": entry.get("podiums", 0),
        })
    return standings


SBK_API = "https://api.pulselive.worldsbk.com"
# ISO3 (API WorldSBK) -> ISO2 (para bandeiras); desconhecido -> ""
_SBK_ISO3 = {
    "ITA": "it", "TUR": "tr", "ESP": "es", "GBR": "gb", "NED": "nl", "FRA": "fr",
    "USA": "us", "GER": "de", "AUS": "au", "RSA": "za", "POR": "pt", "CZE": "cz",
    "JPN": "jp", "IRL": "ie", "BRA": "br", "ARG": "ar", "CAN": "ca", "SUI": "ch",
    "AUT": "at", "BEL": "be", "IND": "in", "THA": "th", "MYS": "my", "HUN": "hu", "SMR": "sm",
}


def _sbk_get(path):
    req = urllib.request.Request(SBK_API + path, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def fetch_sbk_standings():
    """Standings WorldSBK via API oficial PulseLive (api.pulselive.worldsbk.com)."""
    standings = []
    try:
        data = _sbk_get(
            f"/wsbk-results/v1/seasons/{YEAR}/categories/SBK/riders/standings"
        )
        rider_cache, team_cache = {}, {}
        for r in data.get("data", [])[:10]:
            a = r.get("attributes", {})
            rel = r.get("relationships", {})
            rid = (rel.get("rider", {}).get("data") or {}).get("id")
            tid = (rel.get("team", {}).get("data") or {}).get("id")
            name, iso = "?", ""
            if rid is not None:
                if rid not in rider_cache:
                    try:
                        ra = _sbk_get(f"/wsbk-riders/v1/riders/{rid}")["data"]["attributes"]
                        nm = f"{ra.get('name', '')} {ra.get('surname', '')}".strip()
                        rider_cache[rid] = (nm or "?", _SBK_ISO3.get(ra.get("country_iso", ""), ""))
                    except Exception:
                        rider_cache[rid] = ("?", "")
                name, iso = rider_cache[rid]
            team = ""
            if tid is not None:
                if tid not in team_cache:
                    try:
                        team_cache[tid] = _sbk_get(
                            f"/wsbk-riders/v1/teams/{tid}"
                        )["data"]["attributes"].get("name", "")
                    except Exception:
                        team_cache[tid] = ""
                team = team_cache[tid]
            standings.append({
                "position": a.get("position", 0),
                "rider": name,
                "number": a.get("number", 0),
                "country_iso": iso,
                "team": team,
                "points": a.get("points", 0),
                "wins": 0,
            })
    except Exception as e:
        print(f"  [SBK] Nao foi possivel obter standings: {e}")
    return standings


def fetch_sbk_calendar():
    """Calendario WorldSBK via API oficial; lista vazia em caso de falha."""
    calendar = []
    try:
        data = _sbk_get(f"/wsbk-events/v1/seasons/{YEAR}/rounds")
        today = date.today().isoformat()
        for r in data.get("data", []):
            cats = [c.get("id") for c in
                    r.get("relationships", {}).get("categories", {}).get("data", [])]
            if "SBK" not in cats:
                continue
            a = r.get("attributes", {})
            ds = (a.get("start_date") or "")[:10]
            de = (a.get("end_date") or "")[:10]
            calendar.append({
                "round": a.get("sequence_order", 0),
                "name": a.get("description") or a.get("name", ""),
                "circuit": a.get("brief_description", ""),
                "country_iso": _SBK_ISO3.get(a.get("country_iso", ""), ""),
                "date_start": ds,
                "date_end": de,
                "finished": a.get("status") == "FINISHED" or (de != "" and de < today),
            })
        calendar.sort(key=lambda e: (e["round"] or 99, e["date_start"]))
    except Exception as e:
        print(f"  [SBK] Nao foi possivel obter calendario: {e}")
    return calendar


def fetch_sbk_data():
    """Dados SBK: calendario + standings via API oficial (fallback hardcoded)."""
    print("  A buscar calendario SBK...")
    calendar = fetch_sbk_calendar()
    if calendar:
        print(f"  -> {len(calendar)} rondas (API)")
    else:
        today = date.today().isoformat()
        calendar = [dict(ev, finished=ev["date_end"] < today) for ev in SBK_CALENDAR_2026]
        print(f"  -> {len(calendar)} rondas (fallback hardcoded)")

    print("  A buscar classificacao SBK...")
    standings = fetch_sbk_standings()
    print(f"  -> {len(standings)} pilotos SBK encontrados")

    return {
        "standings": standings,
        "calendar": calendar,
    }


def main():
    print(f"A buscar dados MotoGP {YEAR}...")

    season_uuid = find_season_uuid()
    print(f"  Temporada {YEAR}: {season_uuid}")

    category_uuid = find_category_uuid(season_uuid)
    print(f"  Categoria MotoGP: {category_uuid}")

    print("  A buscar calendário MotoGP...")
    calendar = fetch_calendar(season_uuid)
    print(f"  -> {len(calendar)} corridas")

    print("  A buscar classificação MotoGP...")
    standings = fetch_standings(season_uuid, category_uuid)
    print(f"  -> Top {len(standings)} pilotos")

    print(f"\nA buscar dados WorldSBK {YEAR}...")
    sbk = fetch_sbk_data()
    print(f"  -> {len(sbk['calendar'])} rondas SBK")

    # Se o scraping SBK falhou, preservar standings existentes do JSON
    if not sbk["standings"]:
        try:
            with open("motogp-data.json", "r", encoding="utf-8") as f:
                old_data = json.load(f)
            old_sbk_standings = old_data.get("sbk", {}).get("standings", [])
            if old_sbk_standings:
                sbk["standings"] = old_sbk_standings
                print(f"  -> Preservados {len(old_sbk_standings)} standings SBK existentes")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    output = {
        "season": YEAR,
        "updated": date.today().isoformat(),
        "standings": standings,
        "calendar": calendar,
        "sbk": sbk,
    }

    with open("motogp-data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\nGravado: motogp-data.json")
    print("Pronto!")


if __name__ == "__main__":
    main()
