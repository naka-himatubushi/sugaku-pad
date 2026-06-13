// トップ画面。手書きキャンバスと、3 つの技術検証スパイク画面への導線。
import SwiftUI
import PencilKit

struct ContentView: View {
    @State private var canvas = PKCanvasView()

    var body: some View {
        NavigationStack {
            VStack(spacing: 12) {
                Text("MathAI — Goodnotes簡易版（検証ビルド）")
                    .font(.headline)
                CanvasView(canvas: $canvas)
                    .border(Color.secondary)
                HStack(spacing: 12) {
                    NavigationLink("Spike A: OCR", value: SpikeRoute.ocr)
                    NavigationLink("Spike B: 計算", value: SpikeRoute.compute)
                    NavigationLink("Spike C: FM", value: SpikeRoute.foundationModel)
                }
                .buttonStyle(.bordered)
            }
            .padding()
            .navigationDestination(for: SpikeRoute.self) { route in
                switch route {
                case .ocr: OcrSpikeView()
                case .compute: ComputeSpikeView()
                case .foundationModel: FoundationModelAvailabilityView()
                }
            }
        }
    }
}

enum SpikeRoute: Hashable {
    case ocr, compute, foundationModel
}
