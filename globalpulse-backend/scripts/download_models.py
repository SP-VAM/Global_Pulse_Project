"""
GlobalPulse — ML Model Downloader (runs at Render container startup)
=====================================================================
Downloads large .pkl model files from Hugging Face Hub into the models
directory BEFORE uvicorn starts. Skips files that already exist on disk.

Required environment variables (set in Render dashboard):
  HF_REPO_ID  — e.g. "your_username/globalpulse-ml-models"
  HF_TOKEN    — Hugging Face read token (keep private)
"""

import os
import sys
import time

def main() -> None:
    print("=" * 60, flush=True)
    print("GlobalPulse — ML Model Download Check (Hugging Face Hub)", flush=True)
    print("=" * 60, flush=True)

    # ── Read config from environment ──────────────────────────────────────────
    hf_repo_id = os.environ.get("HF_REPO_ID", "").strip()
    hf_token   = os.environ.get("HF_TOKEN", "").strip()
    model_dir  = os.environ.get("STOCK_MODEL_DIR", "app/data/stocks/models").strip()

    if not hf_repo_id:
        print("WARNING: HF_REPO_ID not set — skipping model download.", flush=True)
        print("  Stock predictions will fail if model files are missing.", flush=True)
        return

    # ── Try importing huggingface_hub ─────────────────────────────────────────
    try:
        from huggingface_hub import HfApi, hf_hub_download, list_repo_files
    except ImportError:
        print("ERROR: huggingface_hub package not installed.", flush=True)
        print("  Add 'huggingface_hub' to requirements.txt", flush=True)
        sys.exit(1)

    os.makedirs(model_dir, exist_ok=True)

    # ── Get list of files in the HF repo ─────────────────────────────────────
    try:
        api = HfApi(token=hf_token if hf_token else None)
        remote_files = [
            f for f in api.list_repo_files(repo_id=hf_repo_id, repo_type="model")
            if f.endswith(".pkl")
        ]
    except Exception as e:
        print(f"ERROR: Could not list files in {hf_repo_id}: {e}", flush=True)
        print("  Check HF_REPO_ID and HF_TOKEN are correct.", flush=True)
        return

    if not remote_files:
        print(f"WARNING: No .pkl files found in {hf_repo_id}", flush=True)
        return

    print(f"Found {len(remote_files)} model files in {hf_repo_id}", flush=True)

    downloaded = skipped = failed = 0

    for filename in remote_files:
        dest = os.path.join(model_dir, filename)

        # Already on disk with real content — skip
        if os.path.exists(dest) and os.path.getsize(dest) > 1024:
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(f"  ✓ Already exists ({size_mb:.1f} MB): {filename}", flush=True)
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
                local_dir_use_symlinks=False,
            )
            elapsed = time.time() - t0
            size_mb = os.path.getsize(local_path) / (1024 * 1024)
            print(f"  ✓ Done: {filename} ({size_mb:.1f} MB in {elapsed:.1f}s)", flush=True)
            downloaded += 1
        except Exception as e:
            print(f"  ✗ FAILED: {filename} — {e}", flush=True)
            failed += 1

    print("=" * 60, flush=True)
    print(f"Summary: {downloaded} downloaded, {skipped} skipped, {failed} failed", flush=True)

    if failed > 0:
        print("WARNING: Some models failed to download. Predictions may not work.", flush=True)
    else:
        print("All models ready. Starting server...", flush=True)

    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
