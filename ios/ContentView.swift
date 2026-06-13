// アプリの最初の画面。新メイン「全画面手書き数学ノート」MathNoteView に委譲する。
// (MathAIApp が ContentView() を呼ぶ構造を保ったまま、中身を新 UI へ置換した)
// 旧・埋め込み小キャンバス+確認カードの ScrollView 実装は廃止。
import SwiftUI

struct ContentView: View {
    var body: some View {
        MathNoteView()
    }
}

/// 検証用 Spike 画面への遷移ルート。FloatingActionBar の「…」メニューと
/// MathNoteView の navigationDestination で使う。
enum SpikeRoute: Hashable {
    case ocr, compute, foundationModel, mlxBench, pythonSolve
}
