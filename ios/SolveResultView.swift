// Solve 結果（種別・ステップ・答え）を表示するビュー。
import SwiftUI

struct SolveResultView: View {
    let result: SolveResult

    var body: some View {
        if !result.supported {
            Label("対応範囲外の式です", systemImage: "exclamationmark.triangle")
                .foregroundStyle(.orange)
        } else {
            VStack(alignment: .leading, spacing: 10) {
                Text("種別: \(result.kind)")
                    .font(.subheadline).foregroundStyle(.secondary)
                ForEach(Array(result.steps.enumerated()), id: \.offset) { index, step in
                    HStack(alignment: .top, spacing: 8) {
                        Text("\(index + 1).").monospacedDigit().foregroundStyle(.secondary)
                        Text(step)
                    }
                }
                Divider()
                Text("答え: \(result.answer.joined(separator: ", "))")
                    .font(.headline)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
