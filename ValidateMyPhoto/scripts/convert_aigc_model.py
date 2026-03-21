#!/usr/bin/env python3
"""
Convert an AI-generated image detection model to Core ML format.

Primary target: Heem2/AI-images-vs-Real-images (ResNet-50 fine-tuned
on ~20k real vs. AI images from Stable Diffusion, MidJourney, DALL-E).

Output: ValidateMyPhoto/ValidateMyPhoto/Resources/AIGCDetector.mlpackage
  - Input  : "image"    CVPixelBuffer 224×224 RGB (sRGB, values 0–255)
             ImageNet normalisation is baked in.
  - Output : "aiScore"  Float32 scalar, range ≈0–1.
             Values ABOVE 0.5 indicate the image is likely AI-generated.
"""

import sys, os, platform
import torch
import torch.nn as nn
import coremltools as ct
from pathlib import Path

OUT_PATH = (
    Path(__file__).parent.parent
    / "ValidateMyPhoto" / "Resources"
    / "AIGCDetector.mlpackage"
)
IMG_SIZE = 224
IS_MACOS = platform.system() == "Darwin"

# ---------------------------------------------------------------------------
# 1. HuggingFace fine-tuned detector
# ---------------------------------------------------------------------------

def load_hf_model():
    from transformers import AutoModelForImageClassification
    print("Downloading Heem2/AI-images-vs-Real-images from HuggingFace...")
    hf = AutoModelForImageClassification.from_pretrained(
        "Heem2/AI-images-vs-Real-images",
        ignore_mismatched_sizes=True,
    )
    hf.eval()
    num_labels = hf.config.num_labels
    id2label   = getattr(hf.config, "id2label", {})
    print(f"  Downloaded. num_labels={num_labels}, id2label={id2label}")
    return hf, num_labels, id2label


class HFWrapper(nn.Module):
    """
    Wraps a HuggingFace AutoModelForImageClassification.
    Input : normalised float tensor (1, 3, H, W)
    Output: scalar in [0,1] — probability image is AI-generated
    """
    def __init__(self, hf_model, ai_class_idx: int):
        super().__init__()
        self.body   = hf_model
        self.ai_idx = ai_class_idx

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.body(pixel_values=x).logits          # (B, C)
        if logits.shape[1] == 1:
            prob = torch.sigmoid(logits[:, 0])
        else:
            prob = torch.softmax(logits, dim=1)[:, self.ai_idx]
        return prob.unsqueeze(-1)                           # (B, 1)


# ---------------------------------------------------------------------------
# 2. timm ResNet-50 fallback
# ---------------------------------------------------------------------------

def load_timm_model(pretrained: bool = True):
    import timm
    tag = "pretrained" if pretrained else "random weights"
    print(f"Loading timm ResNet-50 ({tag})...")
    m = timm.create_model("resnet50", pretrained=pretrained, num_classes=1)
    m.eval()
    return m


class TimmWrapper(nn.Module):
    def __init__(self, body):
        super().__init__()
        self.body = body

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.body(x))   # (B, 1)


# ---------------------------------------------------------------------------
# 3. Convert to Core ML  (.mlpackage — works with Xcode 14+ / macOS 13+)
# ---------------------------------------------------------------------------

