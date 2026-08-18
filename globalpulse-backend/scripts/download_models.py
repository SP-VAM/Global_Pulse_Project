"""
GlobalPulse — ML Model Downloader (runs at Render container startup)
=====================================================================
Downloads ONLY 1-Day prediction model files and metadata encoders.
Completely excludes 10d, 5d, and heavy multi-gigabyte models to ensure
fast startup, minimal memory usage, and zero disk bloat.
"""

import os
import sys
import time

# Only 1-Day prediction models and shared encoders
TARGET_FILES = [
    "label_encoder.pkl",
    "model_features.pkl",
    "model_1d_binary.pkl",
    "model_1d_binary_encoder.pkl",
    "model_1d_binary_features.pkl",
    "model_1d_3class_encoder.pkl",
    "model_1d_3class_features.pkl",
]

# Explicitly ignore 10d, 5d, and heavy models
IGNORE_PATTERNS = ["10d", "5d", "xgboost_model"]

def main() -> None:
    print("=" * 60, flush=True)
    print("GlobalPulse — 1-Day ML Model Download (Hugging Face Hub)", flush=True)
    print("=" * 60, flush=True)

    hf_repo_id = os.environ.get("HF_REPO_ID", "").strip()
    hf_token   = os.environ.get("HF_TOKEN", "").strip()
    model_dir  = os.environ.get("STOCK_MODEL_DIR", "app/data/stocks/models").strip()

    if not hf_repo_id:
        print("WARNING: HF_REPO_ID not set — skipping model download.", flush=True)
        return

    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        print("ERROR: huggingface_hub package not installed.", flush=True)
        sys.exit(1)

    os.makedirs(model_dir, exist_ok=True)

    try:
        api = HfApi(token=hf_token if hf_token else None)
        all_remote = [
            f for f in api.list_repo_files(repo_id=hf_repo_id, repo_type="model")
            if f.endswith(".pkl")
        ]
    except Exception as e:
        print(f"ERROR: Could not list files in {hf_repo_id}: {e}", flush=True)
        return

    # Filter: Keep target files, exclude any with 10d/5d/xgboost_model
    selected_files = [
        f for f in all_remote
        if f in TARGET_FILES or (not any(pat in f.lower() for pat in IGNORE_PATTERNS))
    ]

    print(f"Downloading {len(selected_files)} 1-Day model files (10d & 5d excluded):", flush=True)
    for f in selected_files:
        print(f"  • {f}", flush=True)

    downloaded = skipped = failed = 0

    for filename in selected_files:
        dest = os.path.join(model_dir, filename)

        if os.path.exists(dest) and os.path.getsize(dest) > 100:
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(f"  ✓ Already exists ({size_mb:.2f} MB): {filename}", flush=True)
            skipped += 1
            continue

        print(f"  ↓ Downloading: {filename} ...", flush=True)
        t0 = time.time()
        try:
            local_path = hf_hub_download(
                repo_id=hf_repo_id,
                filename=filename,
                repo_type="model",
                token=hf_token if hf_token else None,
                local_dir=model_dir,
            )
            elapsed = time.time() - t0
            size_mb = os.path.getsize(local_path) / (1024 * 1024)
            print(f"  ✓ Done: {filename} ({size_mb:.2f} MB in {elapsed:.1f}s)", flush=True)
            downloaded += 1
        except Exception as e:
            print(f"  ✗ Warning downloading {filename}: {e}", flush=True)
            failed += 1

    print("=" * 60, flush=True)
    print(f"Summary: {downloaded} downloaded, {skipped} skipped, {failed} failed", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    main()
