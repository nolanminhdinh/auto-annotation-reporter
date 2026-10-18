"""Windows entrypoint: create the local runtime, install dependencies, then launch."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parents[1]


def main():
    if os.name!='nt' or sys.version_info < (3,10):
        print('Desktop setup requires Windows and Python 3.10 or newer.',file=sys.stderr)
        return 1
    arguments=sys.argv[1:]
    setup_only='--setup-only' in arguments
    arguments=[arg for arg in arguments if arg!='--setup-only']
    if setup_only and arguments:
        print('SETUP_AUTO takes no pipeline arguments. Pass source options to START_AUTO.',file=sys.stderr)
        return 1
    environment=ROOT/'.venv'
    python=environment/'Scripts/python.exe'
    try:
        if not python.exists():
            print('[Setup] Creating .venv...',flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
        version=subprocess.run([str(python),'-c','import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'],cwd=ROOT)
        if version.returncode:
            raise RuntimeError('Existing .venv uses an old Python version. Create a Python 3.10+ environment before continuing.')
        requirements=ROOT/'requirements-desktop.txt'
        digest=hashlib.sha256(requirements.read_bytes()).hexdigest()
        marker=environment/'.desktop-requirements.sha256'
        probe=('import requests, dotenv, pg8000; from importlib.metadata import version; '
               'from pathlib import Path; '
               'pairs=[line.strip().split("==") for line in Path("requirements-desktop.txt").read_text().splitlines() if "==" in line and not line.lstrip().startswith("#")]; '
               'assert all(version(name)==expected for name,expected in pairs)')
        imports=subprocess.run([str(python),'-c',probe],cwd=ROOT,capture_output=True,timeout=30)
        if imports.returncode or not marker.exists() or marker.read_text().strip()!=digest:
            print('[Setup] Installing the Desktop dependency versions...',flush=True)
            subprocess.run([str(python),'-m','pip','install','-r',str(requirements)],cwd=ROOT,check=True,timeout=300)
            marker.write_text(digest,encoding='utf-8')
        config=ROOT/'config/desktop.local.json'
        if not config.exists():
            shutil.copyfile(ROOT/'config/desktop.example.json',config)
            print('[Setup] Created config/desktop.local.json (demo mode).')
        if not (ROOT/'.env').exists():
            shutil.copyfile(ROOT/'.env.example',ROOT/'.env')
            print('[Setup] Created .env template. Demo needs no source tokens.')
        if setup_only:
            print('Runtime ready. Run START_AUTO.cmd; use START_AUTO.cmd --doctor for prerequisite diagnostics.')
            return 0
        command=[str(python),'-X','utf8','-B',str(ROOT/'src/auto_desktop.py')]
        if '--doctor' not in arguments: command+=['--open-report']
        return subprocess.run(command+arguments,cwd=ROOT).returncode
    except subprocess.CalledProcessError:
        print('Dependency installation failed. Check Internet/proxy access and run SETUP_AUTO.cmd again.',file=sys.stderr)
    except subprocess.TimeoutExpired:
        print('Setup timed out. Check network access and rerun SETUP_AUTO.cmd.',file=sys.stderr)
    except (OSError,RuntimeError) as error:
        print('Setup could not complete: '+str(error),file=sys.stderr)
    return 1


if __name__=='__main__': raise SystemExit(main())
