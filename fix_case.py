import subprocess
import os

repo_dir = r"d:\Orbit"
try:
    idx = subprocess.check_output(["git", "ls-files"], cwd=repo_dir, text=True)
    for line in idx.splitlines():
        if "frontend/src/lib/api" in line.lower() or "frontend/src/lib/api-client" in line.lower():
            original_name = line.strip()
            print(f"FOUND IN GIT: {original_name}")
            
            # If it's not strictly lowercase
            if original_name != original_name.lower():
                print(f"Attempting to rename {original_name} to {original_name.lower()}...")
                # To bypass Windows being case-insensitive, we rename to a temp name first
                temp_name = original_name + ".tmp"
                subprocess.run(["git", "mv", "-f", original_name, temp_name], cwd=repo_dir)
                subprocess.run(["git", "mv", "-f", temp_name, original_name.lower()], cwd=repo_dir)
                print(f"Renamed {original_name} to {original_name.lower()}")
except Exception as e:
    print(f"Error: {e}")
