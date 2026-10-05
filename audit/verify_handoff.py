"""Verify portable documentation links against the exact audited Git snapshot."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit'
text = (AUDIT / 'DOCUMENTATION_HANDOFF.md').read_text(encoding='utf-8')
pattern = r'https://github.com/causalis-causalcraft/Causalis/blob/([0-9a-f]{40})/([^\s)#]+)(?:#L(\d+))?'
issues = []
checked = 0
for sha, path, line in re.findall(pattern, text):
    result = subprocess.run(['git', 'show', f'{sha}:{path}'], cwd=ROOT, capture_output=True)
    checked += 1
    if result.returncode:
        issues.append({'path': path, 'error': 'missing at audited commit'})
    elif line and not 1 <= int(line) <= len(result.stdout.decode('utf-8').splitlines()):
        issues.append({'path': path, 'line': line, 'error': 'line out of bounds'})
if re.search(r'\]\((?:[A-Za-z]:[/\\]|file://)', text):
    issues.append({'error': 'handoff contains a local-only file link'})
result = {'snapshot_links_checked': checked, 'issues': issues}
(AUDIT / 'handoff_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(bool(issues))
