// Spike E: 埋め込み CPython + SymPy + mathai を iPad 内で動かす実証。
// 入力した式を PythonBridge.solveJSON で解き、初回ロード時間・答え・検算・生JSON を表示。
// 目的 = 「計算層もオンデバイスで動く」を実機（まずはシミュレータ）で裏取りする。
import SwiftUI

@MainActor
@Observable
final class PythonSolveSpike {
    var input = "2x+3=7"
    var answer = ""
    var kind = ""
    var verified = false
    var raw = ""
    var firstCallSeconds: Double?
    var running = false
    private var didFirstCall = false

    func solve() async {
        guard !running else { return }
        running = true
        defer { running = false }
        let latex = input
        let measureFirst = !didFirstCall
        let start = Date()
        // Python 初期化＋求解は重い処理。バックグラウンドで実行して UI を止めない。
        let json = await Task.detached(priority: .userInitiated) {
            PythonBridge.solveJSON(latex)
        }.value
        if measureFirst {
            firstCallSeconds = Date().timeIntervalSince(start)
            didFirstCall = true
        }
        raw = json
        if let data = json.data(using: .utf8),
           let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            kind = obj["kind"] as? String ?? ""
            verified = obj["verified"] as? Bool ?? false
            let ans = obj["answer"] as? [String] ?? []
            answer = ans.joined(separator: ", ")
            if answer.isEmpty, let err = obj["error"] as? String { answer = "エラー: \(err)" }
        } else {
            answer = "JSON 解析失敗"
        }
    }
}

struct PythonSolveSpikeView: View {
    @State private var spike = PythonSolveSpike()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Spike E: 埋め込み Python で求解")
                    .font(.title3).bold()
                Text("CPython + SymPy + mathai を端末内で実行。計算層のオンデバイス化を実証。")
                    .font(.caption).foregroundStyle(.secondary)

                TextField("数式 または LaTeX", text: $spike.input)
                    .textFieldStyle(.roundedBorder).font(.title3)
                Button(spike.running ? "計算中…" : "解く（埋め込み Python）") {
                    Task { await spike.solve() }
                }
                .buttonStyle(.borderedProminent)
                .disabled(spike.running)

                VStack(alignment: .leading, spacing: 6) {
                    row("答え", spike.answer)
                    row("種別", spike.kind)
                    row("検算", spike.verified ? "✓ 成立" : "—")
                    row("初回ロード", spike.firstCallSeconds.map { String(format: "%.1f s", $0) } ?? "—")
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))

                if !spike.raw.isEmpty {
                    Text("生 JSON").font(.caption).foregroundStyle(.secondary)
                    Text(spike.raw)
                        .font(.system(.footnote, design: .monospaced))
                        .textSelection(.enabled)
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                }
            }
            .padding()
        }
        .navigationTitle("Python 求解")
    }

    private func row(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            Text(value.isEmpty ? "—" : value).bold()
                .multilineTextAlignment(.trailing)
        }
        .font(.callout)
    }
}
