import json
import platform
import shutil
import subprocess

result = {'platform':platform.platform(), 'processor':platform.processor(), 'python':platform.python_version()}
if shutil.which('nvidia-smi'):
    r = subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],
                       capture_output=True,text=True,timeout=15)
    result['gpu'] = r.stdout.strip() if r.returncode == 0 else r.stderr.strip()
else:
    result['gpu'] = 'nvidia-smi unavailable; GPU not verified'
print(json.dumps(result,indent=2))
