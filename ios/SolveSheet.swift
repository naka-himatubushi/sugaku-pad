// 結果ボトムシート。下からせり出し、答えを見ながら背面キャンバスに書き足せる。
// 中身: ConfirmCard(認識 LaTeX を編集可 + ⟲再計算)と、既存 SolveResultView を
//       格上げ表示する SolveResultPanel(kind 日本語化 / verified 緑シール / answer 最大化 /
//       steps 折りたたみ / SymPy 記法の軽い整形)。
// SolveResult / PythonSolveService は無改変。表示の格上げのみ行う。
import SwiftUI
import PencilKit

struct SolveSheet: View {
    let session: SolveSession
    /// 確認カードの「⟲再計算」で編集後 LaTeX を渡す(OCR をスキップして再求解)。
    let onResolve: (String) -> Void
    /// 「ノートに置く」: 結果を可動カードとしてノート上に配置する。
    let onPin: () -> Void
    /// 訂正キャンバスの手書きを OCR して LaTeX を返す(model.ocr 経由)。nil=失敗。
    let recognizeImage: (UIImage) async -> String?

    @State private var editedLatex: String = ""
    @State private var didInit = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    ConfirmCard(latex: $editedLatex,
                                onResolve: { onResolve(editedLatex) },
                                recognizeImage: recognizeImage)
                    if let result = session.result {
                        SolveResultPanel(result: result)
                    } else {
                        // 結果待ち or 手入力直後。再計算を促す。
                        Label("上の式を確認して「⟲ 再計算」を押してください",
                              systemImage: "arrow.triangle.2.circlepath")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(20)
            }
            .navigationTitle("答え")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if session.result?.supported == true {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button(action: onPin) {
                            Label("ノートに置く", systemImage: "pin")
                        }
                    }
                }
            }
        }
        .presentationDetents([.medium, .large])
        .presentationBackground(.thinMaterial)
        .presentationDragIndicator(.visible)
        .presentationBackgroundInteraction(.enabled(upThrough: .medium))
        .onAppear {
            if !didInit { editedLatex = session.latex; didInit = true }
        }
    }
}

// MARK: - 確認カード(編集可 + 再計算)

struct ConfirmCard: View {
    @Binding var latex: String
    let onResolve: () -> Void
    /// 訂正キャンバスの手書きを OCR して LaTeX を返す。
    let recognizeImage: (UIImage) async -> String?

    @State private var showPenPad = false
    @State private var penCanvas = PKCanvasView()
    @State private var recognizing = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("認識結果(確認して、必要なら直す)")
                .font(.caption).foregroundStyle(.secondary)
            // 読みやすい数式プレビュー(SwiftMath = KaTeX 相当)。生 LaTeX は下の欄で編集。
            if MathView.renderable(latex) {
                MathView(latex: latex, fontSize: 28)
                    .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                    .padding(.vertical, 6)
                    .padding(.horizontal, 4)
            }
            // 生 LaTeX 編集欄。iPad では Apple Pencil の Scribble でこの欄に直接手書き入力できる。
            HStack(spacing: 10) {
                TextField("数式 / LaTeX（ペンで書いても入力できます）", text: $latex)
                    .textFieldStyle(.roundedBorder)
                    .font(.title3)
                    .frame(minHeight: 40)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                Button {
                    onResolve()
                } label: {
                    Label("再計算", systemImage: "arrow.triangle.2.circlepath")
                }
                .buttonStyle(.borderedProminent)
                .disabled(latex.trimmingCharacters(in: .whitespaces).isEmpty)
            }
            // ペンで書き直す(訂正キャンバス → 端末内 OCR で読み直し → 上の式を差し替え)。
            Button {
                withAnimation { showPenPad.toggle() }
            } label: {
                Label(showPenPad ? "手書き訂正を閉じる" : "✎ ペンで書き直す",
                      systemImage: "pencil.and.scribble")
                    .font(.subheadline)
            }
            .buttonStyle(.bordered)
            if showPenPad { penPad }
        }
        .padding(16)
        .background(.background.opacity(0.6), in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(.quaternary))
    }

    private var penPad: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("ここに正しい式を手書き → 「読み取り」で上の式を置き換え")
                .font(.caption2).foregroundStyle(.secondary)
            CorrectionCanvas(canvas: $penCanvas)
                .frame(height: 140)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(.quaternary))
            HStack {
                Button { penCanvas.drawing = PKDrawing() } label: {
                    Label("消す", systemImage: "trash")
                }
                .buttonStyle(.bordered)
                Spacer()
                Button { recognizePad() } label: {
                    Label(recognizing ? "読み取り中…" : "読み取り", systemImage: "sparkles")
                }
                .buttonStyle(.borderedProminent)
                .disabled(recognizing)
            }
        }
    }

    private func recognizePad() {
        let bounds = penCanvas.drawing.bounds
        guard !bounds.isEmpty, bounds.width > 1, bounds.height > 1 else { return }
        let img = normalizedOcrImage(from: penCanvas.drawing, rect: bounds.insetBy(dx: -24, dy: -24))
        recognizing = true
        Task {
            if let r = await recognizeImage(img) {
                let cleaned = r.trimmingCharacters(in: .whitespacesAndNewlines)
                if !cleaned.isEmpty { latex = cleaned }
            }
            penCanvas.drawing = PKDrawing()
            recognizing = false
            withAnimation { showPenPad = false }
        }
    }
}

