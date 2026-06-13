// 結果ボトムシート。下からせり出し、答えを見ながら背面キャンバスに書き足せる。
// 中身: ConfirmCard(認識 LaTeX を編集可 + ⟲再計算)と、既存 SolveResultView を
//       格上げ表示する SolveResultPanel(kind 日本語化 / verified 緑シール / answer 最大化 /
//       steps 折りたたみ / SymPy 記法の軽い整形)。
// SolveResult / PythonSolveService は無改変。表示の格上げのみ行う。
import SwiftUI

struct SolveSheet: View {
    let session: SolveSession
    /// 確認カードの「⟲再計算」で編集後 LaTeX を渡す(OCR をスキップして再求解)。
    let onResolve: (String) -> Void

    @State private var editedLatex: String = ""
    @State private var didInit = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    ConfirmCard(latex: $editedLatex) {
                        onResolve(editedLatex)
                    }
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

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("認識結果(編集して確認)")
                .font(.caption).foregroundStyle(.secondary)
            HStack(spacing: 10) {
                TextField("数式 または LaTeX", text: $latex)
                    .textFieldStyle(.roundedBorder)
                    .font(.title3)
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
        }
        .padding(16)
        .background(.background.opacity(0.6), in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(.quaternary))
    }
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
                    HStack(alignment: .firstTextBaseline, spacing: 10) {
                        Text(prettyAnswer)
                            .font(.title2.bold())
                            .textSelection(.enabled)
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

                // 手順(普段は畳んで答え優先。必要時に開く)
                if !result.steps.isEmpty {
                    DisclosureGroup(isExpanded: $showSteps) {
                        VStack(alignment: .leading, spacing: 10) {
                            ForEach(Array(result.steps.enumerated()), id: \.offset) { index, step in
                                HStack(alignment: .top, spacing: 8) {
                                    Text("\(index + 1).")
                                        .monospacedDigit().foregroundStyle(.secondary)
                                    Text(MathDisplay.pretty(step))
                                        .textSelection(.enabled)
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
