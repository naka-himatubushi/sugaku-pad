// 新メイン画面: 洗練された全画面手書き数学ノート(Goodnotes 流)。
// 構成(ZStack で重ねる浮遊レイヤ方式):
//   1) NoteCanvas      … 全画面 PKCanvasView + Apple 純正 PKToolPicker(正しく first responder にして表示)
//   2) FloatingActionBar … 上部の浮遊バー(認識 / 投げ縄 / 取消 / 全消去 / 設定 / 検証)
//   3) SelectionPopover … 投げ縄で囲んだ直上に出る小アクション(認識して解く / LaTeXに / ✕)
//   4) ProcessingOverlay … 認識/求解中の薄い HUD(初回はモデル準備中の期待値調整)
//   .sheet(item:) … 結果は下からせり出すボトムシート(背面キャンバスに書き足し可)
// 既存の頭脳(PythonSolveService / SolveResult / SolveResultView)は無改変で利用。
import SwiftUI
import PencilKit

struct MathNoteView: View {
    @State private var model = MathNoteModel()
    @State private var canvas = PKCanvasView()
    /// 投げ縄ドラッグ中の始点・現在点(SwiftUI ビュー座標)。
    @State private var lassoStart: CGPoint?
    @State private var lassoCurrent: CGPoint?

