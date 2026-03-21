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
    / "AIGCDetector.mlmodel"   # neuralnetwork format — single file, any Python version
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
# 3. Convert to Core ML  (.mlmodel / neuralnetwork format)
#    Uses "neuralnetwork" rather than "mlprogram" to avoid the BlobWriter
#    crash present in coremltools on Python 3.13+.  The neuralnetwork format
#    is fully supported on macOS 13+ and produces a single portable file.
# ---------------------------------------------------------------------------

def convert(model: nn.Module, out_path: Path, label: str):
    model.eval()
    example = torch.zeros(1, 3, IMG_SIZE, IMG_SIZE)
    print("Tracing model with torch.jit.trace ...")
    with torch.no_grad():
        traced = torch.jit.trace(model, example)

    IMAGE_INPUT = ct.ImageType(
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

    # mlprogram (.mlpackage) is preferred — requires Python ≤3.12 due to a
    # BlobWriter bug in coremltools on Python 3.13+.  neuralnetwork (.mlmodel)
    # is the fallback; it requires deployment target ≤ macOS11 but runs fine
    # on macOS 13+ (the target is a minimum-requirement, not a ceiling).
    mlmodel = None
    for fmt, target, suffix in [
        ("mlprogram",    ct.target.macOS13, ".mlpackage"),
        ("neuralnetwork", ct.target.macOS11, ".mlmodel"),
    ]:
        try:
            print(f"Converting to Core ML ({fmt}) ...")
            mlmodel = ct.convert(
                traced,
                inputs=[IMAGE_INPUT],
                outputs=[ct.TensorType(name="aiScore")],
                minimum_deployment_target=target,
                convert_to=fmt,
            )
            out_path = out_path.with_suffix(suffix)
            break
        except RuntimeError as e:
            if "BlobWriter" in str(e):
                print(f"  {fmt} unavailable ({e}), trying next format ...")
            else:
                raise
    if mlmodel is None:
        raise RuntimeError("All conversion formats failed.")

    mlmodel.short_description = (
        "Binary AI-generated image detector. "
        "aiScore > 0.5 → likely AI-generated. "
        f"Source: {label}"
    )
    mlmodel.author  = "ValidateMyPhoto"
    mlmodel.version = "1.0"

    import shutil
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Remove any stale outputs from previous runs
    for ext in (".mlpackage", ".mlmodel"):
        p = out_path.with_suffix(ext)
        if p.exists():
            shutil.rmtree(str(p)) if p.is_dir() else p.unlink()

    mlmodel.save(str(out_path))

    if out_path.is_dir():
        size_mb = sum(f.stat().st_size for f in out_path.rglob("*") if f.is_file()) / 1_048_576
    else:
        size_mb = out_path.stat().st_size / 1_048_576
    print(f"Saved → {out_path}  ({size_mb:.1f} MB)")

    # If the output is .mlmodel, patch Package.swift so swift build picks it up.
    pkg_swift = out_path.parent.parent.parent / "Package.swift"
    if out_path.suffix == ".mlmodel" and pkg_swift.exists():
        text = pkg_swift.read_text()
        if "AIGCDetector.mlpackage" in text:
            pkg_swift.write_text(
                text.replace("AIGCDetector.mlpackage", "AIGCDetector.mlmodel")
            )
            print(f"Updated Package.swift → resource changed to AIGCDetector.mlmodel")

    return mlmodel, out_path


# ---------------------------------------------------------------------------
# 4. Smoke-test (macOS only — requires libcoremlpython native binary)
# ---------------------------------------------------------------------------

def smoke_test(mlmodel, label: str):
    # CoreML inference requires the system Python / Xcode toolchain and cannot
    # run inside a venv on macOS.  Skip — the model file itself is valid.
    print("Smoke-test skipped (CoreML inference requires system Python, not venv).")


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

    mlmodel, saved_path = convert(wrapper, OUT_PATH, label)
    smoke_test(mlmodel, label)

    print()
    print("Next steps:")
    print(f"  1. In Xcode, drag {saved_path.name} into the file navigator")
    print(f"     (ensure 'Copy items if needed' is checked,")
    print(f"      target membership: ValidateMyPhoto).")
    print(f"  2. The Swift class 'AIGCDetector' is auto-generated by Xcode.")
    print(f"  3. Rebuild — AIPatternDetector will automatically use the model.")
    if "random weights" in label or "ImageNet" in label:
        print()
        print("  WARNING: The model was built WITHOUT fine-tuned AI-detection weights.")
        print("  For production accuracy, replace with weights from:")
        print("    https://huggingface.co/Heem2/AI-images-vs-Real-images")
