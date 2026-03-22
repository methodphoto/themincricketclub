import Foundation

struct BattingRow: Codable, Identifiable, Hashable {
    var id: UUID = UUID()
    var batsman: String = ""
    var dismissalPrimary: String = ""
    var dismissalSecondary: String = ""
    var runs: String = ""
}

struct BowlingRow: Codable, Identifiable, Hashable {
    var id: UUID = UUID()
    var bowler: String = ""
    var overs: String = ""
    var maidens: String = ""
    var runs: String = ""
    var wickets: String = ""
}

struct ImageBlock: Codable, Identifiable, Hashable {
    var id: UUID = UUID()
    var altText: String = ""
    var pathOrURL: String = ""

    var markdownLine: String {
        let alt = altText.isEmpty ? "Match image" : altText
        return "![\(alt)](\(pathOrURL))"
    }
}

struct Innings: Codable, Hashable {
    static let batterSlotCount = 11
    static let minimumBowlerCount = 4

    var battingRows: [BattingRow] = Self.makeEmptyBattingRows(count: Self.batterSlotCount)
    var extrasBreakdown: String = ""
    var extrasRuns: String = ""
    var totalOvers: String = ""
    var totalSummary: String = ""
    var fallScores: [String] = Array(repeating: "", count: 10)
    var fallBatters: [String] = Array(repeating: "", count: 10)
    var bowlingRows: [BowlingRow] = Self.makeEmptyBowlingRows(count: Self.minimumBowlerCount)

    mutating func normalizeForEditing() {
        if battingRows.count < Self.batterSlotCount {
            battingRows.append(contentsOf: Self.makeEmptyBattingRows(count: Self.batterSlotCount - battingRows.count))
        }
        if bowlingRows.count < Self.minimumBowlerCount {
            bowlingRows.append(contentsOf: Self.makeEmptyBowlingRows(count: Self.minimumBowlerCount - bowlingRows.count))
        }
    }

    func normalizedBattingRows() -> [BattingRow] {
        if battingRows.count >= Self.batterSlotCount {
            return Array(battingRows.prefix(Self.batterSlotCount))
        }
        return battingRows + Self.makeEmptyBattingRows(count: Self.batterSlotCount - battingRows.count)
    }

    private static func makeEmptyBattingRows(count: Int) -> [BattingRow] {
        (0..<count).map { _ in BattingRow() }
    }

    private static func makeEmptyBowlingRows(count: Int) -> [BowlingRow] {
        (0..<count).map { _ in BowlingRow() }
    }
}

struct WinLoss: Codable, Hashable {
    var won: String = ""
    var lost: String = ""
    var drawn: String = ""
    var tied: String = ""
}

struct MatchDraft: Codable, Identifiable, Hashable {
    var id: UUID = UUID()

    var season: String = String(Calendar.current.component(.year, from: Date()))
    var slug: String = ""

    var layout: String = "default"
    var title: String = ""
    var homeTeam: String = ""
    var awayTeam: String = "The Min"
    var firstInningsTeam: String? = nil
    var secondInningsTeam: String? = nil
    var locationName: String = ""
    var googleMapsURL: String = ""
    var date: String = ""
    var report: String = ""
    var result: String = ""
    var nextGamePath: String = ""
    var parent: String = ""
    var additionalFrontmatter: String = ""

    var notesAfterNewMatchDetails: String = ""
    var notesBeforeNextGame: String = ""

    var imagesAfterNewMatchDetails: [ImageBlock] = []
    var imagesAfterNextGame: [ImageBlock] = []

    var homeInnings: Innings = Innings()
    var awayInnings: Innings = Innings()
    var winLoss: WinLoss = WinLoss()

    init() {
        if parent.isEmpty {
            parent = "\(season) Fixtures"
        }
        homeInnings.normalizeForEditing()
        awayInnings.normalizeForEditing()
    }

    mutating func normalizeForEditing() {
        homeInnings.normalizeForEditing()
        awayInnings.normalizeForEditing()
    }

    var displayName: String {
        let matchTitle = title.isEmpty ? "Untitled match" : title
        return "\(season) • \(matchTitle)"
    }

