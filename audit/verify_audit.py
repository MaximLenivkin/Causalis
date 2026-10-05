"""Check report section counts and absolute local links; no library mutations."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
issues = []
checked = 0
line_counts = {}
for report in sorted(ROOT.glob('*.md')):
    content = report.read_text(encoding='utf-8')
    for target in re.findall(r'\]\((D:/[^)]+)\)', content):
        match = re.fullmatch(r'(.*?)(?::(\d+))?', target)
        path = Path(match[1])
        checked += 1
        if not path.exists():
            issues.append({'report': report.name, 'target': target, 'error': 'missing'})
        elif match[2]:
            if path not in line_counts:
                line_counts[path] = len(path.read_text(encoding='utf-8').splitlines())
            if not 1 <= int(match[2]) <= line_counts[path]:
                issues.append({'report': report.name, 'target': target, 'error': 'line out of bounds'})

def table_count(filename, heading):
    body = (ROOT / filename).read_text(encoding='utf-8').split(heading, 1)[1]
    body = body.split('\n## ', 1)[0]
    rows = [line for line in body.splitlines() if line.startswith('|') and not re.match(r'^\|[- :|]+$', line)]
    return len(rows) - 1

sections = {
    'code_top10': ('REPORT.md', '## Топ-10 ошибок кода и методологии', 10),
    'code_additional': ('REPORT.md', '## Остальные подтверждённые находки', 21),
    'docs_top10': ('REPORT.md', '## Топ-10 проблем документации', 10),
    'methods_top10': ('REPORT.md', '## Топ-10 методологических расширений', 10),
    'features_top10': ('REPORT.md', '## Топ-10 функций и улучшений API', 10),
    'performance_top10': ('PERFORMANCE.md', '## Топ-10 оптимизаций', 10),
}
counts = {}
for name, (filename, heading, expected) in sections.items():
    counts[name] = table_count(filename, heading)
    if counts[name] != expected:
        issues.append({'section': name, 'actual': counts[name], 'expected': expected})

result = {'local_links_checked': checked, 'table_counts': counts, 'issues': issues}
(ROOT / 'report_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(bool(issues))
