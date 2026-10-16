"""Read-only toolkit startup; no fetch, indexing, build or publication."""
import json
from workspace import ROOT, verify, git, remote_inventory
from source_size import startup_check


def check():
    verified = verify()
    return {'cwd': str(ROOT), 'branch': git('branch', '--show-current'),
            'head': git('rev-parse', 'HEAD'), 'selected_baseline': verified['baseline'],
            'baseline_kind': verified['baseline_kind'], 'remotes': remote_inventory(),
            'tools': 'installed in this checkout', 'dirty': git('status', '--short'),
            'startup_skill': str(ROOT / '.agents/skills/xray-core-start/SKILL.md'),
            'configuration': verified, 'source_size': startup_check()}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
