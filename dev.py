import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"

def clean():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
        print("✔ output/ cleaned")

def build():
    subprocess.run([sys.executable, "main.py"], check=True)
    print("✔ site generated")

def serve():
    subprocess.run(
        [sys.executable, "-m", "http.server", "800"],
        cwd=OUTPUT_DIR
    )

if __name__ == "__main__":
    clean()
    build()
    serve()
