#!/usr/bin/env python3
"""
Recompute one player's rows in statistics/<year>.md directly from the scorecards.

Updates, in every year file where the player appears:
  * Season Batting / Season Batting (by ave)
  * Season Bowling / Season Bowling (by ave)
  * Career Batting / Career Batting (by Ave)      (cumulative to that season)
  * Career Bowling / Career Bowling (by ave)      (cumulative to that season)

Career figures are cumulative, so changing one season also changes every later
year's career rows — those are refreshed automatically.

Column layouts vary between year files, so each row is rebuilt using the number
of columns that row already has:
  Season Batting :  [Mat] Inns No Runs Ave
  Season Bowling :  [Mat] O M Runs Wkts Ave SR
  Career Batting :  Mat Inns No Runs Ave
  Career Bowling :  Mat O M R W Ave SR

After writing, any table whose ordering the change disturbed has the player's
row moved back to its correct position (only that row moves).

Usage:
    python3 update_statistics.py "Richard Earney"
    python3 update_statistics.py "Richard Earney" --dry-run
    python3 update_statistics.py "Richard Earney" --years 1992 2005
"""

import os, re, glob, sys, importlib.util

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    "up", os.path.join(SCRIPT_DIR, "update_profiles.py"))
_up = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_up)
EXCLUDED_ALL = _up.EXCLUDED_GAMES
NOTOUT       = _up.NOTOUT_DISMISSALS


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
    try: o = float(o)
    except ValueError: return 0
    f = int(o)
    return f * 6 + round((o - f) * 10)

