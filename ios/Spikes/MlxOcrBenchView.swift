// Spike D: MLX Swift による端末内 OCR ベンチ。
// 目的 = iPad 実機で「Qwen2.5-VL 3B(4bit) をオンデバイス実行したときの速度と RAM」を測る。
// バンドルした手書き画像を OCR にかけ、ロード時間 / cold・warm latency / tokens/s /
// 物理フットプリント(phys_footprint) / 残メモリ余裕を画面に出す。
//
// 設計メモ:
// - モデルは初回起動時に HuggingFace から ~3.2GB DL（要 Wi-Fi）。2回目以降はキャッシュ。
// - GPU キャッシュ上限を絞り、端末のメモリ枯渇(jetsam)を避ける。
// - latency は連続 N 回計測し、1回目=cold、平均(2回目以降)=warm として Ollama 実測と比較する。
import SwiftUI
import MLX
import MLXLMCommon
import MLXVLM

/// 1 回の推論結果（latency と認識テキスト、スループット）。
struct RunSample: Identifiable {
    let id = UUID()
    let index: Int
    let seconds: Double
    let tokensPerSecond: Double
    let text: String
}

@MainActor
@Observable
final class MlxOcrBench {
    var status: String = "未実行"
    var loadSeconds: Double?
    var footprintAfterLoadMB: Double?
    var peakFootprintMB: Double?
    var availableMB: Double?
    var samples: [RunSample] = []
    var running = false

    // Python 版ベンチ(eval_handwriting.py)と同一プロンプトで条件を揃える。
    private let prompt =
        "You are a precise math OCR. Transcribe the handwritten math expression into ONE line "
        + "of LaTeX. Output ONLY the LaTeX, no explanation, no dollar signs, no code fences."

    /// ベンチ本体: ロード → N 回 OCR → 指標収集。
    func run(iterations: Int = 3) async {
        guard !running else { return }
        running = true
        defer { running = false }
        samples = []
        loadSeconds = nil
        peakFootprintMB = nil

        guard let imageURL = Bundle.main.url(forResource: "handwriting_sample", withExtension: "png")
        else {
            status = "エラー: バンドルに handwriting_sample.png が無い"
            return
        }

        // GPU キャッシュ上限を絞ってメモリ枯渇を防ぐ（公式 MLXChatExample と同方針）。
        MLX.GPU.set(cacheLimit: 20 * 1024 * 1024)

        do {
            // --- モデルロード（初回は DL 込み） ---
            status = "モデルをロード中…（初回は ~3.2GB DL）"
            let t0 = Date()
            // hub は既定値(defaultHubApi)に任せる。HubApi.default は版により無いので渡さない。
            let container = try await VLMModelFactory.shared.loadContainer(
                configuration: VLMRegistry.qwen2_5VL3BInstruct4Bit
            ) { [weak self] progress in
                Task { @MainActor in
                    self?.status = "DL/ロード中 \(Int(progress.fractionCompleted * 100))%"
                }
            }
            loadSeconds = Date().timeIntervalSince(t0)
            footprintAfterLoadMB = MemoryProbe.footprintMB()

            // --- N 回 OCR して latency / tokens-per-sec を測る ---
            var peak = MemoryProbe.footprintMB()
            for i in 0..<iterations {
                status = "推論 \(i + 1)/\(iterations)…"
                let start = Date()
                let (text, tps) = try await ocr(container: container, imageURL: imageURL)
                let elapsed = Date().timeIntervalSince(start)
                samples.append(
                    RunSample(index: i, seconds: elapsed, tokensPerSecond: tps, text: text))
                peak = max(peak, MemoryProbe.footprintMB())
            }
            peakFootprintMB = peak
            availableMB = MemoryProbe.availableMB()
            status = "完了"
        } catch {
            status = "エラー: \(error.localizedDescription)"
        }
    }

    /// 1 枚の画像を OCR し、認識テキストと生成スループット(tokens/s)を返す。
    private func ocr(container: ModelContainer, imageURL: URL) async throws -> (String, Double) {
        let chat: [Chat.Message] = [
            .init(role: .user, content: prompt, images: [.url(imageURL)], videos: [])
        ]
        let userInput = UserInput(
            chat: chat, processing: .init(resize: .init(width: 1024, height: 1024)))

        let stream = try await container.perform { (context: ModelContext) in
            let lmInput = try await context.processor.prepare(input: userInput)
            // 決定的に測るため temperature=0。
            return try MLXLMCommon.generate(
                input: lmInput, parameters: GenerateParameters(temperature: 0), context: context)
        }

        var out = ""
        var tps = 0.0
        for await item in stream {
            if let chunk = item.chunk { out += chunk }
            if let info = item.info { tps = info.tokensPerSecond }
        }
        return (out.trimmingCharacters(in: .whitespacesAndNewlines), tps)
    }
}

struct MlxOcrBenchView: View {
    @State private var bench = MlxOcrBench()

    private var warmAvg: Double? {
        let warm = bench.samples.filter { $0.index > 0 }.map(\.seconds)
        guard !warm.isEmpty else { return nil }
        return warm.reduce(0, +) / Double(warm.count)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Spike D: MLX 端末内 OCR ベンチ")
                    .font(.title3).bold()
                Text("Qwen2.5-VL 3B(4bit) を iPad 内で実行し、速度と RAM を実測する。")
                    .font(.caption).foregroundStyle(.secondary)

                Button(bench.running ? "実行中…" : "ベンチ開始（3回）") {
                    Task { await bench.run(iterations: 3) }
                }
                .buttonStyle(.borderedProminent)
                .disabled(bench.running)

                Text("状態: \(bench.status)").font(.callout)

                metricsCard
                if !bench.samples.isEmpty { runsCard }
            }
            .padding()
        }
        .navigationTitle("MLX ベンチ")
    }

    private var metricsCard: some View {
        VStack(alignment: .leading, spacing: 6) {
            row("モデルロード", bench.loadSeconds.map { String(format: "%.1f s", $0) })
            row("cold latency", bench.samples.first.map { String(format: "%.2f s", $0.seconds) })
            row("warm latency(平均)", warmAvg.map { String(format: "%.2f s", $0) })
            row(
                "生成スループット",
                bench.samples.last.map { String(format: "%.1f tok/s", $0.tokensPerSecond) })
            row("RAM(ロード後)", bench.footprintAfterLoadMB.map { String(format: "%.0f MB", $0) })
            row("RAM(ピーク)", bench.peakFootprintMB.map { String(format: "%.0f MB", $0) })
            row("残メモリ余裕", bench.availableMB.map { String(format: "%.0f MB", $0) })
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    private var runsCard: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("各回の認識結果").font(.caption).foregroundStyle(.secondary)
            ForEach(bench.samples) { s in
                Text("#\(s.index + 1)  \(String(format: "%.2fs", s.seconds))  →  \(s.text)")
                    .font(.system(.footnote, design: .monospaced))
                    .textSelection(.enabled)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    private func row(_ label: String, _ value: String?) -> some View {
        HStack {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            Text(value ?? "—").bold().monospacedDigit()
        }
        .font(.callout)
    }
}
