"""Refresh statistics from staged notebook artifacts without rebuilding them."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ('build/solution.stats.txt', 'project.stats.txt')


def main():
    git_dir = subprocess.check_output(
        ['git', 'rev-parse', '--absolute-git-dir'], cwd=ROOT, text=True,
    ).strip()
    with tempfile.TemporaryDirectory(prefix='coursework-stats-') as directory:
        snapshot = Path(directory)
        subprocess.run(
            ['git', 'checkout-index', '--all', f'--prefix={snapshot}{os.sep}'],
            cwd=ROOT, check=True,
        )
        subprocess.run(
            [sys.executable, '-m', 'tooling.build.statistics'], cwd=snapshot, check=True,
        )
        env = os.environ.copy()
        env.update(GIT_DIR=git_dir, GIT_WORK_TREE=str(snapshot))
        subprocess.run(
            [sys.executable, '-m', 'tooling.project_stats'],
            cwd=snapshot, env=env, check=True,
        )
        for name in REPORTS:
            destination = ROOT / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(snapshot / name, destination)
    subprocess.run(['git', 'add', '--', *REPORTS], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
