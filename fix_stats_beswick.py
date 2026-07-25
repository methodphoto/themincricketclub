#!/usr/bin/env python3
"""
Recompute Richard Beswick's rows in statistics/<year>.md from the scorecards.

Updates, for each requested year:
  * Season Batting  / Season Batting (by ave)
  * Season Bowling  / Season Bowling (by ave)
  * Career Batting  / Career Batting (by Ave)     (cumulative to that season)
  * Career Bowling  / Career Bowling (by ave)     (cumulative to that season)

Column layouts vary between files, so each row is rebuilt using the number of
columns already present in that row rather than a fixed template:
  Season Batting :  [Mat] Inns No Runs Ave        (Mat present in some years)
  Season Bowling :  [Mat] O M Runs Wkts Ave SR
  Career Batting :  Mat Inns No Runs Ave
  Career Bowling :  Mat O M R W Ave SR

Usage:  python3 fix_stats_beswick.py --dry-run [years...]
        python3 fix_stats_beswick.py [years...]
"""
import os, re, glob, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYER_ROW = "Richard Beswick"
ABBREV     = "R Beswick"
EXCLUDED   = {("1997", "captain-scott-xi")}          # guested for Captain Scott XI
NOTOUT     = {"not out", "retired hurt", "retired not out"}

head_re = rf'^\|\s*\*\*\s*{re.escape(ABBREV)}(?:\s+(?:&#\d+;)+)*\s*\*\*\s*\|'


def fm(t, k):
    m = re.search(rf'^{k}:\s*(.*)$', t, re.M)
    return m.group(1).strip() if m else None

def is_min(n):
    n = (n or '').strip().lower()
    return n in ('the min', 'min') or 'old min' in n or 'young min' in n

def to_int(x):
    x = x.strip()
    return int(x) if x.isdigit() else 0

def balls(o):
    o = o.strip()
    if not o:
        return 0
    o = float(o); f = int(o)
    return f * 6 + round((o - f) * 10)

