import json, importlib, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
p=Path('audit/docs_inventory.json')
data=json.loads(p.read_text())
for item in data['notebook_import_flags']:
    try:
        m=importlib.import_module(item['module'])
        getattr(m,item['name'])
        item['verified_status']='export exists (dynamic namespace)'
    except Exception as e:
        item['verified_status']=f'{type(e).__name__}: {e}'
p.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8')
errors=[x for x in data['notebook_import_flags'] if x['verified_status']!='export exists (dynamic namespace)']
print({'checked_flags':len(data['notebook_import_flags']),'errors':errors})