// MARK: - 確認カード内の訂正キャンバス(固定ペン・ツールパレット無し)

/// 確認カードに置く小さな手書き欄。全画面ノートの PKToolPicker と first responder を
/// 奪い合わないよう、パレットは出さず黒の固定ペンにする。
struct CorrectionCanvas: UIViewRepresentable {
    @Binding var canvas: PKCanvasView

    func makeUIView(context: Context) -> PKCanvasView {
        canvas.drawingPolicy = .anyInput
        canvas.tool = PKInkingTool(.pen, color: .black, width: 4)
        canvas.backgroundColor = .clear
        canvas.overrideUserInterfaceStyle = .light   // 白地に黒で描く
        return canvas
    }

    func updateUIView(_ uiView: PKCanvasView, context: Context) {}
}

// MARK: - 結果パネル(SolveResultView を格上げ)

struct SolveResultPanel: View {
    let result: SolveResult
    @State private var showSteps = false

    var body: some View {
        if !result.supported {
            VStack(alignment: .leading, spacing: 8) {
                Label("対応範囲外の式です", systemImage: "exclamationmark.triangle")
                    .foregroundStyle(.orange)
                    .font(.headline)
                Text("上の式を直して「⟲ 再計算」で試せます")
                    .font(.caption).foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
            .background(.background.opacity(0.5), in: RoundedRectangle(cornerRadius: 16))
        } else {
            VStack(alignment: .leading, spacing: 16) {
                // ヘッダ: 種別(日本語) + 検算シール
                HStack {
                    Text(MathDisplay.kindLabel(result.kind))
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.secondary)
                    Spacer()
                    if result.verified {
                        Label("検算済み", systemImage: "checkmark.seal.fill")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.green)
                    }
                }

                // 答え(視線の終着点として最大化)
                VStack(alignment: .leading, spacing: 4) {
                    Text("答え")
                        .font(.caption).foregroundStyle(.secondary)
                    HStack(alignment: .center, spacing: 10) {
                        // 答えを数式描画(SwiftMath)。LaTeX が無ければ整形テキストに fallback。
                        if !result.answerLatex.isEmpty {
                            MathView(latex: result.answerLatex.joined(separator: ",\\ "), fontSize: 30)
                                .frame(minHeight: 38, alignment: .leading)
                        } else {
                            Text(prettyAnswer)
                                .font(.title2.bold())
                                .textSelection(.enabled)
                        }
                        Button {
                            UIPasteboard.general.string = result.answer.joined(separator: ", ")
                        } label: { Image(systemName: "doc.on.doc") }
                        .buttonStyle(.borderless)
                        .controlSize(.small)
                    }
                    if result.verified {
                        Text("代入して成立を確認")
                            .font(.caption).foregroundStyle(.green)
                    }
                }

                // 手順・検算(普段は畳んで答え優先。必要時に開く)。数式は SwiftMath で描画。
                if !result.stepsLatex.isEmpty {
                    DisclosureGroup(isExpanded: $showSteps) {
                        VStack(alignment: .leading, spacing: 12) {
                            ForEach(Array(result.stepsLatex.enumerated()), id: \.element.id) { index, step in
                                VStack(alignment: .leading, spacing: 3) {
                                    Text("\(index + 1). \(step.label)")
                                        .font(.caption).foregroundStyle(.secondary)
                                    if MathView.renderable(step.latex) {
                                        ScrollView(.horizontal, showsIndicators: false) {
                                            MathView(latex: step.latex, fontSize: 20)
                                                .frame(minHeight: 28, alignment: .leading)
                                                .padding(.horizontal, 2)
                                        }
                                    }
                                }
                            }
                        }
                        .padding(.top, 8)
                    } label: {
                        Text("手順・検算を見る").font(.subheadline.weight(.medium))
                    }
                } else if !result.steps.isEmpty {
                    DisclosureGroup(isExpanded: $showSteps) {
                        VStack(alignment: .leading, spacing: 10) {
                            ForEach(Array(result.steps.enumerated()), id: \.offset) { index, step in
                                HStack(alignment: .top, spacing: 8) {
                                    Text("\(index + 1).")
                                        .monospacedDigit().foregroundStyle(.secondary)
                                    Text(MathDisplay.pretty(step)).textSelection(.enabled)
                                }
                            }
                        }
                        .padding(.top, 8)
                    } label: {
                        Text("手順を見る").font(.subheadline.weight(.medium))
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
            .background(.background.opacity(0.5), in: RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(.quaternary))
        }
    }

    private var prettyAnswer: String {
        result.answer.map(MathDisplay.pretty).joined(separator: ",  ")
    }
}
