import SwiftUI
import AppKit

@main
struct ScorecardMacApp: App {
    @StateObject private var store = MatchStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(store)
                .frame(minWidth: 1200, minHeight: 780)
        }
    }
}

struct ContentView: View {
    @EnvironmentObject private var store: MatchStore

    var body: some View {
        NavigationSplitView {
            VStack(alignment: .leading, spacing: 12) {
                List(selection: $store.selectedDraftID) {
                    ForEach(store.drafts) { draft in
                        Text(draft.displayName)
                            .tag(draft.id)
                    }
                }
            }
            .padding()
            .frame(minWidth: 320, idealWidth: 360, maxWidth: 420, maxHeight: .infinity, alignment: .topLeading)
        } detail: {
            if let draftBinding = store.selectedDraftBinding() {
                MatchEditor(draft: draftBinding)
            } else {
                Text("Select or create a match draft")
                    .foregroundStyle(.secondary)
            }
        }
        .navigationSplitViewColumnWidth(min: 320, ideal: 360, max: 420)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                HStack(spacing: 8) {
                    Button {
                        store.deleteSelectedDraft()
                    } label: {
                        Label("Delete", systemImage: "xmark")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.red)
                    .disabled(store.selectedDraftID == nil)

                    Spacer()
                        .frame(width: 14)

                    Button {
                        store.exportSelectedDraft()
                    } label: {
                        Label("Share", systemImage: "square.and.arrow.up")
                    }
                    .disabled(store.selectedDraftID == nil)

                    Button {
                        store.addDraft()
                    } label: {
                        Label("New Match", systemImage: "plus")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.blue)
            }
        }
    }
}
}

