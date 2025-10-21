import os
import sys
import subprocess


def main():
    project_root = os.path.dirname(__file__)
    cache_dir = os.path.join(project_root, ".pycache")

    # Ensure centralized .pycache exists
    os.makedirs(cache_dir, exist_ok=True)

    # Set env var before running target script
    os.environ["PYTHONPYCACHEPREFIX"] = cache_dir

    # Define which script to run (change this as needed)
    target_module = "scripts.document_embedder"

    print(f"Using centralized pycache at: {cache_dir}")
    print(f"Running module: {target_module}")

    # Launch the module with the current environment
    subprocess.run([sys.executable, "-m", target_module], env=os.environ)


if __name__ == "__main__":
    main()
