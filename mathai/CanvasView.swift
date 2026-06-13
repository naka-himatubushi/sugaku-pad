// PencilKit の手書きキャンバスを SwiftUI に橋渡しする薄いラッパ。
import SwiftUI
import PencilKit

struct CanvasView: UIViewRepresentable {
    @Binding var canvas: PKCanvasView

    func makeUIView(context: Context) -> PKCanvasView {
        canvas.drawingPolicy = .anyInput   // 指でも Pencil でも描ける（実機検証しやすく）
        canvas.tool = PKInkingTool(.pen, color: .label, width: 4)
        canvas.backgroundColor = .systemBackground
        return canvas
    }

    func updateUIView(_ uiView: PKCanvasView, context: Context) {}
}
