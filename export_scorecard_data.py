#!/usr/bin/env python3
"""
Export everything the scorecards contain, as CSV, for cross-checking against
FileMaker (or any other record).

Writes three files into export/:

  innings.csv   one row per batting innings
                year, date, opponent, slug, player, position, dismissal,
                bowler, runs, not_out

  spells.csv    one row per bowling spell
                year, date, opponent, slug, player, overs, balls, maidens,
                runs, wickets

  seasons.csv   one row per player per season (the aggregate)
                year, player, matches, innings, not_outs, runs, bat_ave,
                spells, overs, maidens, runs_conceded, wickets, bowl_ave

Only appearances FOR The Min are included; guest appearances for the
opposition are excluded, using the same EXCLUDED_GAMES list as
update_profiles.py.

Usage:  python3 export_scorecard_data.py
"""

import os, re, csv, glob, importlib.util

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR    = os.path.join(SCRIPT_DIR, "export")

# reuse the canonical exclusion list / notion of "not out" from update_profiles
_spec = importlib.util.spec_from_file_location(
    "up", os.path.join(SCRIPT_DIR, "update_profiles.py"))
_up = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_up)
EXCLUDED = _up.EXCLUDED_GAMES
NOTOUT   = _up.NOTOUT_DISMISSALS


def fm(t, k):
    m = re.search(rf'^{k}:\s*(.*)$', t, re.M)
    return m.group(1).strip() if m else ''

def is_min(n):
    n = (n or '').strip().lower()
    return n in ('the min', 'min') or 'old min' in n or 'young min' in n

def to_int(x):
    x = (x or '').strip()
    return int(x) if x.isdigit() else 0

def balls(o):
    o = (o or '').strip()
    if not o:
        return 0
    try:
        o = float(o)
    except ValueError:
        return 0
    f = int(o)
    return f * 6 + round((o - f) * 10)

def overs_str(b):
    return f"{b//6}.{b%6}" if b % 6 else str(b // 6)

def excluded_for(player_abbrev, year, slug):
    """player abbrev -> is this game excluded for them?"""
    for slug_key, games in EXCLUDED.items():
        if (year, slug) in games:
            # map profile slug -> abbreviation
            p = os.path.join(SCRIPT_DIR, "profiles", slug_key + ".md")
            if os.path.exists(p):
                title = fm(open(p).read(), 'title')
                parts = title.split()
                ab = (parts[0][0] + ' ' + ' '.join(parts[1:])) if len(parts) >= 2 else title
                if ab == player_abbrev:
                    return True
    return False


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    innings, spells = [], []

    for ydir in sorted(glob.glob(os.path.join(SCRIPT_DIR, "[12][0-9][0-9][0-9]"))):
        year = os.path.basename(ydir)
        for sc in sorted(glob.glob(os.path.join(ydir, "*.md"))):
            slug = os.path.basename(sc)[:-3]
            if slug == 'index':
                continue
            txt  = open(sc).read()
            home, away = fm(txt, 'homeTeam'), fm(txt, 'awayTeam')
            title, date = fm(txt, 'title'), fm(txt, 'date')
            opponent = away if is_min(home) else home
            cur = sec = bt = None
            pos = 0
            for line in txt.split('\n'):
                h = re.match(r'^##\s+(.*)', line)
                if h:
                    t = (h.group(1).replace('{{page.title}}', title)
                                   .replace('{{page.homeTeam}}', home)
                                   .replace('{{page.awayTeam}}', away).strip())
                    if re.search(r'\b(Innings|Batting)\b', t, re.I):
                        cur = re.sub(r'\b(Innings|Batting)\b', '', t, flags=re.I).strip()
                        sec = 'BAT'; pos = 0
                    elif re.search(r'Bowling', t, re.I):
                        sec = 'BOWL'
                        if cur is not None:
                            bt = (away if (home and cur.lower() == home.lower())
                                  else home if (away and cur.lower() == away.lower()) else '')
                    else:
                        sec = None
                    continue
                m = re.match(r'^\|\s*\*\*([^*]+)\*\*\s*\|', line)
                if not m or sec is None:
                    continue
                raw = m.group(1)
                name = re.sub(r'\s*&#\d+;', '', raw).strip()
                if name.lower() in ('extras', 'total', 'batsman', 'score'):
                    continue
                cells = [c.strip() for c in line.split('|')]
                n = len(cells); c2 = cells[2] if n > 2 else ''

                if sec == 'BAT' and is_min(cur):
                    pos += 1
                    if excluded_for(name, year, slug):
                        continue
                    if c2.lower() == 'dnb' or n != 6:
                        continue
                    ms = re.search(r'(\d+)', cells[4])
                    if not ms:
                        continue
                    no = (c2.lower() in NOTOUT) or ('&#42;' in cells[4])
                    innings.append(dict(year=year, date=date, opponent=opponent or title,
                                        slug=slug, player=name, position=pos,
                                        dismissal=c2, bowler=cells[3], runs=int(ms.group(1)),
                                        not_out=int(no)))
                elif sec == 'BOWL' and is_min(bt) and n >= 7:
                    if excluded_for(name, year, slug):
                        continue
                    b = balls(cells[2])
                    spells.append(dict(year=year, date=date, opponent=opponent or title,
                                       slug=slug, player=name, overs=cells[2], balls=b,
                                       maidens=to_int(cells[3]), runs=to_int(cells[4]),
                                       wickets=to_int(cells[5])))

    # ---- per-season aggregate ----
    agg = {}
    for r in innings:
        d = agg.setdefault((r['year'], r['player']),
                           dict(games=set(), I=0, NO=0, R=0, sp=0, b=0, mdn=0, rc=0, W=0))
        d['games'].add(r['slug']); d['I'] += 1; d['R'] += r['runs']; d['NO'] += r['not_out']
    for r in spells:
        d = agg.setdefault((r['year'], r['player']),
                           dict(games=set(), I=0, NO=0, R=0, sp=0, b=0, mdn=0, rc=0, W=0))
        d['games'].add(r['slug']); d['sp'] += 1; d['b'] += r['balls']
        d['mdn'] += r['maidens']; d['rc'] += r['runs']; d['W'] += r['wickets']

    seasons = []
    for (year, player), d in sorted(agg.items()):
        outs = d['I'] - d['NO']
        seasons.append(dict(
            year=year, player=player, matches=len(d['games']), innings=d['I'],
            not_outs=d['NO'], runs=d['R'],
            bat_ave=round(d['R'] / outs, 2) if outs else '',
            spells=d['sp'], overs=overs_str(d['b']), maidens=d['mdn'],
            runs_conceded=d['rc'], wickets=d['W'],
            bowl_ave=round(d['rc'] / d['W'], 2) if d['W'] else ''))

    for fname, rows in (("innings.csv", innings), ("spells.csv", spells),
                        ("seasons.csv", seasons)):
        p = os.path.join(OUT_DIR, fname)
        with open(p, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"  {p}  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
