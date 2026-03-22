# ScorecardMacApp

A SwiftUI macOS app for creating cricket scorecard markdown files in the same format used by this repository.

## Features

- Create and manage multiple match drafts.
- Assign each match to a season (year folder like `2025`, `2026`, etc.).
- Input frontmatter fields (`layout`, `title`, teams, location, date, report, result, `next`, `parent`, plus extra YAML lines).
- Set first/second-innings team labels independently of home/away, with quick Home-first/Away-first buttons.
- Optional Google Maps URL for location. If provided, location is exported as a markdown link.
- Enter batting (fixed 11 slots), fall of wickets, bowling (minimum 4 bowlers, add more as needed), and win/loss sections for both innings.
- Insert image markdown blocks:
  - below `{% include newMatchDetails %}`
  - below `{% include nextGame %}`
- Live markdown preview.
- Export directly to `<outputRoot>/<season>/<slug>.md`.

## Run

From this folder:

```bash
swift run
```

Or open `Package.swift` in Xcode and run the `ScorecardMacApp` target.

## Output Format

The exported markdown follows the pattern used by files such as:

- `2025/highgate-irregulars.md`

including frontmatter, include blocks, innings sections, and win/loss table.
