// 新メイン画面「手書き数学ノート」の状態とフロー統括。
// 役割: 投げ縄選択(lassoRect) / 処理フェーズ(phase) / 結果セッション(session) /
//       ペン設定(inkColor, allowsFinger) を単一の真実として保持し、
//       認識(MLX OCR) → 確認 → 求解(埋め込み Python) のオーケストレーションを行う。
// 既存の頭脳(PythonSolveService.solve / SolveResult)は無改変で利用する。
// 重い処理(OCR / Python 初期化)は async/await + Task.detached でバックグラウンド化し UI を止めない。
import SwiftUI
import PencilKit
import OSLog

// 診断用ログ。手書き画像の保存先と OCR/求解の結果を os_log に出し、Mac から idevicesyslog で拾う。
private let noteLog = Logger(subsystem: "com.nakazawa.mathai", category: "note")

/// 結果ボトムシートを driving する Identifiable セッション。
/// 認識した LaTeX と求解結果(まだ計算中なら nil)を 1 組で持つ。
struct SolveSession: Identifiable {
    let id = UUID()
    var latex: String
    var result: SolveResult?
}

@MainActor
@Observable
final class MathNoteModel {
    /// 画面全体のフェーズ。処理中オーバーレイの出し分けに使う。
    enum Phase: Equatable { case idle, recognizing, solving }

    // MARK: - 表示・処理状態
    var phase: Phase = .idle
    /// 投げ縄で囲んだ外接矩形(SwiftUI ビュー座標)。nil なら全描画が対象。
    var lassoRect: CGRect?
    /// 投げ縄モード ON/OFF。ON の間はキャンバスへの描画を止めて囲み取りに使う。
    var lassoMode: Bool = false
    /// 結果ボトムシートを出す driving セッション。
    var session: SolveSession?
    /// 認識/求解に失敗したときの簡易メッセージ(トースト等で使う)。
    var errorText: String?

    // MARK: - ペン設定 / 用紙
    /// 既定は指も Apple Pencil も描ける(.anyInput)。トグル ON で Pencil のみ(手のひら誤接触防止)。
    var pencilOnly: Bool = false
    /// ノートの用紙スタイル(白紙 / 方眼)。
    var paper: Paper = .plain
    enum Paper: String, CaseIterable, Identifiable {
        case plain, grid
        var id: String { rawValue }
        var label: String { self == .plain ? "白紙" : "方眼" }
    }

    // MARK: - ノートに置いた結果カード(ドラッグで移動できる)
    struct PlacedResult: Identifiable {
        let id = UUID()
        var latex: String
        var result: SolveResult
        var position: CGPoint
    }
    var placedResults: [PlacedResult] = []
    func placeCard(latex: String, result: SolveResult, at point: CGPoint) {
        placedResults.append(PlacedResult(latex: latex, result: result, position: point))
    }
    func removeCard(_ id: UUID) {
        placedResults.removeAll { $0.id == id }
    }

    // MARK: - 頭脳(いずれも既存・無改変)
    let ocr = MathOcrService()
    private let solver: SolveService = PythonSolveService()

    var isBusy: Bool { phase != .idle }

    // MARK: - フロー

    /// 認識ボタン/投げ縄ポップオーバーの「✨認識して解く」から呼ぶ本流。
    /// 画像 → MLX OCR → LaTeX → 求解 までを一気通貫で走らせる。
    func recognizeAndSolve(image: UIImage) async {
        errorText = nil
        phase = .recognizing
        do {
            let latex = try await ocr.recognize(image)
            let cleaned = latex.trimmingCharacters(in: .whitespacesAndNewlines)
            noteLog.notice("NOTE-OCR latex=\(cleaned, privacy: .public)")
            guard !cleaned.isEmpty else {
                // 認識空: 確認カードに空で出し、人手入力に逃がす(行き止まりを作らない)。
                session = SolveSession(latex: "", result: nil)
                phase = .idle
                return
            }
            await resolve(latex: cleaned)
        } catch {
            errorText = "認識に失敗しました: \(error.localizedDescription)"
            // 失敗しても確認カードを開いて手入力で続行できるようにする。
            session = SolveSession(latex: "", result: nil)
            phase = .idle
        }
    }

    /// LaTeX から求解だけ行う。確認カードの「⟲再計算」もここを叩く(OCR をスキップして高速救済)。
    func resolve(latex: String) async {
        let expr = latex.trimmingCharacters(in: .whitespacesAndNewlines)
        phase = .solving
        // 初回 Python 初期化が重いのでバックグラウンドへ退避(ContentView 既存作法踏襲)。
        let solverRef = solver
        let r = await Task.detached(priority: .userInitiated) { solverRef.solve(expr) }.value
        noteLog.notice("NOTE-SOLVE in=\(expr, privacy: .public) supported=\(r.supported) kind=\(r.kind, privacy: .public) answer=\(r.answer.joined(separator: "|"), privacy: .public) verified=\(r.verified)")
        session = SolveSession(latex: expr, result: r)
        phase = .idle
    }

    /// 投げ縄選択を解除する(シートを閉じた/全消去した時など)。
    func clearSelection() {
        lassoRect = nil
    }
}

// MARK: - 表示用ヘルパ(新規依存ゼロ・純関数)

enum MathDisplay {
    /// SolveResult.kind を日本語ラベルに。未知の kind はそのまま返す。
    static func kindLabel(_ kind: String) -> String {
        switch kind {
        case "linear":     return "1次方程式"
        case "quadratic":  return "2次方程式"
        case "inequality": return "不等式"
        case "system":     return "連立方程式"
        case "evaluate":   return "式の計算"
        case "demo":       return "デモ"
        default:           return kind
        }
    }

    /// SymPy 由来の素の記法(x**2, 2*x, sqrt())を、iosMath 無しでも読みやすい
    /// プレーン表記へ軽く整形する。表示専用で、求解には元の文字列を使う。
    static func pretty(_ s: String) -> String {
        var t = s
        // 累乗 ** を上付き風(² ³ …)に。1〜2桁の指数を Unicode 上付きへ。
        t = replacePowers(in: t)
        // 乗算 * は見やすさのため中点に(2*x → 2·x)。
        t = t.replacingOccurrences(of: "*", with: "·")
        // sqrt(...) → √(...)
        t = t.replacingOccurrences(of: "sqrt(", with: "√(")
        return t
    }

    private static let superscripts: [Character: Character] = [
        "0": "\u{2070}", "1": "\u{00B9}", "2": "\u{00B2}", "3": "\u{00B3}",
        "4": "\u{2074}", "5": "\u{2075}", "6": "\u{2076}", "7": "\u{2077}",
        "8": "\u{2078}", "9": "\u{2079}"
    ]

    /// `base**exp` の exp 部分(連続する数字)を Unicode 上付きへ。`**` は除去。
    private static func replacePowers(in s: String) -> String {
        var result = ""
        let chars = Array(s)
        var i = 0
        while i < chars.count {
            if chars[i] == "*", i + 1 < chars.count, chars[i + 1] == "*" {
                i += 2
                var exp = ""
                while i < chars.count, chars[i].isNumber {
                    exp.append(chars[i]); i += 1
                }
                if exp.isEmpty {
                    // ** の後が数字でない(例: x**(n))ときは ^ にフォールバック。
                    result.append("^")
                } else {
                    for c in exp { result.append(superscripts[c] ?? c) }
                }
            } else {
                result.append(chars[i]); i += 1
            }
        }
        return result
    }
}
