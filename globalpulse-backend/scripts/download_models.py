"""
GlobalPulse — ML Model Downloader (runs at Render container startup)
=====================================================================
Downloads essential .pkl model files from Hugging Face Hub into the models
directory. Skips files that already exist on disk.

Memory-safe: Prioritizes lightweight models (<250MB) to stay well within
Render Free Tier (512MB RAM limit).
"""

import os
import sys
import time

# Priority list of model files needed by the prediction service
PRIORITY_FILES = [
    "label_encoder.pkl",
    "model_features.pkl",
    "model_5d_binary.pkl",
    "model_5d_binary_encoder.pkl",
    "model_5d_binary_features.pkl",
    "model_1d_binary.pkl",
    "model_1d_binary_encoder.pkl",
    "model_1d_binary_features.pkl",
    "model_5d_3class.pkl",
    "model_5d_3class_encoder.pkl",
    "model_5d_3class_features.pkl",
    "model_10d_binary.pkl",
    "model_10d_binary_encoder.pkl",
    "model_10d_binary_features.pkl",
]

def main() -> None:
    print("=" * 60, flush=True)
    print("GlobalPulse — ML Model Download Check (Hugging Face Hub)", flush=True)
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

    if not all_remote:
        print(f"WARNING: No .pkl files found in {hf_repo_id}", flush=True)
        return

    # Order files: priority files first, then rest
    ordered_files = [f for f in PRIORITY_FILES if f in all_remote]
    ordered_files += [f for f in all_remote if f not in ordered_files]

    downloaded = skipped = failed = 0

    for filename in ordered_files:
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
