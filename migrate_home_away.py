#!/usr/bin/env python3
"""
Migrate Min CC scorecards from `{{page.title}}` innings headings to explicit
home/away headings, adding `homeTeam:` / `awayTeam:` to the frontmatter.

Before:                          After (Min away — the normal case):
  title: Stowting                  title: Stowting
  ...                              homeTeam: Stowting
  ## {{page.title}} Innings        awayTeam: The Min
  ## The Min Innings               ...
                                   ## {{page.homeTeam}} Innings
                                   ## {{page.awayTeam}} Innings

At grounds where The Min is the home side the two are reversed, so the Min's
innings becomes `{{page.homeTeam}}` and the opponent's `{{page.awayTeam}}`.

Heading ORDER is never changed — it reflects who batted first, not who was at
home.  Only the label on each heading changes.

Usage:
  python3 migrate_home_away.py --dry-run     # report only
  python3 migrate_home_away.py               # apply
"""

import os, re, glob, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Grounds where The Min is the HOME side.
MIN_HOME_LOCATIONS = {
    "solefields",
    "dinder cricket ground",
    "reigate grammar school",
    "toddington manor",
    "toddington",              # same ground, older spelling
}

# (location, opponent-title) pairs that override the above — Min was AWAY.
MIN_HOME_EXCEPTIONS = {
    ("reigate grammar school", "hartswood occasionals"),
}

# Intra-club games — both sides are Min, so the ground does not decide home/away.
# The Old Min are the home side in both fixtures.  These are already migrated
# (they use {{page.homeTeam}}/{{page.awayTeam}}), so the script reports them as
# ALREADY; the mapping is recorded here for reference.
INTRA_CLUB = {
    "2007/old-min-young-min.md": ("The Old Min", "The Young Min"),
    "2008/old-min-young-min.md": ("The Old Min", "The Young Min"),
}
SKIP_FILES = set()

MIN_HEAD = re.compile(r'^##\s*(?:The\s+)?Min\s+(?:Innings|Batting)\s*$', re.I)
ANY_HEAD = re.compile(r'^##\s*(.*(?:Innings|Batting).*?)\s*$', re.I)


def fm(txt, key):
    m = re.search(rf'^{key}:\s*(.*)$', txt, re.MULTILINE)
    return m.group(1).strip() if m else None


def migrate(path, dry_run=True):
    rel = path.replace(SCRIPT_DIR + os.sep, "").replace(os.sep, "/")
    txt = open(path).read()

    if rel in SKIP_FILES:
        return ("SKIP", rel, "intra-club game (Old Min v Young Min)")
    if '| Batsman' not in txt:
        return None                                   # not a scorecard
    if '{{page.homeTeam}}' in txt or '{{page.awayTeam}}' in txt:
        return ("ALREADY", rel, "already uses home/away")

    lines = txt.splitlines()
    head_idx = [i for i, l in enumerate(lines) if ANY_HEAD.match(l)]
    if len(head_idx) != 2:
        return ("SKIP", rel, f"expected 2 innings headings, found {len(head_idx)}")

    min_i = [i for i in head_idx if MIN_HEAD.match(lines[i])]
    opp_i = [i for i in head_idx if i not in min_i]
    if len(min_i) != 1 or len(opp_i) != 1:
        return ("SKIP", rel, "could not identify the Min innings heading")
    min_i, opp_i = min_i[0], opp_i[0]

    opponent = (fm(txt, 'title') or '').strip()
    if not opponent:
        return ("SKIP", rel, "no title in frontmatter")

    loc = (fm(txt, 'location') or '').strip().lower()
    min_home = loc in MIN_HOME_LOCATIONS
    if (loc, opponent.lower()) in MIN_HOME_EXCEPTIONS:
        min_home = False

    if min_home:
        home_team, away_team = "The Min", opponent
        lines[min_i] = "## {{page.homeTeam}} Innings"
        lines[opp_i] = "## {{page.awayTeam}} Innings"
    else:
        home_team, away_team = opponent, "The Min"
        lines[opp_i] = "## {{page.homeTeam}} Innings"
        lines[min_i] = "## {{page.awayTeam}} Innings"

    # Insert homeTeam/awayTeam into frontmatter, directly after the title line.
    out, done = [], False
    for l in lines:
        out.append(l)
        if not done and re.match(r'^title:', l):
            out.append(f"homeTeam: {home_team}")
            out.append(f"awayTeam: {away_team}")
            done = True
    if not done:
        return ("SKIP", rel, "could not place frontmatter")

    if not dry_run:
        open(path, 'w').write('\n'.join(out) + '\n')
    return ("MIN-HOME" if min_home else "OK", rel, f"home={home_team} | away={away_team}")


def main():
    dry = '--dry-run' in sys.argv
    results = []
    for ydir in sorted(glob.glob(os.path.join(SCRIPT_DIR, "[12][0-9][0-9][0-9]"))):
        for sc in sorted(glob.glob(os.path.join(ydir, "*.md"))):
            if os.path.basename(sc) == 'index.md':
                continue
            r = migrate(sc, dry_run=dry)
            if r:
                results.append(r)

    for tag in ("MIN-HOME", "SKIP", "ALREADY"):
        rows = [r for r in results if r[0] == tag]
        if rows:
            print(f"\n=== {tag} ({len(rows)}) ===")
            for _, rel, note in rows:
                print(f"  {rel:40s} {note}")
    ok = [r for r in results if r[0] == "OK"]
    print(f"\n=== OK — Min away, converted ({len(ok)}) ===")
    print(f"  (listing suppressed; {len(ok)} files)")
    print(f"\nTOTAL processed: {len(results)}   {'DRY RUN — nothing written' if dry else 'WRITTEN'}")


if __name__ == "__main__":
    main()