    var body: some View {
        NavigationStack {
            // GeometryReader で画面サイズを取り、ポップオーバー位置の clamp に使う。
            GeometryReader { geo in
                ZStack {
                    // 0) 用紙(最背面): 白紙 / 方眼
                    PaperBackground(paper: model.paper)
                        .ignoresSafeArea()

                    // 1) 全画面キャンバス(用紙の上。背景は透明にして用紙を透かす)
                    NoteCanvas(canvas: $canvas, model: model)
                        .ignoresSafeArea()

                    // 投げ縄モード中のジェスチャ捕捉レイヤ + 点線ループ描画。
                    // canvas は殺さず、このレイヤだけが allowsHitTesting でヒットを取る。
                    if model.lassoMode {
                        lassoLayer
                    }

                    // 選択中の外接矩形ハイライト(どの式を解くのか視覚的に結ぶ)。
                    // ヒットは取らない(下のキャンバス/上のポップオーバーに委ねる)。
                    if let rect = model.lassoRect {
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color.accentColor.opacity(0.7),
                                    style: StrokeStyle(lineWidth: 2, dash: [6, 4]))
                            .background(Color.accentColor.opacity(0.06))
                            .frame(width: rect.width, height: rect.height)
                            .position(x: rect.midX, y: rect.midY)
                            .allowsHitTesting(false)
                    }

                    // 3) 投げ縄直上の選択ポップオーバー。
                    //    上部バーや画面端と重ならないよう座標を clamp/フォールバックする。
                    //    (FloatingActionBar より下層に置き、バーのボタンを邪魔しない)
                    if let rect = model.lassoRect, !model.isBusy {
                        SelectionPopover(
                            onRecognize: { recognize(rect: rect) },
                            onEditLatex: { openEditor() },
                            onCancel: { model.clearSelection() }
                        )
                        .position(popoverPosition(for: rect, in: geo.size))
                    }

                    // 置かれた結果カード(ドラッグで移動・タップで詳細・✕で削除)
                    ForEach($model.placedResults) { $card in
                        ResultCard(
                            card: card,
                            onTap: { model.session = SolveSession(latex: card.latex, result: card.result) },
                            onClose: { model.removeCard(card.id) }
                        )
                        .position(card.position)
                        .gesture(
                            DragGesture()
                                .onChanged { v in card.position = v.location }
                        )
                    }

                    // 2) 上部浮遊アクションバー(投げ縄/ポップオーバー/カードより上層 = 必ず押せる)
                    VStack {
                        FloatingActionBar(model: model, canvas: canvas, onRecognizeAll: recognizeAll)
                            .padding(.horizontal, 16)
                            .padding(.top, 8)
                        Spacer()
                    }

                    // 4) 処理中オーバーレイ(最前面)
                    if model.isBusy {
                        ProcessingOverlay(phase: model.phase,
                                          isFirstLoad: !model.ocr.isLoaded,
                                          loadProgress: model.ocr.loadProgress)
                    }
                }
            }
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: SpikeRoute.self) { route in
                switch route {
                case .ocr: OcrSpikeView()
                case .compute: ComputeSpikeView()
                case .foundationModel: FoundationModelAvailabilityView()
                case .mlxBench: MlxOcrBenchView()
                case .pythonSolve: PythonSolveSpikeView()
                }
            }
            .sheet(item: $model.session, onDismiss: { model.clearSelection() }) { session in
                SolveSheet(
                    session: session,
                    onResolve: { editedLatex in Task { await model.resolve(latex: editedLatex) } },
                    onPin: {
                        if let r = session.result {
                            // 投げ縄位置の少し下に置く。無ければ既定位置。あとはドラッグで移動。
                            let p = model.lassoRect.map { CGPoint(x: $0.midX, y: $0.maxY + 60) }
                                ?? CGPoint(x: 200, y: 260)
                            model.placeCard(latex: session.latex, result: r, at: p)
                            model.session = nil
                        }
                    }
                )
            }
            // 極小選択ガード等の errorText を黙殺せず簡易アラートで surface する。
            .alert("お知らせ", isPresented: errorAlertBinding) {
                Button("OK", role: .cancel) { model.errorText = nil }
            } message: {
                Text(model.errorText ?? "")
            }
        }
    }

    /// model.errorText の有無を Bool バインディングに変換(.alert(isPresented:) 用)。
    private var errorAlertBinding: Binding<Bool> {
        Binding(
            get: { model.errorText != nil },
            set: { if !$0 { model.errorText = nil } }
        )
    }

    /// 選択ポップオーバーの表示位置を解決する。
    /// 基本は選択矩形の上(rect.minY - 36)。上部バーと重なるなら下(rect.maxY + 36)へフォールバックし、
    /// 最後に画面端からはみ出さないよう x/y を clamp する。
    private func popoverPosition(for rect: CGRect, in size: CGSize) -> CGPoint {
        let topSafe: CGFloat = 96       // 上部バー領域。これより上には出さない。
        let margin: CGFloat = 40        // 画面端マージン。
        let above = rect.minY - 36
        // 上に置くと上部バーへ食い込むなら矩形の下側へ。
        var y = above < topSafe ? rect.maxY + 36 : above
        y = min(max(y, topSafe), size.height - margin)
        let x = min(max(rect.midX, margin), size.width - margin)
        return CGPoint(x: x, y: y)
    }

    // MARK: - 投げ縄レイヤ

    /// 投げ縄のジェスチャ捕捉レイヤ。canvas を殺さず、このレイヤが最前面でヒットを取る。
    /// contentShape(Rectangle()) で透明全域をタップ可能にし、ドラッグで矩形を確定する。
    private var lassoLayer: some View {
        ZStack {
            Color.clear.contentShape(Rectangle())
            if let s = lassoStart, let c = lassoCurrent {
                let r = CGRect(x: min(s.x, c.x), y: min(s.y, c.y),
                               width: abs(c.x - s.x), height: abs(c.y - s.y))
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.accentColor,
                            style: StrokeStyle(lineWidth: 2, dash: [6, 4]))
                    .background(Color.accentColor.opacity(0.06))
                    .frame(width: r.width, height: r.height)
                    .position(x: r.midX, y: r.midY)
            }
        }
        .gesture(
            DragGesture(minimumDistance: 4)
                .onChanged { v in
                    if lassoStart == nil { lassoStart = v.startLocation }
                    lassoCurrent = v.location
                }
                .onEnded { v in
                    let s = lassoStart ?? v.startLocation
                    let e = v.location
                    let r = CGRect(x: min(s.x, e.x), y: min(s.y, e.y),
                                   width: abs(e.x - s.x), height: abs(e.y - s.y))
                    lassoStart = nil; lassoCurrent = nil
                    if r.width > Self.minLassoSide && r.height > Self.minLassoSide {
                        model.lassoRect = r
                        model.lassoMode = false   // 囲み終えたら描画モードへ戻す
                    }
                }
        )
    }

    /// 投げ縄として有効と見なす最小辺長(ビュー座標 pt)。これ未満は誤タップ扱いで無視。
    private static let minLassoSide: CGFloat = 24

    // MARK: - アクション

    /// 投げ縄ルート: SwiftUI ビュー座標 rect を canvas のローカル座標へ写像してラスタライズ。
    private func recognize(rect: CGRect) {
        // 第一カットはズーム/スクロールを封じている(NoteCanvas.alwaysBounceVertical=false)ため、
        // ビュー座標 = canvas のローカル座標 = drawing 座標 とみなせる。
        // 極小選択ガード: そもそも選択が小さすぎるなら OCR せず弾く(空画像 = 認識失敗の元)。
        guard rect.width >= Self.minLassoSide, rect.height >= Self.minLassoSide else {
            model.errorText = "選択範囲が小さすぎます。もう少し大きく囲んでください"
            return
        }
        // drawing.bounds と交差させて安全側に。交差が無ければ描画なしとして弾く。
        let drawingBounds = canvas.drawing.bounds
        let intersection = rect.intersection(drawingBounds)
        let target = intersection.isNull || intersection.isEmpty ? rect : intersection
        // OCR 用に黒字・白地へ正規化(ペン色が薄い/白でも確実に認識させる)。
        let image = ocrImage(rect: target)
        guard imageHasContent(image) else {
            model.errorText = "囲んだ範囲に手書きが見つかりませんでした"
            return
        }
        Task { await model.recognizeAndSolve(image: image) }
    }

    /// 認識ボタンルート(保険): 全描画を対象に認識して解く。
    private func recognizeAll() {
        model.clearSelection()
        let bounds = canvas.drawing.bounds
        // 何も描かれていなければ早期 return(空画像で OCR を走らせない)。
        guard !bounds.isEmpty, bounds.width > 1, bounds.height > 1 else {
            model.errorText = "まだ何も書かれていません"
            return
        }
        let rect = bounds.insetBy(dx: -24, dy: -24)
        let image = ocrImage(rect: rect)
        guard imageHasContent(image) else {
            model.errorText = "手書きが見つかりませんでした"
            return
        }
        Task { await model.recognizeAndSolve(image: image) }
    }

    /// 画像が空(サイズゼロ)でないかの最小チェック。極小/空画像を OCR 前に弾く。
    private func imageHasContent(_ image: UIImage) -> Bool {
        image.size.width >= 1 && image.size.height >= 1
    }

    /// OCR 用画像を作る。全ストロークを黒に塗り替え、白い背景に合成する。
    /// ペン色が白/薄い色でも「黒字・白地」になり、OCR が確実に読める(表示色とは独立)。
    /// OCR 用画像を作る。手書きを「黒字・白地」に正規化して認識精度を担保する。
    /// 2段構え: ①全ストロークを黒に塗り替え(ペンが何色でも黒で渡す)
    ///          ②.light トレイトで描画(PencilKit がダーク文脈で黒インクを白へ自動反転する罠を回避)
    ///          ③白背景に合成(透明を無くし黒字白地に)。
    private func ocrImage(rect: CGRect) -> UIImage {
        let blackStrokes = canvas.drawing.strokes.map { s -> PKStroke in
            var ns = s
            ns.ink = PKInk(s.ink.inkType, color: .black)
            return ns
        }
        var strokeImg = UIImage()
        UITraitCollection(userInterfaceStyle: .light).performAsCurrent {
            strokeImg = PKDrawing(strokes: blackStrokes).image(from: rect, scale: 3.0)
        }
        let renderer = UIGraphicsImageRenderer(size: strokeImg.size)
        return renderer.image { ctx in
            UIColor.white.setFill()
            ctx.fill(CGRect(origin: .zero, size: strokeImg.size))
            strokeImg.draw(at: .zero)
        }
    }

    /// 「✎LaTeXに」= OCR を介さず空の確認カードを開いて手入力させる。
    private func openEditor() {
        model.session = SolveSession(latex: "", result: nil)
    }
}

