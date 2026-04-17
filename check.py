import subprocess
try:
    proc = subprocess.run(['git', 'ls-tree', '-r', 'HEAD', '--name-only'], cwd='d:/Orbit', capture_output=True, text=True)
    out = proc.stdout
    for line in out.splitlines():
        if 'frontend/src/lib' in line:
            print(f"GIT FILE: {line}")
except Exception as e:
    print(f"ERROR: {e}")
