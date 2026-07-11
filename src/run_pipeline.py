import subprocess
import sys
from pathlib import Path


CODE_DIR = Path(__file__).resolve().parent


def run(script_name):
    script = CODE_DIR / script_name
    print(f"\n=== Running {script.name} ===")
    subprocess.run([sys.executable, str(script)], check=True)


def main():
    run("initial_data_diagnostic.py")
    run("spectral_pipeline.py")
    run("sensitivity_analysis.py")
    run("dispersion_analysis.py")


if __name__ == "__main__":
    main()
