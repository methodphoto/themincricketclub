import Foundation
import SwiftUI
import AppKit

@MainActor
final class MatchStore: ObservableObject {
    @Published var drafts: [MatchDraft] = []
    @Published var selectedDraftID: MatchDraft.ID?
    @Published var outputRootPath: String

    @Published var statusMessage: String = ""

    private let draftsURL: URL
    private let settingsURL: URL

    init() {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = appSupport.appendingPathComponent("ScorecardMacApp", isDirectory: true)

        self.draftsURL = appDir.appendingPathComponent("drafts.json")
        self.settingsURL = appDir.appendingPathComponent("settings.json")
        self.outputRootPath = Self.detectOutputRoot()

        do {
            try FileManager.default.createDirectory(at: appDir, withIntermediateDirectories: true)
        } catch {
            statusMessage = "Could not create app support directory: \(error.localizedDescription)"
        }

        load()
        if drafts.isEmpty {
            addDraft()
        }
    }

    private static func detectOutputRoot() -> String {
        let fm = FileManager.default
        var candidate = URL(fileURLWithPath: fm.currentDirectoryPath, isDirectory: true)

        for _ in 0..<5 {
            let configPath = candidate.appendingPathComponent("_config.yml").path
            if fm.fileExists(atPath: configPath) {
                return candidate.path
            }
            let next = candidate.deletingLastPathComponent()
            if next.path == candidate.path {
                break
            }
            candidate = next
        }

        return fm.currentDirectoryPath
    }

    func addDraft() {
        var draft = MatchDraft()
        if draft.parent.isEmpty {
            draft.parent = "\(draft.season) Fixtures"
        }
        draft.normalizeForEditing()
        drafts.append(draft)
        selectedDraftID = draft.id
        saveDrafts()
    }

    func deleteSelectedDraft() {
        guard let selectedDraftID else { return }
        drafts.removeAll { $0.id == selectedDraftID }
        self.selectedDraftID = drafts.first?.id
        saveDrafts()
    }

    func selectedDraftBinding() -> Binding<MatchDraft>? {
        guard let selectedDraftID,
              drafts.contains(where: { $0.id == selectedDraftID }) else {
            return nil
        }

        return Binding(
            get: {
                self.drafts.first(where: { $0.id == selectedDraftID })!
            },
            set: { updatedDraft in
                guard let index = self.drafts.firstIndex(where: { $0.id == selectedDraftID }) else { return }
                var normalizedDraft = updatedDraft
                normalizedDraft.normalizeForEditing()
                self.drafts[index] = normalizedDraft
                self.saveDrafts()
            }
        )
    }

    func exportSelectedDraft() {
        guard let selectedDraftID,
              let draft = drafts.first(where: { $0.id == selectedDraftID }) else {
            statusMessage = "No match selected."
            return
        }

        let season = draft.season.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !season.isEmpty else {
            statusMessage = "Season is required before exporting."
            return
        }

        let root = outputRootPath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !root.isEmpty else {
            statusMessage = "Output root path is empty."
            return
        }

        let seasonDir = URL(fileURLWithPath: root, isDirectory: true).appendingPathComponent(season, isDirectory: true)
        let fileURL = seasonDir.appendingPathComponent("\(draft.resolvedSlug).md")

        do {
            try FileManager.default.createDirectory(at: seasonDir, withIntermediateDirectories: true)
            try draft.markdown().write(to: fileURL, atomically: true, encoding: .utf8)
            saveSettings()
            statusMessage = "Saved \(fileURL.path)"
        } catch {
            statusMessage = "Export failed: \(error.localizedDescription)"
        }
    }

    func chooseOutputFolder() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "Choose Output Folder"

        if panel.runModal() == .OK, let url = panel.url {
            outputRootPath = url.path
            saveSettings()
        }
    }

    private func load() {
        loadDrafts()
        loadSettings()
    }

    private func loadDrafts() {
        guard let data = try? Data(contentsOf: draftsURL) else {
            return
        }

        do {
            let decoded = try JSONDecoder().decode([MatchDraft].self, from: data)
            drafts = decoded.map { draft in
                var normalizedDraft = draft
                normalizedDraft.normalizeForEditing()
                return normalizedDraft
            }
            selectedDraftID = drafts.first?.id
        } catch {
            statusMessage = "Could not load drafts: \(error.localizedDescription)"
        }
    }

    private func loadSettings() {
        struct Settings: Codable {
            var outputRootPath: String
        }

        guard let data = try? Data(contentsOf: settingsURL) else {
            return
        }

        if let settings = try? JSONDecoder().decode(Settings.self, from: data) {
            outputRootPath = settings.outputRootPath
        }
    }

    private func saveSettings() {
        struct Settings: Codable {
            var outputRootPath: String
        }

        do {
            let data = try JSONEncoder().encode(Settings(outputRootPath: outputRootPath))
            try data.write(to: settingsURL, options: .atomic)
        } catch {
            statusMessage = "Could not save settings: \(error.localizedDescription)"
        }
    }

    private func saveDrafts() {
        do {
            let data = try JSONEncoder().encode(drafts)
            try data.write(to: draftsURL, options: .atomic)
        } catch {
            statusMessage = "Could not save drafts: \(error.localizedDescription)"
        }
    }
}
