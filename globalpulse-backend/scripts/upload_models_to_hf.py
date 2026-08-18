"""
GlobalPulse — ML Model Uploader (Run this ONCE from your PC)
=============================================================
This script uploads all .pkl model files from your local machine
to Hugging Face Hub (free, no office restrictions).

SETUP:
  1. pip install huggingface_hub
  2. Create a FREE account at https://huggingface.co/join
  3. Go to https://huggingface.co/settings/tokens
     → New token → Name: "globalpulse" → Role: Write → Generate
  4. Paste your token below OR set as env var: HF_TOKEN=your_token
  5. Run: python scripts/upload_models_to_hf.py
"""

import os
import sys

try:
    from huggingface_hub import HfApi, create_repo
except ImportError:
    print("ERROR: huggingface_hub not installed.")
    print("Run: pip install huggingface_hub")
    sys.exit(1)

# ── CONFIGURE THESE ────────────────────────────────────────────────────────────
HF_TOKEN    = os.environ.get("HF_TOKEN", "")          # paste your HF token here if not set as env var
HF_USERNAME = os.environ.get("HF_USERNAME", "")       # your Hugging Face username
REPO_NAME   = "globalpulse-ml-models"                 # will be created automatically

# Local model directory
MODEL_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "app", "data", "stocks", "models"
)
# ──────────────────────────────────────────────────────────────────────────────

def main():
    if not HF_TOKEN:
        print("ERROR: HF_TOKEN not set.")
        print("  Option A: set env var:  set HF_TOKEN=your_token_here")
        print("  Option B: edit this script and paste token in HF_TOKEN variable")
        sys.exit(1)

    if not HF_USERNAME:
        print("ERROR: HF_USERNAME not set.")
        print("  set HF_USERNAME=your_huggingface_username")
        sys.exit(1)

    repo_id = f"{HF_USERNAME}/{REPO_NAME}"
    api = HfApi(token=HF_TOKEN)

    # Create the repo if it doesn't exist (private by default)
    print(f"Creating/verifying repo: {repo_id} ...")
    create_repo(repo_id=repo_id, repo_type="model", private=True, exist_ok=True, token=HF_TOKEN)
    print(f"✓ Repo ready: https://huggingface.co/{repo_id}")

    # Find all .pkl files in model directory
    model_path = os.path.abspath(MODEL_DIR)
    if not os.path.exists(model_path):
        print(f"ERROR: Model directory not found: {model_path}")
        sys.exit(1)

    pkl_files = [f for f in os.listdir(model_path) if f.endswith(".pkl")]
    if not pkl_files:
        print("No .pkl files found in model directory.")
        sys.exit(1)

    print(f"\nFound {len(pkl_files)} model files to upload:")
    for f in pkl_files:
        size_mb = os.path.getsize(os.path.join(model_path, f)) / (1024 * 1024)
        print(f"  {f}  ({size_mb:.1f} MB)")

    print(f"\nUploading to {repo_id} ...")
    for filename in pkl_files:
        local_path = os.path.join(model_path, filename)
        size_mb = os.path.getsize(local_path) / (1024 * 1024)
        print(f"\n↑ Uploading {filename} ({size_mb:.1f} MB) ...", flush=True)
        try:
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=filename,
                repo_id=repo_id,
                repo_type="model",
                token=HF_TOKEN,
            )
            print(f"  ✓ Done: {filename}", flush=True)
        except Exception as e:
            print(f"  ✗ FAILED: {filename} — {e}", flush=True)

    print(f"\n{'='*60}")
    print(f"All models uploaded to: https://huggingface.co/{repo_id}")
    print(f"\nSet this env var in Render:")
    print(f"  HF_REPO_ID = {repo_id}")
    print(f"  HF_TOKEN   = (your token — keep this secret)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
