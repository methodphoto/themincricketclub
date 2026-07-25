#!/usr/bin/env python3
"""
Compare a FileMaker export against what the scorecards say.

Run export_scorecard_data.py first, then point this at your FileMaker CSV:

    python3 reconcile_filemaker.py ~/Desktop/fm_export.csv

It figures out the columns itself (case/spacing/underscore insensitive) and
works at whichever level your export is:

  season level   needs: player, year   plus any of
                 runs / innings / not_outs / wickets / maidens / runs_conceded
  innings level  needs: player, year, runs   and ideally opponent
                 (rows are summed per player-season before comparing)

Player names are matched on the "R Beswick" form. If FileMaker stores
"Richard Beswick" or "Beswick, Richard" that is handled too.

Output: a per-season table of every figure that differs, plus a summary of
which side is missing games. Nothing is written or changed.

Options:
    --player "R Beswick"    limit to one player
    --year 1990             limit to one season
    --map fmcol=ourcol      force a column mapping (repeatable)
"""

import os, re, csv, sys, glob
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(SCRIPT_DIR, "export")

CANON = {
    'player':        ['player', 'name', 'playername', 'fullname', 'batsman', 'bowler'],
    'year':          ['year', 'season', 'seasonyear'],
    'opponent':      ['opponent', 'opposition', 'against', 'team', 'vs'],
    'matches':       ['matches', 'mat', 'games', 'played', 'm'],
    'innings':       ['innings', 'inns', 'in'],
    'not_outs':      ['notouts', 'notout', 'nos', 'no'],
    'runs':          ['runs', 'runsscored', 'score', 'r'],
    'spells':        ['spells', 'bowlingmatches', 'bowled'],
    'overs':         ['overs', 'o'],
    'maidens':       ['maidens', 'mdns', 'mdn'],
    'runs_conceded': ['runsconceded', 'runsagainst', 'conceded', 'rc'],
    'wickets':       ['wickets', 'wkts', 'w'],
}

def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def abbrev(name):
    """'Richard Beswick' / 'Beswick, Richard' / 'R Beswick' -> 'R Beswick'"""
    name = (name or '').strip()
    if not name:
        return ''
    if ',' in name:
        last, first = [p.strip() for p in name.split(',', 1)]
        return f"{first[:1]} {last}" if first else last
    parts = name.split()
    if len(parts) >= 2 and len(parts[0]) > 1 and parts[0][0].isupper():
        return f"{parts[0][0]} {' '.join(parts[1:])}"
    return name

def num(x):
    x = str(x or '').strip().replace('*', '')
    if not x:
        return None
    try:
        return float(x) if '.' in x else int(x)
    except ValueError:
        return None


def detect_columns(header, forced):
    mapping = {}
    nh = {norm(h): h for h in header}
    for canon, aliases in CANON.items():
        for a in aliases:
            if a in nh:
                mapping[canon] = nh[a]; break
    mapping.update(forced)
    return mapping


def load_ours():
    p = os.path.join(EXPORT_DIR, "seasons.csv")
    if not os.path.exists(p):
        sys.exit("Run  python3 export_scorecard_data.py  first.")
    out = {}
    for r in csv.DictReader(open(p)):
        out[(r['year'], r['player'])] = r
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    path = args[0]
    only_player = None; only_year = None; forced = {}
    for i, a in enumerate(sys.argv):
        if a == '--player': only_player = abbrev(sys.argv[i+1])
        if a == '--year':   only_year = sys.argv[i+1]
        if a == '--map':
            k, v = sys.argv[i+1].split('=', 1); forced[v] = k

    rows = list(csv.DictReader(open(path, newline='', encoding='utf-8-sig')))
    if not rows:
        sys.exit("empty CSV")
    cols = detect_columns(rows[0].keys(), forced)
    print("Detected columns:")
    for k, v in cols.items():
        print(f"   {k:14s} <- {v!r}")
    missing = [k for k in ('player', 'year') if k not in cols]
    if missing:
        sys.exit(f"\nCould not find column(s) for: {missing}. Use --map fmcolumn=ourname")

    # fold FileMaker rows to player-season
    fm = defaultdict(lambda: defaultdict(int))
    seen_rows = defaultdict(int)
    for r in rows:
        p = abbrev(r.get(cols['player']))
        y = str(r.get(cols['year']) or '').strip()[:4]
        if not p or not y.isdigit():
            continue
        if only_player and p != only_player: continue
        if only_year and y != only_year: continue
        key = (y, p); seen_rows[key] += 1
        for field in ('matches', 'innings', 'not_outs', 'runs', 'spells',
                      'maidens', 'runs_conceded', 'wickets'):
            if field in cols:
                v = num(r.get(cols[field]))
                if v is not None:
                    fm[key][field] += v

    ours = load_ours()
    per_innings = 'innings' not in cols and 'runs' in cols  # summed rows
    compare = [f for f in ('matches', 'innings', 'not_outs', 'runs',
                           'spells', 'maidens', 'runs_conceded', 'wickets')
               if f in cols]
    if per_innings:
        compare = [f for f in compare if f != 'matches']

    print(f"\nComparing: {', '.join(compare)}"
          f"{'   (FileMaker rows summed per player-season)' if per_innings else ''}\n")

    diffs = 0; only_fm = []; only_us = []
    keys = set(fm) | {k for k in ours
                      if (not only_player or k[1] == only_player)
                      and (not only_year or k[0] == only_year)}
    for key in sorted(keys):
        y, p = key
        o = ours.get(key)
        f = fm.get(key)
        if o and not f:
            only_us.append(key); continue
        if f and not o:
            only_fm.append(key); continue
        bad = []
        for field in compare:
            ov = num(o.get(field))
            fv = f.get(field)
            if ov is None and fv is None: continue
            if (ov or 0) != (fv or 0):
                bad.append(f"{field}: FM {fv} vs scorecards {ov}")
        if bad:
            diffs += 1
            print(f"{y}  {p}")
            for b in bad:
                print(f"      {b}")

    print(f"\n{'-'*60}")
    print(f"player-seasons with differences : {diffs}")
    print(f"in FileMaker but not scorecards : {len(only_fm)}")
    for k in only_fm[:15]: print(f"      {k[0]}  {k[1]}")
    if len(only_fm) > 15: print(f"      ... and {len(only_fm)-15} more")
    print(f"in scorecards but not FileMaker : {len(only_us)}")
    for k in only_us[:15]: print(f"      {k[0]}  {k[1]}")
    if len(only_us) > 15: print(f"      ... and {len(only_us)-15} more")


if __name__ == "__main__":
    main()
