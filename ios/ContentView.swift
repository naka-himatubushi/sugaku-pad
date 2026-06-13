// アプリ本体の Solve フロー: 手書きキャンバス → 確認カード（編集可能な認識結果）→ Solve → ステップ表示。
// 認識(OCR)と埋め込み計算は後続スライス。当面 SolveService はモック、確認カードはテキスト編集で代用。
import SwiftUI
import PencilKit

struct ContentView: View {
    @State private var canvas = PKCanvasView()
    @State private var input = "2x + 3 = 7"
    @State private var result: SolveResult?
    private let service: SolveService = MockSolveService()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("手書き（認識は後続スライス）")
                        .font(.caption).foregroundStyle(.secondary)
                    CanvasView(canvas: $canvas)
                        .frame(height: 180)
                        .border(Color.secondary)

                    // 確認カード: 認識結果を見せ、計算前に編集・確定する（Goodnotes と同じ設計）
                    VStack(alignment: .leading, spacing: 8) {
                        Text("認識結果（編集して確認）")
                            .font(.caption).foregroundStyle(.secondary)
                        TextField("数式 または LaTeX", text: $input)
                            .textFieldStyle(.roundedBorder)
                            .font(.title3)
                        Button("Solve") { result = service.solve(input) }
                            .buttonStyle(.borderedProminent)
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
                    }
                }
            }
            .navigationDestination(for: SpikeRoute.self) { route in
                switch route {
                case .ocr: OcrSpikeView()
                case .compute: ComputeSpikeView()
                case .foundationModel: FoundationModelAvailabilityView()
                case .mlxBench: MlxOcrBenchView()
                }
            }
        }
    }
}

enum SpikeRoute: Hashable {
    case ocr, compute, foundationModel, mlxBench
}