def overs(b):
    return f"{b//6}.{b%6}" if b % 6 else str(b // 6)

def fmtnum(x):
    if isinstance(x, str): return x          # '-' passes through
    return f"{x:.2f}".rstrip('0').rstrip('.') if isinstance(x, float) else str(x)


def resolve(full_name):
    """'Richard Earney' -> ('R Earney', profile-slug, excluded-games)"""
    parts = full_name.strip().split()
    ab = (parts[0][0] + ' ' + ' '.join(parts[1:])) if len(parts) >= 2 else full_name
    slug = None
    for p in glob.glob(os.path.join(SCRIPT_DIR, "profiles", "*.md")):
        if fm(open(p).read(), 'title').strip().lower() == full_name.strip().lower():
            slug = os.path.basename(p)[:-3]; break
    ab = _up.NAME_ALIASES.get(slug, ab) if slug else ab
    return ab, slug, EXCLUDED_ALL.get(slug, frozenset())


def season_figures(abbrev, excluded):
    S = {}
    for ydir in sorted(glob.glob(os.path.join(SCRIPT_DIR, "[12][0-9][0-9][0-9]"))):
        y = os.path.basename(ydir)
        d = S.setdefault(y, dict(M=set(), I=0, NO=0, R=0, b=0, mdn=0, br=0, W=0, sp=0))
        head = rf'^\|\s*\*\*\s*{re.escape(abbrev)}(?:\s+(?:&#\d+;)+)*\s*\*\*\s*\|'
        for sc in sorted(glob.glob(os.path.join(ydir, "*.md"))):
            slug = os.path.basename(sc)[:-3]
            if slug == 'index' or (y, slug) in excluded:
                continue
            txt = open(sc).read()
            home, away = fm(txt, 'homeTeam'), fm(txt, 'awayTeam')
            cur = sec = bt = None
            for line in txt.split('\n'):
                h = re.match(r'^##\s+(.*)', line)
                if h:
                    t = (h.group(1).replace('{{page.title}}', fm(txt, 'title'))
                                   .replace('{{page.homeTeam}}', home)
                                   .replace('{{page.awayTeam}}', away).strip())
                    if re.search(r'\b(Innings|Batting)\b', t, re.I):
                        cur = re.sub(r'\b(Innings|Batting)\b', '', t, flags=re.I).strip(); sec = 'BAT'
                    elif re.search(r'Bowling', t, re.I):
                        sec = 'BOWL'
                        if cur is not None:
                            bt = (away if (home and cur.lower() == home.lower())
                                  else home if (away and cur.lower() == away.lower()) else '')
                    else:
                        sec = None
                    continue
                if sec is None or not re.search(head, line.strip()):
                    continue
                c = [x.strip() for x in line.split('|')]
                n = len(c); c2 = c[2] if n > 2 else ''
                if sec == 'BAT' and is_min(cur):
                    d['M'].add(slug)
                    if c2.lower() == 'dnb' or n != 6:
                        continue
                    ms = re.search(r'(\d+)', c[4])
                    if ms:
                        d['I'] += 1; d['R'] += int(ms.group(1))
                        if c2.lower() in NOTOUT or '&#42;' in c[4]:
                            d['NO'] += 1
                elif sec == 'BOWL' and is_min(bt) and n >= 7:
                    d['M'].add(slug); d['sp'] += 1
                    d['b'] += balls(c[2]); d['mdn'] += to_int(c[3])
                    d['br'] += to_int(c[4]); d['W'] += to_int(c[5])
    return {y: {**v, 'M': len(v['M'])} for y, v in S.items()}


def career_to(S, year):
    c = dict(M=0, I=0, NO=0, R=0, b=0, mdn=0, br=0, W=0)
    for y in sorted(S):
        if y > year: break
        for k in c: c[k] += S[y][k]
    return c


def build_row(player, kind, vals, ncols):
    if kind in ('season_bat', 'career_bat'):
        mat, inns, no, runs, ave = vals
        cols = ([mat] if ncols == 5 else []) + [inns, no, runs, ave]
    else:
        mat, o, m, r, w, ave, sr = vals
        cols = ([mat] if ncols == 7 else []) + [o, m, r, w, ave, sr]
    return f"| **{player}** | " + " | ".join(str(c) for c in cols) + " |"


def row_label(line):
    m = re.match(r'^\|\s*\*\*([^*]+)\*\*', line)
    return m.group(1).strip() if m else None

def matches_player(line, full, ab):
    lbl = row_label(line)
    return lbl is not None and lbl in (full, ab)

def classify(heading):
    low = heading.lower()
    if 'season' in low and 'batting' in low: return 'season_bat'
    if 'season' in low and 'bowling' in low: return 'season_bowl'
    if 'career' in low and 'batting' in low: return 'career_bat'
    if 'career' in low and 'bowling' in low: return 'career_bowl'
    return None


def sort_key_for(heading):
    low = heading.lower()
    if 'batting' in low: return (-1 if 'ave' in low else -2), False
    if 'bowling' in low: return (-2 if 'ave' in low else -3), ('ave' in low)
    return None, False


def resort(path, player, abbrev):
    """Move the player's row back into position in any table it disturbed."""
    lines = open(path).read().split('\n')
    cur = None; sections = {}
    for i, l in enumerate(lines):
        h = re.match(r'^##\s+(.*)', l)
        if h: cur = h.group(1).strip(); sections.setdefault(cur, [])
        elif cur is not None and re.match(r'^\|\s*\*\*[^*]+\*\*\s*\|', l):
            sections[cur].append(i)
    moved = []
    for name, idxs in sections.items():
        if len(idxs) < 3 or classify(name) is None: continue
        key, asc = sort_key_for(name)
        def val(l):
            m = re.match(r'^\|\s*\*\*[^*]+\*\*\s*\|(.*)\|\s*$', l)
            if not m: return None
            nums = [x.strip() for x in m.group(1).split('|')]
            if len(nums) < abs(key): return None
            try: return float(nums[key])
            except ValueError: return None
        rows = [lines[i] for i in idxs]
        bi = [k for k, l in enumerate(rows) if matches_player(l, player, abbrev)]
        if not bi: continue
        bi = bi[0]; brow = rows[bi]; bval = val(brow)
        if bval is None: continue
        others = [r for k, r in enumerate(rows) if k != bi]
        pos = len(others)
        for k, l in enumerate(others):
            v = val(l)
            if v is None: continue
            if (bval < v) if asc else (bval > v):
                pos = k; break
        if pos != bi:
            new = others[:pos] + [brow] + others[pos:]
            for slot, i in enumerate(idxs): lines[i] = new[slot]
            moved.append(f"{name}: {bi} -> {pos}")
    if moved:
        open(path, 'w').write('\n'.join(lines))
    return moved


def update_year(player, abbrev, year, S, dry):
    path = os.path.join(SCRIPT_DIR, "statistics", f"{year}.md")
    if not os.path.exists(path): return []
    txt = open(path).read()
    if f"**{player}**" not in txt and f"**{abbrev}**" not in txt: return []
    s = S.get(year); c = career_to(S, year)
    if s is None: return []

    s_ave  = round(s['R'] / (s['I'] - s['NO']), 2) if s['I'] > s['NO'] else '-'
    s_bave = round(s['br'] / s['W'], 2) if s['W'] else '-'
    s_sr   = round(s['b'] / s['W'], 2) if s['W'] else '-'
    c_ave  = round(c['R'] / (c['I'] - c['NO']), 2) if c['I'] > c['NO'] else '-'
    c_bave = round(c['br'] / c['W'], 2) if c['W'] else '-'
    c_sr   = round(c['b'] / c['W'], 2) if c['W'] else '-'
    want = {
        'season_bat':  (s['M'], s['I'], s['NO'], s['R'], fmtnum(s_ave)),
        'season_bowl': (s['sp'], overs(s['b']), s['mdn'], s['br'], s['W'], fmtnum(s_bave), fmtnum(s_sr)),
        'career_bat':  (c['M'], c['I'], c['NO'], c['R'], fmtnum(c_ave)),
        'career_bowl': (c['M'], overs(c['b']), c['mdn'], c['br'], c['W'], fmtnum(c_bave), fmtnum(c_sr)),
    }

    lines = txt.split('\n')

    # modal column count per section — the table's real shape, so we match it
    # rather than assume (some years carry an undeclared Mat column).
    shape = {}; cur = None
    for l in lines:
        h = re.match(r'^##\s+(.*)', l)
        if h: cur = h.group(1).strip(); continue
        if cur and re.match(r'^\|\s*\*\*[^*]+\*\*\s*\|', l):
            n = len([x for x in l.split('|')[2:] if x.strip() != ''])
            shape.setdefault(cur, []).append(n)
    modal = {k: max(set(v), key=v.count) for k, v in shape.items() if v}

    out = []; cur = None; notes = []
    for line in lines:
        h = re.match(r'^##\s+(.*)', line)
        if h: cur = h.group(1).strip(); out.append(line); continue
        if cur and line.strip().startswith('|') and matches_player(line, player, abbrev):
            kind = classify(cur)
            if not kind: out.append(line); continue
            mine = len([x for x in line.split('|')[2:] if x.strip() != ''])
            ncols = modal.get(cur, mine)
            if mine != ncols:
                notes.append(f"  [{cur}] SKIPPED — row has {mine} cols, table uses {ncols}"
                             f"\n      {line.strip()}")
                out.append(line); continue
            label = row_label(line)
            new = build_row(label, kind, want[kind], ncols)
            built = len([x for x in new.split('|')[2:] if x.strip() != ''])
            if built != ncols:
                notes.append(f"  [{cur}] SKIPPED — table has {ncols} columns but this"
                             f" statistic needs {built} (column missing from the whole table)"
                             f"\n      {line.strip()}")
                out.append(line); continue
            if new.replace(' ', '') != line.strip().replace(' ', ''):
                notes.append(f"  [{cur}]\n      old: {line.strip()}\n      new: {new}")
            out.append(new); continue
        out.append(line)
    if not dry and notes:
        open(path, 'w').write('\n'.join(out))
        for m in resort(path, player, abbrev):
            notes.append(f"  re-sorted {m}")
    return notes


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args: sys.exit(__doc__)
    full = args[0]
    dry = '--dry-run' in sys.argv
    years = None
    if '--years' in sys.argv:
        years = [a for a in sys.argv[sys.argv.index('--years')+1:] if a.isdigit()]

    ab, slug, excl = resolve(full)
    print(f"player: {full}   scorecard name: {ab}   profile: {slug}")
    if excl: print(f"excluded games: {sorted(excl)}")
    S = season_figures(ab, excl)
    todo = years or sorted(S)
    changed = 0
    for y in todo:
        notes = update_year(full, ab, y, S, dry)
        if notes:
            changed += 1
            print(f"=== {y} ===")
            print("\n".join(notes))
    print(f"\n{changed} year file(s) {'would be ' if dry else ''}updated"
          f"{'  — DRY RUN, nothing written' if dry else ''}")


if __name__ == "__main__":
    main()