def overs(b):
    return f"{b//6}.{b%6}" if b % 6 else str(b // 6)


def season_figures():
    """{year: dict} of Beswick's Min-only figures, per season."""
    S = {}
    for ydir in sorted(glob.glob(os.path.join(SCRIPT_DIR, "[12][0-9][0-9][0-9]"))):
        y = os.path.basename(ydir)
        d = S.setdefault(y, dict(M=set(), I=0, NO=0, R=0, b=0, mdn=0, br=0, W=0, sp=0))
        for sc in sorted(glob.glob(os.path.join(ydir, "*.md"))):
            slug = os.path.basename(sc)[:-3]
            if slug == 'index' or (y, slug) in EXCLUDED:
                continue
            txt = open(sc).read()
            home, away = fm(txt, 'homeTeam'), fm(txt, 'awayTeam')
            cur = sec = bt = None
            for line in txt.splitlines():
                h = re.match(r'^##\s+(.*)', line)
                if h:
                    t = (h.group(1).replace('{{page.title}}', fm(txt, 'title') or '')
                                   .replace('{{page.homeTeam}}', home or '')
                                   .replace('{{page.awayTeam}}', away or '').strip())
                    if re.search(r'\b(Innings|Batting)\b', t, re.I):
                        cur = re.sub(r'\b(Innings|Batting)\b', '', t, flags=re.I).strip(); sec = 'BAT'
                    elif re.search(r'Bowling', t, re.I):
                        sec = 'BOWL'
                        if cur is not None:
                            bt = (away if (home and cur.lower() == home.lower())
                                  else home if (away and cur.lower() == away.lower()) else None)
                    else:
                        sec = None
                    continue
                if sec is None or not re.search(head_re, line.strip()):
                    continue
                c = [x.strip() for x in line.strip().split('|')]
                n = len(c); c2 = c[2] if n > 2 else ''
                if sec == 'BAT' and is_min(cur):
                    d['M'].add(slug)
                    if c2.lower() == 'dnb':
                        continue
                    if n == 6:
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
        if y > year:
            break
        for k in c:
            c[k] += S[y][k]
    return c


def fmtnum(x):
    return f"{x:.2f}".rstrip('0').rstrip('.') if isinstance(x, float) else str(x)


def build_row(kind, vals_with_mat, ncols):
    """Rebuild a row honouring how many numeric columns the file uses."""
    if kind in ('season_bat', 'career_bat'):
        mat, inns, no, runs, ave = vals_with_mat
        cols = ([mat] if ncols == 5 else []) + [inns, no, runs, ave]
    else:
        mat, o, m, r, w, ave, sr = vals_with_mat
        cols = ([mat] if ncols == 7 else []) + [o, m, r, w, ave, sr]
    return f"| **{PLAYER_ROW}** | " + " | ".join(str(c) for c in cols) + " |"


def update_year(year, S, dry=False):
    path = os.path.join(SCRIPT_DIR, "statistics", f"{year}.md")
    if not os.path.exists(path):
        return [f"{year}: no statistics file"]
    txt = open(path).read()
    s = S[year]; c = career_to(S, year)

    s_ave  = round(s['R'] / (s['I'] - s['NO']), 2) if s['I'] > s['NO'] else 0
    s_bave = round(s['br'] / s['W'], 2) if s['W'] else 0
    s_sr   = round(s['b'] / s['W'], 2) if s['W'] else 0
    c_ave  = round(c['R'] / (c['I'] - c['NO']), 2) if c['I'] > c['NO'] else 0
    c_bave = round(c['br'] / c['W'], 2) if c['W'] else 0
    c_sr   = round(c['b'] / c['W'], 2) if c['W'] else 0

    want = {
        'season_bat':  (s['M'], s['I'], s['NO'], s['R'], fmtnum(s_ave)),
        'season_bowl': (s['sp'], overs(s['b']), s['mdn'], s['br'], s['W'], fmtnum(s_bave), fmtnum(s_sr)),
        'career_bat':  (c['M'], c['I'], c['NO'], c['R'], fmtnum(c_ave)),
        'career_bowl': (c['M'], overs(c['b']), c['mdn'], c['br'], c['W'], fmtnum(c_bave), fmtnum(c_sr)),
    }

    # split on \n only — splitlines() also breaks on \x0b/\u2028 etc,
    # which appear inside some names and would corrupt those rows.
    lines = txt.split('\n'); out = []; cur = None; notes = []
    for line in lines:
        h = re.match(r'^##\s+(.*)', line)
        if h:
            cur = h.group(1).strip().lower(); out.append(line); continue
        if PLAYER_ROW in line and line.strip().startswith('|') and cur:
            if 'season' in cur and 'batting' in cur:   kind = 'season_bat'
            elif 'season' in cur and 'bowling' in cur: kind = 'season_bowl'
            elif 'career' in cur and 'batting' in cur: kind = 'career_bat'
            elif 'career' in cur and 'bowling' in cur: kind = 'career_bowl'
            else:
                out.append(line); continue
            ncols = len([x for x in line.strip().split('|')[2:] if x.strip() != ''])
            new = build_row(kind, want[kind], ncols)
            if new.replace(' ', '') != line.strip().replace(' ', ''):
                notes.append(f"  [{cur}]\n      old: {line.strip()}\n      new: {new}")
            out.append(new); continue
        out.append(line)
    new_txt = '\n'.join(out)
    if not dry and new_txt != txt:
        open(path, 'w').write(new_txt)
    return notes


def main():
    dry = '--dry-run' in sys.argv
    years = [a for a in sys.argv[1:] if a.isdigit()] or \
            ["1990", "1992", "1996", "1999", "2011", "2014", "2018", "2019"]
    S = season_figures()
    for y in years:
        notes = update_year(y, S, dry)
        print(f"=== {y} ===")
        print("\n".join(notes) if notes else "  (already correct)")
    print("\nDRY RUN — nothing written" if dry else "\nWritten.")


if __name__ == "__main__":
    main()
