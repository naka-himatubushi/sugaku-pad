// Spike C: 端末内 Foundation Models（iOS 26）が使えるか実機で確認する画面。
// FoundationModels の API（SystemLanguageModel / LanguageModelSession）は iOS 26 想定。
// 実 SDK と差異があればコンパイル時に判明するので、Xcode 投入後に実 API へ合わせる。
import SwiftUI
#if canImport(FoundationModels)
import FoundationModels
#endif

struct FoundationModelAvailabilityView: View {
    @State private var status = "未確認"
    @State private var sample = ""

    var body: some View {
        VStack(spacing: 16) {
            Text("Spike C: Foundation Models").font(.headline)
            Text(status)
            Text(sample).font(.caption).textSelection(.enabled)
            Button("確認する") { Task { await check() } }
                .buttonStyle(.borderedProminent)
        }
        .padding()
    }

    func check() async {
        #if canImport(FoundationModels)
        if #available(iOS 26.0, *) {
            let model = SystemLanguageModel.default
            switch model.availability {
            case .available:
                status = "available ✅"
                do {
                    let session = LanguageModelSession()
                    let reply = try await session.respond(to: "2x + 3 = 7 を解くと x は？数値だけ答えて。")
                    sample = "FM 応答: \(reply.content)"
                } catch {
                    sample = "応答エラー: \(error)"
                }
            case .unavailable(let reason):
                status = "unavailable ❌ (\(String(describing: reason)))"
            @unknown default:
                status = "unknown"
            }
        } else {
            status = "iOS 26 未満 → Foundation Models 非対応"
        }
        #else
        status = "FoundationModels SDK なし（Xcode / iOS が古い）"
        #endif
    }
}
