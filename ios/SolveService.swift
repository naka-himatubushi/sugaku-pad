// Solve のバックエンド抽象。UI は SolveService 越しに計算する。
// 当面は MockSolveService（シミュレータでUI確認用）。Xcode 投入後に
// 埋め込み Python(Python-Apple-support)+mathai.solve_latex 実装へ差し替える。
import Foundation

/// 1 手順の数式表示用(ラベル + LaTeX)。SwiftMath で本物の数式に描画する。
struct StepLatex: Identifiable {
    let id = UUID()
    let label: String
    let latex: String
}

struct SolveResult {
    let supported: Bool
    let kind: String          // linear / quadratic / inequality / system / evaluate / ...
    let steps: [String]
    let answer: [String]
    var answerLatex: [String] = []   // 答えの LaTeX 形(SwiftMath で数式描画する)
    var stepsLatex: [StepLatex] = [] // 手順の LaTeX 形(教科書品質の数式描画用)
    var verified: Bool = false   // 検算（代入/サンプル点）で成立を確認したか

    static let unsupported = SolveResult(supported: false, kind: "unknown", steps: [], answer: [])
}

protocol SolveService {
    func solve(_ input: String) -> SolveResult
}

/// シミュレータで UI を確認するための仮実装。代表式だけ正しい手順を返す。
/// 本実装（埋め込み SymPy = mathai）に差し替える前提のスタブ。
struct MockSolveService: SolveService {
    func solve(_ input: String) -> SolveResult {
        let normalized = input.replacingOccurrences(of: " ", with: "")
        switch normalized {
        case "2x+3=7":
            return SolveResult(supported: true, kind: "linear",
                               steps: ["方程式: 2*x + 3 = 7",
                                       "x の項をまとめる: 2*x = 4",
                                       "両辺を 2 で割る → x = 2"],
                               answer: ["2"])
        case "x^2-5x+6=0", "x^{2}-5x+6=0":
            return SolveResult(supported: true, kind: "quadratic",
                               steps: ["方程式: x**2 - 5*x + 6 = 0",
                                       "因数分解: (x - 3)*(x - 2) = 0",
                                       "各因子を 0 にする → x = 2, 3"],
                               answer: ["2", "3"])
        default:
            return SolveResult(supported: true, kind: "demo",
                               steps: ["（モック）本実装では mathai が \(input) を解きます",
                                       "Xcode 投入後に埋め込み SymPy へ差し替え"],
                               answer: ["—"])
        }
    }
}
