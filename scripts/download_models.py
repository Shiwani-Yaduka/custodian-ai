"""
Download MediaPipe Face Landmarker model into web/public/models/
Size is ~3.75 MB. Runs offline once downloaded.
"""
import shutil
import sys
import urllib.request
from pathlib import Path

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
ROOT = Path(__file__).resolve().parent.parent
DEST_DIR = ROOT / "web" / "public" / "models"
DEST_FILE = DEST_DIR / "face_landmarker.task"
WASM_SRC = ROOT / "web" / "node_modules" / "@mediapipe" / "tasks-vision" / "wasm"
WASM_DEST = ROOT / "web" / "public" / "wasm"


def sync_wasm():
    if WASM_SRC.exists():
        WASM_DEST.mkdir(parents=True, exist_ok=True)
        for item in WASM_SRC.glob("*"):
            dest_item = WASM_DEST / item.name
            if not dest_item.exists() or dest_item.stat().st_size != item.stat().st_size:
                shutil.copy2(item, dest_item)
        print(f"[models] Synchronized local MediaPipe WASM assets to {WASM_DEST}.")


def download_model():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    sync_wasm()

    if DEST_FILE.exists() and DEST_FILE.stat().st_size > 3_000_000:
        size = DEST_FILE.stat().st_size
        print(f"[models] {DEST_FILE.name} already exists ({size} bytes). Skipping.")
        return 0

    print(f"[models] Downloading {MODEL_URL}...")
    try:
        def reporthook(blocknum, blocksize, totalsize):
            percent = blocknum * blocksize * 100 / totalsize
            sys.stdout.write(f"\r[models] Downloading: {min(100.0, percent):.1f}%")
            sys.stdout.flush()

        urllib.request.urlretrieve(MODEL_URL, DEST_FILE, reporthook)
        size = DEST_FILE.stat().st_size
        print(f"\n[models] Successfully downloaded to {DEST_FILE} ({size} bytes).")
        return 0
    except Exception as e:
        print(f"\n[models] Failed to download model: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(download_model())