// MARK: - 全画面キャンバス + 純正 PKToolPicker

/// 全画面 PKCanvasView を SwiftUI に橋渡しし、Apple 純正 PKToolPicker を表示する。
/// 重要: 全画面キャンバスにして first responder にすることで純正パレットが正しく出る
///       (小さい埋め込みでは出ない)。picker は Coordinator に強参照で保持する。
/// 古典バグ回避: window 未所属のまま becomeFirstResponder/setVisible してもパレットは出ない。
///       window 着地後(updateUIView で uiView.window != nil)に一度だけ確立する。
struct NoteCanvas: UIViewRepresentable {
    @Binding var canvas: PKCanvasView
    let model: MathNoteModel

    func makeUIView(context: Context) -> PKCanvasView {
        canvas.drawingPolicy = model.pencilOnly ? .pencilOnly : .anyInput
        canvas.tool = PKInkingTool(.pen, color: .black, width: 4)   // 白い用紙に映える黒
        canvas.backgroundColor = .clear   // 背面の PaperBackground(白/方眼)を透かす
        // 用紙は常に白なので、ダークモードでも黒インク既定＋白地向けの色パレットにする。
        canvas.overrideUserInterfaceStyle = .light
        // 第一カット: ズーム/スクロールは封じる(投げ縄座標 = drawing 座標を保つため)。
        canvas.alwaysBounceVertical = false
        canvas.alwaysBounceHorizontal = false
        canvas.isScrollEnabled = false
        canvas.minimumZoomScale = 1
        canvas.maximumZoomScale = 1
        canvas.bouncesZoom = false
        canvas.delegate = context.coordinator
        // picker は強参照で保持しないと解放されて消える。実際の表示確立は updateUIView で行う。
        let picker = PKToolPicker()
        picker.colorUserInterfaceStyle = .light   // 白い用紙に合わせ、黒を既定にし黒を選べるように
        context.coordinator.picker = picker
        return canvas
    }

