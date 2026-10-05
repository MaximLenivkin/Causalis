from pathlib import Path
import ast, json, re
root=Path.cwd()
mods={}
for p in (root/'causalis').rglob('*.py'):
    rel=p.relative_to(root).with_suffix('')
    parts=list(rel.parts)
    if parts[-1]=='__init__': parts.pop()
    mod='.'.join(parts)
    tree=ast.parse(p.read_text(encoding='utf-8-sig'))
    names={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
    for n in tree.body:
        if isinstance(n,ast.ImportFrom): names.update(a.asname or a.name for a in n.names)
        if isinstance(n,(ast.Assign,ast.AnnAssign)):
            targets=n.targets if isinstance(n,ast.Assign) else [n.target]
            names.update(t.id for t in targets if isinstance(t,ast.Name))
    mods[mod]={'file':str(p.relative_to(root)),'names':sorted(names)}
html=(root/'notebooks/api/html/apidocs/causalis')
existing={p.stem for p in html.glob('causalis*.html')}
current=set(mods)
missing=[m for m in sorted(current-existing) if not any(x.startswith('_') for x in m.split('.')[1:])]
stale=sorted(existing-current)
notebooks=list((root/'notebooks').rglob('*.ipynb'))
imports=[]
for p in notebooks:
    data=json.loads(p.read_text(encoding='utf-8-sig'))
    for i,c in enumerate(data['cells'],1):
        if c['cell_type']!='code': continue
        src=''.join(c['source'])
        src='\n'.join(l for l in src.splitlines() if not l.lstrip().startswith(('%','!')))
        try: tree=ast.parse(src)
        except SyntaxError: continue
        for n in ast.walk(tree):
            if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('causalis'):
                if n.module not in mods: imports.append({'file':str(p.relative_to(root)),'cell':i,'module':n.module,'status':'missing module'})
                else:
                    for a in n.names:
                        if a.name!='*' and a.name not in mods[n.module]['names']:
                            imports.append({'file':str(p.relative_to(root)),'cell':i,'module':n.module,'name':a.name,'status':'not in static namespace; verify'})
out={'current_source_modules':len(mods),'generated_api_modules':len(existing),'notebooks':len(notebooks),'missing_public_api_modules':missing,'stale_api_modules':stale,'notebook_import_flags':imports}
(root/'audit/docs_inventory.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(out,indent=2,ensure_ascii=False))
