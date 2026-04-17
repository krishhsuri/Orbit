import subprocess
with open('git_lib_files.txt', 'w') as f:
    out = subprocess.check_output(['git', 'ls-files', 'frontend/src/lib'], text=True)
    f.write(out)
