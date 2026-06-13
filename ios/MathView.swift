// LaTeX 数式をネイティブに描画する SwiftUI ラッパ(SwiftMath / iosMath)。
// OCR が出す生 LaTeX(\frac{1}{2} 等)を「実際の数式の見た目」で表示し、読みやすくする。
// Web 版の KaTeX に相当。確認カードや答えの表示に使う。
import SwiftUI
import SwiftMath

struct MathView: UIViewRepresentable {
    let latex: String
    var fontSize: CGFloat = 20
    var textColor: UIColor = .label
    var alignment: MTTextAlignment = .left

    func makeUIView(context: Context) -> MTMathUILabel {
        let label = MTMathUILabel()
        label.labelMode = .display
        label.textAlignment = alignment
        label.fontSize = fontSize
        label.textColor = textColor
        label.setContentHuggingPriority(.required, for: .vertical)
        label.setContentCompressionResistancePriority(.required, for: .vertical)
        return label
    }

    func updateUIView(_ uiView: MTMathUILabel, context: Context) {
        uiView.fontSize = fontSize
        uiView.textColor = textColor
        uiView.textAlignment = alignment
        uiView.latex = MathView.clean(latex)
    }

    /// OCR が付けがちな数式デリミタを除去して SwiftMath が解釈できる素の LaTeX にする。
    static func clean(_ s: String) -> String {
        var t = s
        for d in ["\\(", "\\)", "\\[", "\\]", "$$", "$"] {
            t = t.replacingOccurrences(of: d, with: "")
        }
        return t.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// SwiftMath が解釈できそうかの簡易判定(空や明らかに壊れている時は呼び出し側でテキスト fallback)。
    static func renderable(_ s: String) -> Bool {
        !clean(s).isEmpty
    }
}
