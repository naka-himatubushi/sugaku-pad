// アプリ本体の Solve フロー: 手書きキャンバス → 確認カード（編集可能な認識結果）→ Solve → ステップ表示。
// 認識(OCR)と埋め込み計算は後続スライス。当面 SolveService はモック、確認カードはテキスト編集で代用。
import SwiftUI
import PencilKit

struct ContentView: View {
    @State private var canvas = PKCanvasView()
    @State private var input = "2x + 3 = 7"
    @State private var result: SolveResult?
    @State private var solving = false
    private let service = PythonSolveService()   // 端末内 Python(mathai+SymPy) で解く

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("手書き（ペン・消しゴム・色・太さが使えます）")
                        .font(.caption).foregroundStyle(.secondary)
                    CanvasToolbar(canvas: canvas)
                    CanvasView(canvas: $canvas)
                        .frame(height: 260)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.secondary.opacity(0.4)))

                    // 確認カード: 認識結果を見せ、計算前に編集・確定する（Goodnotes と同じ設計）
                    VStack(alignment: .leading, spacing: 8) {
                        Text("認識結果（編集して確認）")
                            .font(.caption).foregroundStyle(.secondary)
                        TextField("数式 または LaTeX", text: $input)
                            .textFieldStyle(.roundedBorder)
                            .font(.title3)
                        Button(solving ? "計算中…" : "Solve") {
                            let expr = input
                            let svc = service
                            solving = true
                            Task {
                                // 初回は Python 初期化で重いのでバックグラウンド実行
                                let r = await Task.detached { svc.solve(expr) }.value
                                result = r
                                solving = false
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(solving)
                    }
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))

                    if let result {
                        SolveResultView(result: result)
                            .padding()
                            .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                    }
                }
                .padding()
            }
            .navigationTitle("MathAI")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu("検証") {
                        NavigationLink("Spike A: OCR", value: SpikeRoute.ocr)
                        NavigationLink("Spike B: 計算", value: SpikeRoute.compute)
                        NavigationLink("Spike C: FM", value: SpikeRoute.foundationModel)
                        NavigationLink("Spike D: MLX ベンチ", value: SpikeRoute.mlxBench)
                        NavigationLink("Spike E: Python 求解", value: SpikeRoute.pythonSolve)
                    }
                }
            }
            .navigationDestination(for: SpikeRoute.self) { route in
                switch route {
                case .ocr: OcrSpikeView()
                case .compute: ComputeSpikeView()
                case .foundationModel: FoundationModelAvailabilityView()
                case .mlxBench: MlxOcrBenchView()
                case .pythonSolve: PythonSolveSpikeView()
                }
            }
        }
    }
}

enum SpikeRoute: Hashable {
    case ocr, compute, foundationModel, mlxBench, pythonSolve
}
