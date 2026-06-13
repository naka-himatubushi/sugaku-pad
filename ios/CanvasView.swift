// PencilKit の手書きキャンバスを SwiftUI に橋渡しする薄いラッパ。
// ツール（ペン/消しゴム/色/太さ）は ContentView の自前ツールバーから canvas.tool を直接設定する。
import SwiftUI
import PencilKit

struct CanvasView: UIViewRepresentable {
    @Binding var canvas: PKCanvasView

    func makeUIView(context: Context) -> PKCanvasView {
        canvas.drawingPolicy = .anyInput   // 指でも Pencil でも描ける
        canvas.tool = PKInkingTool(.pen, color: .label, width: 4)
        canvas.backgroundColor = .secondarySystemBackground
        canvas.alwaysBounceVertical = false
        return canvas
    }

    func updateUIView(_ uiView: PKCanvasView, context: Context) {}
}