struct MatchEditor: View {
    @EnvironmentObject private var store: MatchStore
    @Binding var draft: MatchDraft

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                scorecardTextField("Output root", text: $store.outputRootPath)
                Button("Choose Folder") {
                    store.chooseOutputFolder()
                }
            }

            if !store.statusMessage.isEmpty {
                Text(store.statusMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            TabView {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        frontmatterSection
                        imageSection(title: "Images below {% include newMatchDetails %}", images: $draft.imagesAfterNewMatchDetails)
                        notesSection(title: "Text below {% include newMatchDetails %}", text: $draft.notesAfterNewMatchDetails)
                        inningsEditor(title: firstInningsEditorTitle, innings: $draft.homeInnings)
                        inningsEditor(title: secondInningsEditorTitle, innings: $draft.awayInnings)
                        winLossSection
                        notesSection(title: "Text before {% include nextGame %}", text: $draft.notesBeforeNextGame)
                        imageSection(title: "Images below {% include nextGame %}", images: $draft.imagesAfterNextGame)
                    }
                    .padding(.trailing, 10)
                }
                .tabItem { Text("Editor") }

                TextEditor(text: .constant(draft.markdown()))
                    .font(.system(.body, design: .monospaced))
                    .padding(8)
                    .tabItem { Text("Preview") }
            }
        }
        .padding()
        .onAppear {
            draft.normalizeForEditing()
        }
    }

    private var frontmatterSection: some View {
        GroupBox("Frontmatter") {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    labeledField("Season", text: $draft.season)
                    labeledField("Slug (optional)", text: $draft.slug)
                    labeledField("Date", text: $draft.date)
                }
                HStack {
                    labeledField("Layout", text: $draft.layout)
                    labeledField("Title", text: $draft.title)
                }
                HStack {
                    labeledField("Home Team", text: $draft.homeTeam)
                    labeledField("Away Team", text: $draft.awayTeam)
                }
                HStack {
                    labeledField("1st Innings Team (optional)", text: optionalStringBinding($draft.firstInningsTeam))
                    labeledField("2nd Innings Team (optional)", text: optionalStringBinding($draft.secondInningsTeam))
                }
                HStack {
                    Button("Home Bats First") {
                        setBattingOrder(homeBatsFirst: true)
                    }
                    Button("Away Bats First") {
                        setBattingOrder(homeBatsFirst: false)
                    }
                    Text("Use quick buttons or type any team label.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                HStack {
                    labeledField("Location", text: $draft.locationName)
                    labeledField("Google Maps URL", text: $draft.googleMapsURL)
                }
                HStack {
                    labeledField("Result", text: $draft.result)
                    labeledField("Next Game Path", text: $draft.nextGamePath)
                    labeledField("Parent", text: $draft.parent)
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("Report")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    TextEditor(text: $draft.report)
                        .frame(minHeight: 80)
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.secondary.opacity(0.3)))
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("Additional frontmatter (raw YAML lines)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    TextEditor(text: $draft.additionalFrontmatter)
                        .frame(minHeight: 70)
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.secondary.opacity(0.3)))
                }
            }
            .padding(8)
        }
    }

    private func inningsEditor(title: String, innings: Binding<Innings>) -> some View {
        GroupBox(title) {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Batting (11 slots)")
                        .font(.headline)

                    ForEach(0..<Innings.batterSlotCount, id: \.self) { idx in
                        HStack {
                            Text("\(idx + 1)")
                                .frame(width: 24, alignment: .leading)
                            scorecardTextField("Batsman", text: innings.battingRows[idx].batsman)
                            scorecardTextField("Dismissal", text: innings.battingRows[idx].dismissalPrimary)
                            scorecardTextField("Detail", text: innings.battingRows[idx].dismissalSecondary)
                            scorecardTextField("Runs", text: innings.battingRows[idx].runs)
                                .frame(width: 80)
                        }
                    }
                }

                HStack {
                    labeledField("Extras Breakdown", text: innings.extrasBreakdown)
                    labeledField("Extras Runs", text: innings.extrasRuns)
                    labeledField("Total Overs", text: innings.totalOvers)
                    labeledField("Total Summary", text: innings.totalSummary)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Fall of Wickets")
                        .font(.headline)
                    Text("Enter values for wickets 1 to 10")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    ForEach(0..<10, id: \.self) { idx in
                        HStack {
                            Text("\(idx + 1)")
                                .frame(width: 24, alignment: .leading)
                            scorecardTextField("Score", text: innings.fallScores[idx])
                            scorecardTextField("Batsman", text: innings.fallBatters[idx])
                        }
                    }
                }

                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Bowling")
                            .font(.headline)
                        Button("Add Bowler") {
                            innings.wrappedValue.bowlingRows.append(BowlingRow())
                        }
                    }

                    ForEach(innings.bowlingRows) { $row in
                        HStack {
                            scorecardTextField("Bowler", text: $row.bowler)
                            scorecardTextField("O", text: $row.overs)
                            scorecardTextField("M", text: $row.maidens)
                            scorecardTextField("R", text: $row.runs)
                            scorecardTextField("W", text: $row.wickets)
                            Button("Remove") {
                                if innings.wrappedValue.bowlingRows.count > Innings.minimumBowlerCount {
                                    innings.wrappedValue.bowlingRows.removeAll { $0.id == row.id }
                                }
                            }
                            .disabled(innings.wrappedValue.bowlingRows.count <= Innings.minimumBowlerCount)
                        }
                    }
                }
            }
            .padding(8)
        }
        .onAppear {
            innings.wrappedValue.normalizeForEditing()
        }
    }

    private var winLossSection: some View {
        GroupBox("Win/Loss Ratio") {
            HStack {
                labeledField("Won", text: $draft.winLoss.won)
                labeledField("Lost", text: $draft.winLoss.lost)
                labeledField("Drawn", text: $draft.winLoss.drawn)
                labeledField("Tied", text: $draft.winLoss.tied)
            }
            .padding(8)
        }
    }

    private func notesSection(title: String, text: Binding<String>) -> some View {
        GroupBox(title) {
            TextEditor(text: text)
                .frame(minHeight: 70)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.secondary.opacity(0.3)))
                .padding(8)
        }
    }

    private func imageSection(title: String, images: Binding<[ImageBlock]>) -> some View {
        GroupBox(title) {
            VStack(alignment: .leading, spacing: 8) {
                Button("Add Image") {
                    images.wrappedValue.append(ImageBlock())
                }

                ForEach(images) { $image in
                    HStack {
                        scorecardTextField("Alt text", text: $image.altText)
                        scorecardTextField("Path or URL", text: $image.pathOrURL)
                        Button("Remove") {
                            images.wrappedValue.removeAll { $0.id == image.id }
                        }
                    }
                }
            }
            .padding(8)
        }
    }

    private func labeledField(_ label: String, text: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
            scorecardTextField(label, text: text)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func scorecardTextField(_ placeholder: String, text: Binding<String>) -> some View {
        ScorecardTextField(placeholder: placeholder, text: text)
            .scorecardTextFieldStyle()
    }

    private func optionalStringBinding(_ value: Binding<String?>) -> Binding<String> {
        Binding(
            get: { value.wrappedValue ?? "" },
            set: { newValue in
                let trimmed = newValue.trimmingCharacters(in: .whitespacesAndNewlines)
                value.wrappedValue = trimmed.isEmpty ? nil : newValue
            }
        )
    }

    private func setBattingOrder(homeBatsFirst: Bool) {
        if homeBatsFirst {
            draft.firstInningsTeam = "{{page.homeTeam}}"
            draft.secondInningsTeam = "{{page.awayTeam}}"
        } else {
            draft.firstInningsTeam = "{{page.awayTeam}}"
            draft.secondInningsTeam = "{{page.homeTeam}}"
        }
    }

    private func inningsTeamDisplayText(_ value: String?, fallback: String) -> String {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? fallback : trimmed
    }

    private var firstInningsEditorTitle: String {
        let fallback = draft.homeTeam.isEmpty ? "{{page.homeTeam}}" : draft.homeTeam
        return "First Innings (\(inningsTeamDisplayText(draft.firstInningsTeam, fallback: fallback)))"
    }

    private var secondInningsEditorTitle: String {
        let fallback = draft.awayTeam.isEmpty ? "{{page.awayTeam}}" : draft.awayTeam
        return "Second Innings (\(inningsTeamDisplayText(draft.secondInningsTeam, fallback: fallback)))"
    }
}

