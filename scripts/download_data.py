"""Fetch exact upstream v783 files and verify SHA-256 before accepting them."""
import hashlib
from pathlib import Path
import urllib.request

FILES = {
    'Completeness_783.csv': 'bbb847a4cc2caaa7a16349722d220c087317b946d148d4d592d94d250617a311',
    'Connectivity_783.parquet': 'efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347',
}


def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    folder = Path(__file__).resolve().parents[1] / 'data'
    folder.mkdir(exist_ok=True)
    for name, expected in FILES.items():
        target = folder / name
        if target.exists():
            if sha(target) != expected: raise RuntimeError(f'{name}: existing file hash differs; inspect it manually')
            print(f'{name}: already verified'); continue
        temporary = target.with_suffix(target.suffix+'.part')
        try:
            url = 'https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/main/'+name
            with urllib.request.urlopen(url, timeout=90) as source, temporary.open('wb') as dest:
                while chunk := source.read(1024*1024): dest.write(chunk)
            if sha(temporary) != expected: raise RuntimeError(f'{name}: upstream changed or download corrupted')
            temporary.replace(target)
            print(f'{name}: verified')
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__': main()