def convert(model: nn.Module, out_path: Path, label: str):
    model.eval()
    example = torch.zeros(1, 3, IMG_SIZE, IMG_SIZE)
    print("Tracing model with torch.jit.trace ...")
    with torch.no_grad():
        traced = torch.jit.trace(model, example)

    print("Converting to Core ML (mlprogram / macOS 13+) ...")
    mlmodel = ct.convert(
        traced,
        inputs=[
            ct.ImageType(
                name="image",
                shape=(1, 3, IMG_SIZE, IMG_SIZE),
                # Bake in ImageNet normalisation: pixel → (pixel/255 - mean) / std
                scale=1.0 / 255.0,
                bias=[
                    -0.485 / 0.229,   # R
                    -0.456 / 0.224,   # G
                    -0.406 / 0.225,   # B
                ],
                color_layout=ct.colorlayout.RGB,
                channel_first=True,
            )
        ],
        outputs=[ct.TensorType(name="aiScore")],
        minimum_deployment_target=ct.target.macOS13,
        convert_to="mlprogram",
    )

    mlmodel.short_description = (
        "Binary AI-generated image detector. "
        "aiScore > 0.5 → likely AI-generated. "
        f"Source: {label}"
    )
    mlmodel.author  = "ValidateMyPhoto"
    mlmodel.version = "1.0"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Remove stale output if present
    if out_path.exists():
        import shutil
        shutil.rmtree(str(out_path))
    mlmodel.save(str(out_path))

    if out_path.is_dir():
        size_mb = sum(f.stat().st_size for f in out_path.rglob("*") if f.is_file()) / 1_048_576
    else:
        size_mb = out_path.stat().st_size / 1_048_576
    print(f"Saved → {out_path}  ({size_mb:.1f} MB)")
    return mlmodel


# ---------------------------------------------------------------------------
# 4. Smoke-test (macOS only — requires libcoremlpython native binary)
# ---------------------------------------------------------------------------

def smoke_test(mlmodel, label: str):
    if not IS_MACOS:
        print("Smoke-test skipped (requires macOS to run Core ML inference).")
        return
    import numpy as np
    from PIL import Image as PILImage
    print(f"Smoke-testing '{label}' ...")
    dummy = PILImage.fromarray(
        (np.random.rand(IMG_SIZE, IMG_SIZE, 3) * 255).astype("uint8"), "RGB"
    )
    preds = mlmodel.predict({"image": dummy})
    score = float(preds["aiScore"].flatten()[0])
    print(f"  Random-noise image → aiScore = {score:.4f}  (expect ~0.5 for random input)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("ValidateMyPhoto — Core ML Model Converter")
    print("=" * 60)

    wrapper = None
    label   = ""

    # Attempt 1 — HuggingFace fine-tuned detector
    try:
        hf_model, num_labels, id2label = load_hf_model()
        ai_idx = 1
        for idx, name in id2label.items():
            if any(kw in str(name).lower() for kw in ("ai", "fake", "generated", "artificial")):
                ai_idx = int(idx)
                break
        print(f"  AI-class index = {ai_idx}  ({id2label.get(ai_idx, '?')})")
        wrapper = HFWrapper(hf_model, ai_idx)
        label   = "Heem2/AI-images-vs-Real-images (HuggingFace)"
    except Exception as e:
        print(f"HuggingFace model failed: {e}")

    # Attempt 2 — timm pretrained
    if wrapper is None:
        try:
            wrapper = TimmWrapper(load_timm_model(pretrained=True))
            label   = "timm ResNet-50 (ImageNet pretrained — NOT fine-tuned for AI detection)"
        except Exception as e:
            print(f"timm pretrained failed: {e}")

    # Attempt 3 — timm random weights (architecture stub)
    if wrapper is None:
        try:
            wrapper = TimmWrapper(load_timm_model(pretrained=False))
            label   = "timm ResNet-50 (random weights — architecture stub only)"
        except Exception as e:
            print(f"timm random failed: {e}")
            sys.exit(1)

    mlmodel = convert(wrapper, OUT_PATH, label)
    smoke_test(mlmodel, label)

    print()
    print("Next steps:")
    print(f"  1. In Xcode, drag {OUT_PATH.name} into the file navigator")
    print(f"     (ensure 'Copy items if needed' is checked,")
    print(f"      target membership: ValidateMyPhoto).")
    print(f"  2. The Swift class 'AIGCDetector' is auto-generated by Xcode.")
    print(f"  3. Rebuild — AIPatternDetector will automatically use the model.")
    if "random weights" in label or "ImageNet" in label:
        print()
        print("  WARNING: The model was built WITHOUT fine-tuned AI-detection weights.")
        print("  For production accuracy, replace with weights from:")
        print("    https://huggingface.co/Heem2/AI-images-vs-Real-images")
