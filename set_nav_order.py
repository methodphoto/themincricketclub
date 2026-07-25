#!/usr/bin/env python3
"""
Add / refresh `nav_order:` frontmatter on every scorecard so the sidebar menu
lists each season's games in the order they were played.

The running order is taken from that season's `index.md` — the fixture list —
by reading its match links from top to bottom.  The first fixture gets
`nav_order: 1`, the second `2`, and so on, matching the convention already used
for 1983.

`nav_order` is written as the last line of the frontmatter (after `parent:`).
Re-running is safe: an existing `nav_order` is corrected in place rather than
duplicated, and a file already holding the right value is left untouched.

Scorecards that are not linked from their season index get no `nav_order` and
are reported — Just the Docs sorts those after the numbered pages.

Usage:
  python3 set_nav_order.py --dry-run     # report only, write nothing
  python3 set_nav_order.py               # apply
  python3 set_nav_order.py 1996 1997     # limit to specific years
"""

import os, re, glob, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def ordered_slugs(index_path):
    """Match slugs from a season index.md, in the order they appear."""
    txt = open(index_path).read()
    slugs = []
    for m in re.finditer(r'\[([^\]]+)\]\(\s*([^)\s#][^)]*?)\s*\)', txt):
        target = m.group(2).strip()
        # skip external links, season nav (../1984), anchors, absolute paths
        if target.startswith(('http', '../', '/', '#', 'mailto:')):
            continue
        slug = target.rstrip('/').split('/')[-1]
        if slug.endswith('.md'):
            slug = slug[:-3]
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


def set_nav_order(path, order):
    """Insert or update nav_order in the frontmatter. Returns action taken."""
    txt = open(path).read()
    m = re.match(r'^(---\s*\n)(.*?)(\n---\s*\n)', txt, re.S)
    if not m:
        return "NO-FRONTMATTER"
    head, body, tail = m.group(1), m.group(2), m.group(3)

    existing = re.search(r'^nav_order:\s*(.*)$', body, re.M)
    if existing:
        if existing.group(1).strip() == str(order):
            return "OK"                                  # already correct
        body = re.sub(r'^nav_order:.*$', f'nav_order: {order}', body, count=1, flags=re.M)
        action = "UPDATED"
    else:
        body = body.rstrip('\n') + f'\nnav_order: {order}'
        action = "ADDED"

    open(path, 'w').write(head + body + tail + txt[m.end():])
    return action


def main():
    years = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in sys.argv

    dirs = ([os.path.join(SCRIPT_DIR, y) for y in years] if years
            else sorted(glob.glob(os.path.join(SCRIPT_DIR, "[12][0-9][0-9][0-9]"))))

    added = updated = ok = 0
    unlinked, problems = [], []

    for ydir in dirs:
        year = os.path.basename(ydir)
        index = os.path.join(ydir, "index.md")
        if not os.path.exists(index):
            problems.append(f"{year}: no index.md")
            continue

        slugs = ordered_slugs(index)
        present = {os.path.basename(f)[:-3] for f in glob.glob(os.path.join(ydir, "*.md"))} - {'index'}

        for n, slug in enumerate(slugs, start=1):
            path = os.path.join(ydir, slug + ".md")
            if not os.path.exists(path):
                problems.append(f"{year}: index links '{slug}' but no such file")
                continue
            action = "OK" if dry and False else (
                set_nav_order(path, n) if not dry else _preview(path, n))
            if action == "ADDED":   added += 1
            elif action == "UPDATED": updated += 1
            elif action == "OK":      ok += 1
            else: problems.append(f"{year}/{slug}: {action}")

        for slug in sorted(present - set(slugs)):
            unlinked.append(f"{year}/{slug}")

    verb = "would be" if dry else ""
    print(f"added {verb} {added}   updated {verb} {updated}   already correct {ok}")
    if unlinked:
        print(f"\nnot linked from their season index ({len(unlinked)}) — left without nav_order:")
        for u in unlinked: print(f"  {u}")
    if problems:
        print(f"\nproblems ({len(problems)}):")
        for p in problems: print(f"  {p}")
    if dry:
        print("\nDRY RUN — nothing written")


def _preview(path, order):
    txt = open(path).read()
    m = re.search(r'^nav_order:\s*(.*)$', txt, re.M)
    if not m:
        return "ADDED"
    return "OK" if m.group(1).strip() == str(order) else "UPDATED"


if __name__ == "__main__":
    main()
