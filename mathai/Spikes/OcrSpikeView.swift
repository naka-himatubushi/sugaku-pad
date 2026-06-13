// Spike A: 手書きを端末内 OCR で LaTeX 化する画面。
// 現状は OCR モデル未搭載のプレースホルダ。pix2tex の CoreML/MLX 化は
// docs/superpowers/plans/2026-06-13-on-device-feasibility-spikes.md の Task 3 参照。
import SwiftUI
import PencilKit

struct OcrSpikeView: View {
    @State private var canvas = PKCanvasView()
    @State private var latex = "（数式を手書きして「認識」）"

    var body: some View {
        VStack(spacing: 12) {
            Text("Spike A: 端末内 OCR").font(.headline)
            CanvasView(canvas: $canvas)
                .border(Color.secondary)
            Button("認識") { latex = recognize(rasterize(canvas)) }
                .buttonStyle(.borderedProminent)
            Text("LaTeX: \(latex)")
                .font(.callout)
                .textSelection(.enabled)
        }
        .padding()
    }

    private func rasterize(_ canvas: PKCanvasView) -> UIImage {
        let bounds = canvas.drawing.bounds.isEmpty ? canvas.bounds : canvas.drawing.bounds
        return canvas.drawing.image(from: bounds, scale: 2.0)
    }

    private func recognize(_ image: UIImage) -> String {
        // TODO(Spike A): 端末内 LaTeX-OCR モデル（pix2tex→CoreML/MLX）を呼ぶ。
        return "（OCRモデル未搭載）"
    }
}
