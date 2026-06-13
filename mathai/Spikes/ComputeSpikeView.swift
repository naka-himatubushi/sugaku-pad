// Spike B: 端末内で数式を解く画面。
// 最終形は埋め込み Python(Python-Apple-support)+SymPy で mathai.solve_latex を呼ぶ。
// 計算ロジックの実体は Mac 側 mathai/ で実装・テスト済み（21 テスト PASS）。
// 埋め込みは docs/superpowers/plans/2026-06-13-on-device-feasibility-spikes.md の Task 4 参照。
import SwiftUI

struct ComputeSpikeView: View {
    @State private var input = "2x + 3 = 7"
    @State private var output = ""

    var body: some View {
        VStack(spacing: 12) {
            Text("Spike B: 端末内 計算").font(.headline)
            TextField("数式 または LaTeX", text: $input)
                .textFieldStyle(.roundedBorder)
            Button("解く") { output = solve(input) }
                .buttonStyle(.borderedProminent)
            Text(output)
                .font(.callout)
                .textSelection(.enabled)
        }
        .padding()
    }

    private func solve(_ expr: String) -> String {
        // TODO(Spike B): 埋め込み SymPy で mathai.solve_latex を呼ぶ。
        return "（埋め込みSymPy未搭載 — Mac の `python -m mathai \"\(expr)\"` では解ける）"
    }
}