    func updateUIView(_ uiView: PKCanvasView, context: Context) {
        // 設定トグル(指入力)を反映。
        let desired: PKCanvasViewDrawingPolicy = model.pencilOnly ? .pencilOnly : .anyInput
        if uiView.drawingPolicy != desired { uiView.drawingPolicy = desired }

        guard let picker = context.coordinator.picker else { return }

        // --- パレットの初回確立: window に着地し、まだ確立していない時だけ一度だけ ---
        // window 未所属のまま becomeFirstResponder/setVisible を呼ぶと純正パレットが出ない。
        if uiView.window != nil && !context.coordinator.didEstablishPicker {
            context.coordinator.didEstablishPicker = true
            picker.setVisible(true, forFirstResponder: uiView)
            picker.addObserver(uiView)
            uiView.becomeFirstResponder()
            // 既定ペンを黒に固定(白い用紙で見えるように。パレット確立後に上書き)。
            uiView.tool = PKInkingTool(.pen, color: .black, width: 4)
        }

        // 確立済みなら、投げ縄モードに応じてパレット表示を出し分ける。
        // 投げ縄モード中はパレットを隠してジェスチャに集中、描画モードでは再表示。
        // canvas 自体は殺さない(first responder を失わない)。ヒットは上層 lassoLayer が取る。
        if context.coordinator.didEstablishPicker {
            picker.setVisible(!model.lassoMode, forFirstResponder: uiView)
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator: NSObject, PKCanvasViewDelegate {
        /// 解放されるとパレットが消えるので強参照で保持する。
        var picker: PKToolPicker?
        /// パレットの first responder 確立を一度だけ行うためのフラグ。
        var didEstablishPicker = false
    }
}

// MARK: - 上部浮遊アクションバー

struct FloatingActionBar: View {
    @Bindable var model: MathNoteModel
    let canvas: PKCanvasView
    let onRecognizeAll: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Text("MathAI")
                .font(.headline)
                .padding(.trailing, 4)

            Divider().frame(height: 22)

            // 認識して解く(全描画) — 保険ルート
            Button {
                onRecognizeAll()
            } label: {
                Label("認識して解く", systemImage: "sparkles")
            }
            .disabled(model.isBusy)

            // 投げ縄トグル(主役ルート)
            Button {
                model.lassoMode.toggle()
                if model.lassoMode { model.clearSelection() }
            } label: {
                Label("投げ縄", systemImage: "lasso")
                    .symbolVariant(model.lassoMode ? .fill : .none)
            }
            .tint(model.lassoMode ? .accentColor : nil)
            .disabled(model.isBusy)

            Divider().frame(height: 22)

            Button {
                // first responder でないと canvas.undoManager が nil になり得るので window 側へフォールバック。
                let undo = canvas.undoManager ?? canvas.window?.undoManager
                undo?.undo()
            } label: { Image(systemName: "arrow.uturn.backward") }
            .disabled(model.isBusy)

            Button(role: .destructive) {
                canvas.drawing = PKDrawing()
                model.clearSelection()
            } label: { Image(systemName: "trash") }
            .disabled(model.isBusy)

            Spacer()

            // 設定(指入力トグル) + 検証メニュー
            Menu {
                Picker(selection: $model.paper) {
                    ForEach(MathNoteModel.Paper.allCases) { p in Text(p.label).tag(p) }
                } label: {
                    Label("用紙", systemImage: "squareshape.split.3x3")
                }
                Toggle(isOn: $model.pencilOnly) {
                    Label("Apple Pencil のみ(手のひら防止)", systemImage: "pencil.tip")
                }
                Section("検証(開発用)") {
                    NavigationLink(value: SpikeRoute.ocr) { Label("Spike A: OCR", systemImage: "a.circle") }
                    NavigationLink(value: SpikeRoute.compute) { Label("Spike B: 計算", systemImage: "b.circle") }
                    NavigationLink(value: SpikeRoute.foundationModel) { Label("Spike C: FM", systemImage: "c.circle") }
                    NavigationLink(value: SpikeRoute.mlxBench) { Label("Spike D: MLX ベンチ", systemImage: "d.circle") }
                    NavigationLink(value: SpikeRoute.pythonSolve) { Label("Spike E: Python 求解", systemImage: "e.circle") }
                }
            } label: {
                Image(systemName: "ellipsis.circle")
            }
        }
        .font(.title3)
        .labelStyle(.iconOnly)
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(.thinMaterial, in: Capsule())
        .overlay(Capsule().strokeBorder(.quaternary))
        .shadow(color: .black.opacity(0.08), radius: 8, y: 2)
    }
}