private struct ScorecardTextFieldModifier: ViewModifier {
    private let fieldBackground = Color(red: 30.0 / 255.0, green: 30.0 / 255.0, blue: 30.0 / 255.0)

    func body(content: Content) -> some View {
        content
            .textFieldStyle(.plain)
            .padding(.horizontal, 8)
            .padding(.vertical, 8)
            .foregroundStyle(.white)
            .tint(.white)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(fieldBackground)
                    .allowsHitTesting(false)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.white.opacity(0.15), lineWidth: 1)
                    .allowsHitTesting(false)
            )
    }
}

private extension View {
    func scorecardTextFieldStyle() -> some View {
        modifier(ScorecardTextFieldModifier())
    }
}

private struct ScorecardTextField: NSViewRepresentable {
    let placeholder: String
    @Binding var text: String

    func makeCoordinator() -> Coordinator {
        Coordinator(text: $text)
    }

    func makeNSView(context: Context) -> NSTextField {
        let textField = NSTextField(frame: .zero)
        textField.delegate = context.coordinator
        textField.isEditable = true
        textField.isSelectable = true
        textField.isEnabled = true
        textField.isBordered = false
        textField.drawsBackground = false
        textField.focusRingType = .none
        textField.font = .systemFont(ofSize: NSFont.systemFontSize)
        textField.textColor = .white
        textField.lineBreakMode = .byTruncatingTail
        textField.usesSingleLineMode = true
        textField.cell?.wraps = false
        textField.stringValue = text
        textField.placeholderAttributedString = placeholderString
        return textField
    }

    func updateNSView(_ textField: NSTextField, context: Context) {
        if textField.stringValue != text {
            textField.stringValue = text
        }
        textField.placeholderAttributedString = placeholderString
    }

    private var placeholderString: NSAttributedString {
        NSAttributedString(
            string: placeholder,
            attributes: [.foregroundColor: NSColor.secondaryLabelColor]
        )
    }

    final class Coordinator: NSObject, NSTextFieldDelegate {
        @Binding private var text: String

        init(text: Binding<String>) {
            _text = text
        }

        func controlTextDidChange(_ notification: Notification) {
            guard let textField = notification.object as? NSTextField else { return }
            text = textField.stringValue
        }

        func control(_ control: NSControl, textView: NSTextView, doCommandBy commandSelector: Selector) -> Bool {
            if commandSelector == #selector(NSResponder.insertTab(_:)) {
                control.window?.selectNextKeyView(control)
                return true
            }
            if commandSelector == #selector(NSResponder.insertBacktab(_:)) {
                control.window?.selectPreviousKeyView(control)
                return true
            }
            return false
        }
    }
}
