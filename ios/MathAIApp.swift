// MathAI アプリのエントリポイント。Goodnotes AI for Math クローン（簡易版・検証ビルド）。
import SwiftUI

@main
struct MathAIApp: App {
    init() {
        // ヘッドレス自己テスト: 環境変数 PYSOLVE_SELFTEST=1 のとき、起動直後に
        // 埋め込み Python で求解して stdout に出す（シミュレータでの runtime 検証用）。
        if ProcessInfo.processInfo.environment["PYSOLVE_SELFTEST"] == "1" {
            Task.detached(priority: .userInitiated) {
                for expr in ["2x+3=7", "x^2-5x+6=0", "2x+3>7", "x+y=3; x-y=1"] {
                    let json = PythonBridge.solveJSON(expr)
                    print("PYSOLVE-SELFTEST \(expr) => \(json)")
                }
                print("PYSOLVE-SELFTEST-DONE")
            }
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