// MARK: - 投げ縄直上の選択ポップオーバー

struct SelectionPopover: View {
    let onRecognize: () -> Void
    let onEditLatex: () -> Void
    let onCancel: () -> Void

    var body: some View {
        HStack(spacing: 6) {
            Button(action: onRecognize) {
                Label("認識して解く", systemImage: "sparkles")
                    .font(.subheadline.weight(.semibold))
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)

            Button(action: onEditLatex) {
                Image(systemName: "character.cursor.ibeam")
            }
            .buttonStyle(.bordered)
            .controlSize(.small)

            Button(action: onCancel) {
                Image(systemName: "xmark")
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(.regularMaterial, in: Capsule())
        .overlay(Capsule().strokeBorder(.quaternary))
        .shadow(color: .black.opacity(0.12), radius: 6, y: 2)
    }
}

// MARK: - 処理中オーバーレイ

struct ProcessingOverlay: View {
    let phase: MathNoteModel.Phase
    let isFirstLoad: Bool
    let loadProgress: Double

    private var title: String {
        switch phase {
        case .recognizing: return "手書きを認識中…"
        case .solving:     return "計算中…"
        case .idle:        return ""
        }
    }

    var body: some View {
        ZStack {
            Color.black.opacity(0.12).ignoresSafeArea()
            VStack(spacing: 12) {
                ProgressView()
                    .controlSize(.large)
                Text(title).font(.headline)
                if phase == .recognizing && isFirstLoad {
                    Text("初回はモデル準備中(~3.2GB)。少し時間がかかります")
                        .font(.caption).foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                    if loadProgress > 0 && loadProgress < 1 {
                        ProgressView(value: loadProgress)
                            .frame(width: 220)
                    }
                }
            }
            .padding(28)
            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))
            .shadow(color: .black.opacity(0.15), radius: 16, y: 4)
        }
        .transition(.opacity)
    }
}

// MARK: - 用紙背景(白紙 / 方眼)

/// ノートの紙。ダークモードでも白い紙にし、方眼なら薄いグリッド線を引く。
/// キャンバスは背景透明なので、この上に手書きが乗る。
struct PaperBackground: View {
    let paper: MathNoteModel.Paper

    var body: some View {
        ZStack {
            Color.white
            if paper == .grid {
                Canvas { ctx, size in
                    let step: CGFloat = 28
                    var path = Path()
                    var x = step
                    while x < size.width {
                        path.move(to: CGPoint(x: x, y: 0))
                        path.addLine(to: CGPoint(x: x, y: size.height)); x += step
                    }
                    var y = step
                    while y < size.height {
                        path.move(to: CGPoint(x: 0, y: y))
                        path.addLine(to: CGPoint(x: size.width, y: y)); y += step
                    }
                    ctx.stroke(path, with: .color(.black.opacity(0.08)), lineWidth: 0.5)
                }
            }
        }
    }
}

// MARK: - ノートに置く結果カード(ドラッグで移動)

/// 答えをノート上に置く小さなカード。ドラッグで移動、タップで詳細シート、✕で削除。
struct ResultCard: View {
    let card: MathNoteModel.PlacedResult
    let onTap: () -> Void
    let onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                Text(MathDisplay.kindLabel(card.result.kind))
                    .font(.caption2).foregroundStyle(.secondary)
                if card.result.verified {
                    Image(systemName: "checkmark.seal.fill")
                        .font(.caption2).foregroundStyle(.green)
                }
                Spacer(minLength: 8)
                Button(action: onClose) {
                    Image(systemName: "xmark.circle.fill").foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
            Text(card.result.answer.map(MathDisplay.pretty).joined(separator: ",  "))
                .font(.headline)
                .foregroundStyle(.primary)
        }
        .padding(10)
        .frame(maxWidth: 220, alignment: .leading)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(.quaternary))
        .shadow(color: .black.opacity(0.12), radius: 6, y: 2)
        .contentShape(RoundedRectangle(cornerRadius: 12))
        .onTapGesture(perform: onTap)
    }
}
