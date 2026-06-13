// PencilKit の手書きキャンバスを SwiftUI に橋渡しする薄いラッパ。
// Goodnotes 風のツールパレット（ペン/鉛筆/マーカー/消しゴム/投げ縄/色/太さ/定規）を出す。
import SwiftUI
import PencilKit

struct CanvasView: UIViewRepresentable {
    @Binding var canvas: PKCanvasView

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> PKCanvasView {
        canvas.drawingPolicy = .anyInput   // 指でも Pencil でも描ける（実機/シミュレータ両対応）
        canvas.tool = PKInkingTool(.pen, color: .label, width: 4)
        canvas.backgroundColor = .systemBackground
        canvas.alwaysBounceVertical = false
        return canvas
    }

    func updateUIView(_ uiView: PKCanvasView, context: Context) {
        // ツールパレットは view が window に乗ってから一度だけ表示する（first responder 必須）。
        guard uiView.window != nil, !context.coordinator.shown else { return }
        context.coordinator.shown = true
        let picker = context.coordinator.toolPicker
        picker.setVisible(true, forFirstResponder: uiView)
        picker.addObserver(uiView)
        uiView.becomeFirstResponder()
    }

    /// PKToolPicker を保持する（弱参照だと即解放されてパレットが消えるため）。
    final class Coordinator {
        let toolPicker = PKToolPicker()
        var shown = false
    }
}
