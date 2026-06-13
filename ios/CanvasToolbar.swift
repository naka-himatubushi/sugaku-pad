// 手書きキャンバス用の自前ツールバー（Goodnotes 風）。
// PKToolPicker(浮遊パレット)は埋め込み小キャンバスで表示が不安定なため、
// 確実に出る SwiftUI ボタンで pen/marker/eraser・色・太さ・取り消し・全消去を提供する。
import SwiftUI
import PencilKit

struct CanvasToolbar: View {
    let canvas: PKCanvasView

    enum Tool { case pen, marker, eraser }
    enum Pen: String, CaseIterable, Identifiable {
        case ink, red, blue, green
        var id: String { rawValue }
        var ui: UIColor {
            switch self {
            case .ink: return .label
            case .red: return .systemRed
            case .blue: return .systemBlue
            case .green: return .systemGreen
            }
        }
    }

    @State private var tool: Tool = .pen
    @State private var pen: Pen = .ink
    @State private var width: CGFloat = 4

    private func apply() {
        switch tool {
        case .pen: canvas.tool = PKInkingTool(.pen, color: pen.ui, width: width)
        case .marker: canvas.tool = PKInkingTool(.marker, color: pen.ui, width: width * 3)
        case .eraser: canvas.tool = PKEraserTool(.bitmap)
        }
    }

    var body: some View {
        HStack(spacing: 14) {
            toolButton(.pen, "pencil.tip")
            toolButton(.marker, "highlighter")
            toolButton(.eraser, "eraser")

            Divider().frame(height: 22)

            ForEach(Pen.allCases) { p in
                Button {
                    pen = p; if tool == .eraser { tool = .pen }; apply()
                } label: {
                    Circle().fill(Color(p.ui))
                        .frame(width: 22, height: 22)
                        .overlay(Circle().stroke(.primary, lineWidth: pen == p && tool != .eraser ? 2.5 : 0))
                }
                .buttonStyle(.plain)
            }

            Divider().frame(height: 22)

            Menu {
                Button("細") { width = 2; apply() }
                Button("中") { width = 4; apply() }
                Button("太") { width = 8; apply() }
            } label: {
                Image(systemName: "lineweight")
            }

            Spacer()

            Button { canvas.undoManager?.undo() } label: { Image(systemName: "arrow.uturn.backward") }
            Button(role: .destructive) { canvas.drawing = PKDrawing() } label: { Image(systemName: "trash") }
        }
        .font(.title3)
        .padding(.horizontal, 12).padding(.vertical, 8)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    private func toolButton(_ t: Tool, _ icon: String) -> some View {
        Button {
            tool = t; apply()
        } label: {
            Image(systemName: icon)
                .frame(width: 34, height: 30)
                .background(tool == t ? Color.accentColor.opacity(0.22) : .clear,
                            in: RoundedRectangle(cornerRadius: 8))
                .foregroundStyle(tool == t ? Color.accentColor : .primary)
        }
        .buttonStyle(.plain)
    }
}
