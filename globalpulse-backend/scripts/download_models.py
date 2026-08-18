"""
GlobalPulse — ML Model Downloader
===================================
Runs BEFORE uvicorn starts (see Dockerfile CMD).
Downloads large .pkl model files from Google Drive into the models directory.
Skips files that already exist on disk (safe to re-run).

HOW TO GET A GOOGLE DRIVE FILE ID:
  1. Upload the .pkl file to Google Drive
  2. Right-click → Share → Change to "Anyone with the link"
  3. Copy the link: https://drive.google.com/file/d/FILE_ID_HERE/view
  4. Paste just the FILE_ID_HERE into MODEL_FILES below
"""

import os
import sys
import urllib.request
import urllib.error

# ── Configuration ─────────────────────────────────────────────────────────────
# Directory where models will be saved (matches STOCK_MODEL_DIR in config.py)
MODEL_DIR = os.environ.get("STOCK_MODEL_DIR", "app/data/stocks/models")

# ── Model File Registry ────────────────────────────────────────────────────────
# Format: "filename.pkl": "GOOGLE_DRIVE_FILE_ID"
# Fill in the Google Drive File IDs after uploading your .pkl files.
MODEL_FILES = {
    "xgboost_model.pkl":                   os.environ.get("GDRIVE_XGBOOST_MODEL", ""),
    "label_encoder.pkl":                   os.environ.get("GDRIVE_LABEL_ENCODER", ""),
    "model_features.pkl":                  os.environ.get("GDRIVE_MODEL_FEATURES", ""),
    "model_1d_3class.pkl":                 os.environ.get("GDRIVE_MODEL_1D_3CLASS", ""),
    "model_1d_3class_encoder.pkl":         os.environ.get("GDRIVE_MODEL_1D_3CLASS_ENC", ""),
    "model_1d_3class_features.pkl":        os.environ.get("GDRIVE_MODEL_1D_3CLASS_FEAT", ""),
    "model_1d_binary.pkl":                 os.environ.get("GDRIVE_MODEL_1D_BINARY", ""),
    "model_1d_binary_encoder.pkl":         os.environ.get("GDRIVE_MODEL_1D_BINARY_ENC", ""),
    "model_1d_binary_features.pkl":        os.environ.get("GDRIVE_MODEL_1D_BINARY_FEAT", ""),
    "model_5d_3class.pkl":                 os.environ.get("GDRIVE_MODEL_5D_3CLASS", ""),
    "model_5d_3class_encoder.pkl":         os.environ.get("GDRIVE_MODEL_5D_3CLASS_ENC", ""),
    "model_5d_3class_features.pkl":        os.environ.get("GDRIVE_MODEL_5D_3CLASS_FEAT", ""),
    "model_5d_binary.pkl":                 os.environ.get("GDRIVE_MODEL_5D_BINARY", ""),
    "model_5d_binary_encoder.pkl":         os.environ.get("GDRIVE_MODEL_5D_BINARY_ENC", ""),
    "model_5d_binary_features.pkl":        os.environ.get("GDRIVE_MODEL_5D_BINARY_FEAT", ""),
    "model_10d_3class.pkl":                os.environ.get("GDRIVE_MODEL_10D_3CLASS", ""),
    "model_10d_3class_encoder.pkl":        os.environ.get("GDRIVE_MODEL_10D_3CLASS_ENC", ""),
    "model_10d_3class_features.pkl":       os.environ.get("GDRIVE_MODEL_10D_3CLASS_FEAT", ""),
    "model_10d_binary.pkl":                os.environ.get("GDRIVE_MODEL_10D_BINARY", ""),
    "model_10d_binary_encoder.pkl":        os.environ.get("GDRIVE_MODEL_10D_BINARY_ENC", ""),
    "model_10d_binary_features.pkl":       os.environ.get("GDRIVE_MODEL_10D_BINARY_FEAT", ""),
    "model_10d_binary_sector.pkl":         os.environ.get("GDRIVE_MODEL_10D_SECTOR", ""),
    "model_10d_binary_sector_encoder.pkl": os.environ.get("GDRIVE_MODEL_10D_SECTOR_ENC", ""),
    "model_10d_binary_sector_features.pkl":os.environ.get("GDRIVE_MODEL_10D_SECTOR_FEAT", ""),
}

# JSON metric files — small, commit to git instead (these are skipped here)
SKIP_EXTENSIONS = {".json"}

# ── Download Helper ────────────────────────────────────────────────────────────

def gdrive_url(file_id: str) -> str:
    """Build the direct Google Drive download URL for a given file ID."""
    return f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"


def download_file(url: str, dest: str) -> None:
    """Download a file from url to dest with progress logging."""
    print(f"  ↓ Downloading → {os.path.basename(dest)}", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=600) as response, open(dest, "wb") as out:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 1024 * 1024  # 1 MB chunks
            while True:
                data = response.read(chunk)
                if not data:
                    break
                out.write(data)
                downloaded += len(data)
                if total:
                    pct = downloaded * 100 // total
                    print(f"    {pct}% ({downloaded // (1024*1024)} MB / {total // (1024*1024)} MB)", flush=True)
        print(f"  ✓ Done: {os.path.basename(dest)}", flush=True)
    except Exception as e:
        print(f"  ✗ FAILED: {os.path.basename(dest)} — {e}", flush=True)
        # Remove partial file
        if os.path.exists(dest):
            os.remove(dest)
        raise


def main() -> None:
    print("=" * 60, flush=True)
    print("GlobalPulse — ML Model Download Check", flush=True)
    print("=" * 60, flush=True)

    os.makedirs(MODEL_DIR, exist_ok=True)

    skipped = 0
    downloaded = 0
    failed = 0

    for filename, file_id in MODEL_FILES.items():
        dest = os.path.join(MODEL_DIR, filename)
        ext = os.path.splitext(filename)[1]

        # Skip non-pkl files
        if ext in SKIP_EXTENSIONS:
            continue

        # Already on disk — skip
        if os.path.exists(dest) and os.path.getsize(dest) > 1024:
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(f"  ✓ Already exists ({size_mb:.1f} MB): {filename}", flush=True)
            skipped += 1
            continue

        # No Google Drive ID configured — skip with warning
        if not file_id:
            print(f"  ⚠ No GDRIVE ID set for {filename} — skipping", flush=True)
            skipped += 1
            continue

        try:
            download_file(gdrive_url(file_id), dest)
            downloaded += 1
        except Exception:
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