    var resolvedSlug: String {
        if !slug.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return Self.slugify(slug)
        }
        return Self.slugify(title)
    }

    static func slugify(_ input: String) -> String {
        let lower = input.lowercased()
        let transformed = lower.replacingOccurrences(
            of: "[^a-z0-9]+",
            with: "-",
            options: .regularExpression
        )
        let trimmed = transformed.trimmingCharacters(in: CharacterSet(charactersIn: "-"))
        return trimmed.isEmpty ? "new-match" : trimmed
    }

    func markdown() -> String {
        var lines: [String] = []

        lines.append("---")
        lines.append("layout: \(yamlValue(layout))")
        lines.append("title: \(yamlValue(title))")
        lines.append("homeTeam: \(yamlValue(homeTeam))")
        lines.append("awayTeam: \(yamlValue(awayTeam))")
        lines.append("location: \(yamlValue(locationValue()))")
        lines.append("date: \(yamlValue(date))")
        lines.append("report: \(yamlValue(report))")
        lines.append("result: \(yamlValue(result))")
        lines.append("next: \(yamlValue(nextGamePath))")
        let resolvedParent = parent.isEmpty ? "\(season) Fixtures" : parent
        lines.append("parent: \(yamlValue(resolvedParent))")

        let additional = additionalFrontmatter
            .split(separator: "\n", omittingEmptySubsequences: false)
            .map(String.init)
            .map { $0.trimmingCharacters(in: .newlines) }
            .filter { !$0.isEmpty }
        lines.append(contentsOf: additional)
        lines.append("---")
        lines.append("")

        lines.append("{% include newMatchDetails %}")
        lines.append("")

        if !imagesAfterNewMatchDetails.isEmpty {
            for image in imagesAfterNewMatchDetails where !image.pathOrURL.isEmpty {
                lines.append(image.markdownLine)
            }
            lines.append("")
        }

        if !notesAfterNewMatchDetails.isEmpty {
            lines.append(notesAfterNewMatchDetails)
            lines.append("")
        }

        lines.append(contentsOf: inningsSection(
            heading: inningsHeading(firstInningsTeam, fallback: "{{page.homeTeam}}"),
            innings: homeInnings
        ))
        lines.append(contentsOf: inningsSection(
            heading: inningsHeading(secondInningsTeam, fallback: "{{page.awayTeam}}"),
            innings: awayInnings
        ))

        lines.append("## Win/Loss Ratio")
        lines.append("")
        lines.append("| Won | Lost | Drawn | Tied |")
        lines.append("|:---|:---|:---|---:|")
        lines.append("| \(cell(winLoss.won)) | \(cell(winLoss.lost)) | \(cell(winLoss.drawn)) | \(cell(winLoss.tied)) |")
        lines.append("")

        if !notesBeforeNextGame.isEmpty {
            lines.append(notesBeforeNextGame)
            lines.append("")
        }

        lines.append("{% include nextGame %}")

        if !imagesAfterNextGame.isEmpty {
            lines.append("")
            for image in imagesAfterNextGame where !image.pathOrURL.isEmpty {
                lines.append(image.markdownLine)
            }
        }

        return lines.joined(separator: "\n") + "\n"
    }

    private func locationValue() -> String {
        let trimmedLocation = locationName.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedMap = googleMapsURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmedLocation.isEmpty else {
            return ""
        }

        if !trimmedMap.isEmpty {
            return "[\(trimmedLocation)](\(trimmedMap))"
        }
        return trimmedLocation
    }

    private func inningsSection(heading: String, innings: Innings) -> [String] {
        var lines: [String] = []

        lines.append("## \(heading) Innings")
        lines.append("")
        lines.append("| Batsman | Dismissal | | Runs |")
        lines.append("|:---|:---|---|---:|")
        for row in innings.normalizedBattingRows() {
            lines.append("| **\(cell(row.batsman))** | \(cell(row.dismissalPrimary)) | \(cell(row.dismissalSecondary)) | \(cell(row.runs)) |")
        }
        lines.append("| **Extras** | | \(cell(innings.extrasBreakdown)) | **\(cell(innings.extrasRuns))** |")
        lines.append("| **Total** | | (\(cell(innings.totalOvers)) overs) | **\(cell(innings.totalSummary))** |")
        lines.append("")

        lines.append("## Fall of Wickets")
        lines.append("")
        lines.append("| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |")
        lines.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
        lines.append("| **Score** | \(innings.fallScores.map(cell).joined(separator: " | ")) |")
        lines.append("| **Batsman** | \(innings.fallBatters.map(cell).joined(separator: " | ")) |")
        lines.append("")

        lines.append("## Bowling")
        lines.append("")
        lines.append("| | O | M | R | W |")
        lines.append("|---|:---|:---|:---|:---|")
        for row in innings.bowlingRows {
            lines.append("| **\(cell(row.bowler))** | \(cell(row.overs)) | \(cell(row.maidens)) | \(cell(row.runs)) | \(cell(row.wickets)) |")
        }
        lines.append("")

        return lines
    }

    private func yamlValue(_ input: String) -> String {
        let singleLine = input.replacingOccurrences(of: "\n", with: " ")
        let escaped = singleLine.replacingOccurrences(of: "'", with: "''")
        return "'\(escaped)'"
    }

    private func cell(_ value: String) -> String {
        value.replacingOccurrences(of: "|", with: "\\|")
    }

    private func inningsHeading(_ value: String?, fallback: String) -> String {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? fallback : trimmed
    }
}
