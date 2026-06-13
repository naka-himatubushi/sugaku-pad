// 本物の Solve バックエンド: 端末内の埋め込み Python(mathai+SymPy) を呼ぶ。
// PythonBridge.solveJSON が返す JSON を SolveResult に変換する。MockSolveService の差し替え。
// 注意: PythonBridge 呼び出しは重い（初回 Python 初期化）。呼び出し側はバックグラウンドで実行する。
import Foundation

struct PythonSolveService: SolveService {
    func solve(_ input: String) -> SolveResult {
        let json = PythonBridge.solveJSON(input)
        guard let data = json.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return .unsupported
        }
        let supported = obj["supported"] as? Bool ?? false
        guard supported else { return .unsupported }
        // mathai が返す steps_latex([{label, latex}, …]) を拾う(今まで捨てていた)。
        let rawSteps = obj["steps_latex"] as? [[String: String]] ?? []
        let stepsLatex = rawSteps.map { StepLatex(label: $0["label"] ?? "", latex: $0["latex"] ?? "") }
        return SolveResult(
            supported: true,
            kind: obj["kind"] as? String ?? "",
            steps: obj["steps"] as? [String] ?? [],
            answer: obj["answer"] as? [String] ?? [],
            answerLatex: obj["answer_latex"] as? [String] ?? [],
            stepsLatex: stepsLatex,
            verified: obj["verified"] as? Bool ?? false
        )
    }
}
