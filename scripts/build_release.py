"""Create a clean, reproducible source archive using an explicit allowlist."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('api', 'tests', 'docs', 'knowledge', 'prompts', 'workflow', '.github', 'scripts')
FILES = ('README.md', 'requirements.txt', 'Dockerfile', 'docker-compose.yml', 'docker-compose.dify.yml', '.env.example',
         '.gitignore', '.gitattributes', '.dockerignore', 'pyproject.toml', 'LICENSE', '启动工作台.cmd', '运行测试.cmd', '项目讲解与面试问答.md', '核心基础知识与名词解释.md')


def build():
    paths = [ROOT / name for name in FILES]
    for directory in DIRECTORIES:
        paths.extend(p for p in (ROOT / directory).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.db')
                     and (p.suffix != '.png' or p.parent in (ROOT / 'docs' / 'images', ROOT / 'docs' / 'screenshots')))
    paths = sorted(set(paths))
    manifest = {}
    for path in paths:
        content = path.read_bytes()
        if re.search(rb'(?:app-|sk-)[A-Za-z0-9]{16,}', content):
            raise RuntimeError(f'Possible secret in {path.relative_to(ROOT)}')
        manifest[path.relative_to(ROOT).as_posix()] = hashlib.sha256(content).hexdigest()
    output = ROOT / 'release'
    output.mkdir(exist_ok=True)
    target = output / 'smart-travel-agent-v1.0.0.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        def write(name, content):
            info = zipfile.ZipInfo('smart-travel-agent/' + name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
        for path in paths:
            write(path.relative_to(ROOT).as_posix(), path.read_bytes())
        write('MANIFEST.json', json.dumps(manifest, indent=2))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest + '  ' + target.name + '\n', encoding='utf-8')
    print(f'{target.name}: {len(paths)} files; SHA256 {digest}')


if __name__ == '__main__':
    build()
