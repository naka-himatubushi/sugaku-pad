// MathAI アプリのエントリポイント。Goodnotes AI for Math クローン（簡易版・検証ビルド）。
import SwiftUI

@main
struct MathAIApp: App {
    init() {
        // ヘッドレス自己テスト: 環境変数 PYSOLVE_SELFTEST=1 のとき、起動直後に
        // 埋め込み Python で求解して stdout に出す（シミュレータでの runtime 検証用）。
        if ProcessInfo.processInfo.environment["PYSOLVE_SELFTEST"] == "1" {
            Task.detached(priority: .userInitiated) {
                let svc = PythonSolveService()
                for expr in ["2x+3=7", "x^2-5x+6=0", "2x+3>7", "x+y=3; x-y=1"] {
                    // 本流と同じ PythonSolveService 経由（JSON→SolveResult の変換も検証）
                    let r = svc.solve(expr)
                    print("PYSOLVE-SELFTEST \(expr) => supported=\(r.supported) kind=\(r.kind) "
                        + "answer=\(r.answer) verified=\(r.verified)")
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
