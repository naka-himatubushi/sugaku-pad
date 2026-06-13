"""Spike A probe: pix2tex を Core ML 化できるか Mac 上で確認する（Xcode 不要）。

pix2tex は ViT エンコーダ + 自己回帰デコーダ。デコーダのループ変換は難しいため、
まずエンコーダ単体の Core ML 変換可否を測る。結果がどうあれ Spike A の判断材料。
"""
import torch
import coremltools as ct
from pix2tex.cli import LatexOCR


def main() -> None:
    ocr = LatexOCR()
    model = ocr.model
    print("model:", type(model).__name__,
          "| encoder:", hasattr(model, "encoder"),
          "| decoder:", hasattr(model, "decoder"))

    enc = model.encoder
    enc.eval()
    shape = (1, 1, 192, 672)
    dummy = torch.zeros(*shape)

    # 戦略1: torch.jit.trace → coremltools
    try:
        with torch.no_grad():
            traced = torch.jit.trace(enc, dummy, check_trace=False)
        ml = ct.convert(traced, inputs=[ct.TensorType(name="image", shape=shape)])
        ml.save("spikes/ocr/pix2tex_encoder.mlpackage")
        print(f"✅ jit.trace 経路で変換成功 shape={shape}")
        return
    except Exception as e:
        print(f"❌ jit.trace 失敗: {type(e).__name__}: {str(e)[:160]}")

    # 戦略2: torch.export → run_decompositions → coremltools（新パイプライン）
    try:
        with torch.no_grad():
            exported = torch.export.export(enc, (dummy,))
            exported = exported.run_decompositions({})  # TRAINING→ATEN dialect へ
        ml = ct.convert(exported)
        ml.save("spikes/ocr/pix2tex_encoder.mlpackage")
        print(f"✅ torch.export 経路で変換成功 shape={shape}")
        return
    except Exception as e:
        print(f"❌ torch.export 失敗: {type(e).__name__}: {str(e)[:160]}")

    print("→ pix2tex は標準経路で Core ML 化できない。Spike A の結論: MLX 経路 / "
          "export 向きの別 OCR モデル / 入力は手入力＋確認カード を検討。")


if __name__ == "__main__":
    main()
