// 端末内 OCR サービス: 手書き UIImage → LaTeX 1 行。
// MlxOcrBenchView(Spike D)の MLX ロード/推論ロジックを抽出し再構成したもの。
// - モデル(Qwen2.5-VL 3B 4bit)は初回だけロードして container を保持(以降 warm)。
// - 入力画像は bench で実証済みの images:[.url(tmpPNG)] 経路に揃える
//   (UIImage → temporaryDirectory に PNG 書き出し → .url)。
//   .ciImage 直渡しは bench と異なり通らないリスクがあるため採らない。
// - プロンプト / temperature=0 / resize 1024 も bench と同一にして挙動を揃える。
// - cross-actor 設計: 表示状態(loadProgress/isLoaded)だけ @MainActor で持ち、
//   重い MLX 推論・ロード本体は MainActor 外の actor(OcrEngine)で回す。
//   進捗更新だけ Task { @MainActor in ... } でメインへ hop し UI を詰まらせない。
// 新規 SwiftPM 依存はゼロ(MLX/MLXVLM/MLXLMCommon は既存 project.yml の依存)。
import Foundation
import UIKit
import MLX
import MLXLMCommon
import MLXVLM

/// MainActor 外で MLX のロード/推論を回す actor。
/// container をこの actor 内で保持し、cross-actor で UI を巻き込まない。
/// 進捗は呼び出し側が渡す MainActor クロージャ越しに通知する。
actor OcrEngine {
    private var container: ModelContainer?

    // Spike D / Python 版ベンチと同一プロンプトで条件を揃える。
    private let prompt =
        "You are a precise math OCR. Transcribe the handwritten math expression into ONE line "
        + "of LaTeX. Output ONLY the LaTeX, no explanation, no dollar signs, no code fences."

    /// 既にロード済みか(初回オーバーレイの文言切替に使う)。
    var isLoaded: Bool { container != nil }

    /// 手書き画像(PNG エンコード済みバイト列)を LaTeX 1 行に認識する。MainActor 外で実行される。
    /// UIImage は Sendable でないため、cross-actor 安全な Data(PNG)を受け取る設計にしている。
    /// - Parameter pngData: PNG エンコード済みの画像データ。
    /// - Parameter onProgress: ロード進捗(0...1)を通知する MainActor 隔離クロージャ。
    func recognize(
        pngData: Data,
        onProgress: @MainActor @escaping (Double) -> Void
    ) async throws -> String {
        // GPU キャッシュ上限を絞ってメモリ枯渇(jetsam)を防ぐ(公式 MLXChatExample と同方針)。
        MLX.GPU.set(cacheLimit: 20 * 1024 * 1024)

        let container = try await loadIfNeeded(onProgress: onProgress)

        // bench と同じく一時 PNG に書き出して .url で渡す。
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("mathai-ocr-\(UUID().uuidString).png")
        try pngData.write(to: url)
        defer { try? FileManager.default.removeItem(at: url) }

        let chat: [Chat.Message] = [
            .init(role: .user, content: prompt, images: [.url(url)], videos: [])
        ]
        // 重要: 正方形 1024x1024 リサイズはしない(横長の式を縦に潰してアスペクト比が壊れ、
        //       認識が激しく劣化していた)。モデル既定の前処理(アスペクト比保持)に任せる。
        let userInput = UserInput(chat: chat)

        let stream = try await container.perform { (context: ModelContext) in
            let lmInput = try await context.processor.prepare(input: userInput)
            return try MLXLMCommon.generate(
                input: lmInput, parameters: GenerateParameters(temperature: 0), context: context)
        }

        var out = ""
        for await item in stream {
            if let chunk = item.chunk { out += chunk }
        }
        return out.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// 初回のみモデルをロード(DL 込み)。2 回目以降は保持済み container を返す。
    private func loadIfNeeded(
        onProgress: @MainActor @escaping (Double) -> Void
    ) async throws -> ModelContainer {
        if let c = container { return c }
        await MainActor.run { onProgress(0) }
        // Qwen2-VL 2B 4bit。実機 MLX 実効ベンチで 3B(4/6)を上回る 6/6・かつ軽い(~1.5GB)で
        // 8GB iPad の冷えロードも安定。SmolVLM(1/6) は精度不足、7B は 16GB 機向け。
        let c = try await VLMModelFactory.shared.loadContainer(
            configuration: VLMRegistry.qwen2VL2BInstruct4Bit
        ) { progress in
            Task { @MainActor in onProgress(progress.fractionCompleted) }
        }
        container = c
        await MainActor.run { onProgress(1) }
        return c
    }
}

@MainActor
@Observable
final class MathOcrService {
    /// モデルロードの進捗(0...1)。初回 ~3.2GB DL の期待値調整に使う。
    var loadProgress: Double = 0
    /// ロード済みかどうか(初回オーバーレイの文言切替に使う)。
    /// engine 側の真実をミラーした表示用フラグ(MainActor で読める)。
    private(set) var isLoaded: Bool = false

    /// MLX 推論本体を回す actor(MainActor 外)。
    private let engine = OcrEngine()

    /// 手書き画像を LaTeX 1 行に認識する。
    /// 推論本体は engine(MainActor 外)で回し、進捗更新だけ MainActor へ hop する。
    /// UIImage の PNG エンコードはここ(呼び出し側)で済ませ、actor へは Sendable な Data を渡す。
    func recognize(_ image: UIImage) async throws -> String {
        guard let pngData = image.pngData() else {
            throw OcrError.imageEncodingFailed
        }
        let result = try await engine.recognize(pngData: pngData) { [weak self] progress in
            self?.loadProgress = progress
        }
        isLoaded = true
        loadProgress = 1
        return result
    }

    enum OcrError: LocalizedError {
        case imageEncodingFailed
        var errorDescription: String? {
            switch self {
            case .imageEncodingFailed: return "画像の書き出しに失敗しました"
            }
        }
    }
}
