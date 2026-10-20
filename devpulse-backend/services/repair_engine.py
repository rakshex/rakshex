"""Deterministic Python requests JSON-key repair. Parses source; never executes it.

A reviewer supplies an explicit rename and provenance. Both inline contracts must
confirm the removed/added request property and an unchanged property schema.
Other SDKs, dynamic payloads and semantic migrations stop for human review.
"""
import ast
import copy
import difflib
import hashlib
import re
from pathlib import PurePosixPath
from urllib.parse import urlsplit
from services.contract_analysis import digest, validate_contract, METHODS

MAX_FILES = 40
MAX_SOURCE_BYTES = 262144


class RepairRefused(ValueError):
    pass


def safe_files(files):
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise RepairRefused('Provide 1–40 explicitly scoped Python files')
    total = 0
    for path, source in files.items():
        parts = PurePosixPath(path).parts if isinstance(path,str) else ()
        if (not parts or len(parts)>8 or len(path)>240 or str(PurePosixPath(path)) != path or path.startswith('/') or
            any(part.startswith('.') or not re.fullmatch(r'[A-Za-z0-9_-]+(?:\.py)?',part) for part in parts)
            or '..' in parts or not path.endswith('.py') or not isinstance(source,str)):
            raise RepairRefused('Only normalized relative Python source/test paths are accepted')
        total += len(source.encode())
        if total > MAX_SOURCE_BYTES or '\x00' in source:
            raise RepairRefused('Source exceeds the supported size or encoding boundary')
    return dict(sorted(files.items()))


def _schema(spec, path, method):
    try:
        operation=spec['paths'][path][method]
        schema=operation['requestBody']['content']['application/json']['schema']
        if schema.get('type')!='object' or not isinstance(schema.get('properties'),dict):
            raise KeyError()
        return schema
    except (KeyError,TypeError):
        raise RepairRefused('An inline JSON object request schema is required') from None


def plan_repair(before, after, files, rule):
    files=safe_files(files)
    validate_contract(before);validate_contract(after)
    method=rule.get('method','').lower();path=rule.get('path','')
    removed=rule.get('removed','');added=rule.get('added','')
    origin=rule.get('origin','');provenance=rule.get('provenance','')
    for name in (removed,added):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',name):
            raise RepairRefused('Rename keys must be simple identifiers')
    if removed==added or method not in ('post','put','patch'):
        raise RepairRefused('Only explicit JSON request key renames are supported')
    parsed=urlsplit(origin)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/') or parsed.port:
        raise RepairRefused('Use a credential-free HTTPS origin without a port')
    if not provenance.startswith('https://') or len(provenance)>500 or urlsplit(provenance).username or urlsplit(provenance).query or urlsplit(provenance).fragment:
        raise RepairRefused('Provide a public HTTPS migration reference without credentials or query')
    old=_schema(before,path,method);new=_schema(after,path,method)
    if removed not in old['properties'] or removed in new['properties'] or added in old['properties'] or added not in new['properties']:
        raise RepairRefused('Contracts do not establish this removed/added property pair')
    if digest(old['properties'][removed])!=digest(new['properties'][added]):
        raise RepairRefused('Property semantics differ; a key rename is unsafe')
    old_normal=dict(old);old_normal['properties']={added if k==removed else k:v for k,v in old['properties'].items()}
    if 'required' in old_normal:
        old_normal['required']=[added if k==removed else k for k in old_normal['required']]
    if digest(old_normal)!=digest(new):
        raise RepairRefused('Other request-schema changes require human review')
    old_op=before['paths'][path][method];new_op=after['paths'][path][method]
    normalized_body=copy.deepcopy(old_op['requestBody'])
    normalized_body['content']['application/json']['schema']=old_normal
    if digest(normalized_body)!=digest(new_op['requestBody']):
        raise RepairRefused('Other request-body changes require human review')
    old_path={k:v for k,v in before['paths'][path].items() if k not in METHODS}
    new_path={k:v for k,v in after['paths'][path].items() if k not in METHODS}
    if digest(old_path)!=digest(new_path):
        raise RepairRefused('Path-level parameter/server changes require human review')
    if digest({k:v for k,v in old_op.items() if k!='requestBody'})!=digest({k:v for k,v in new_op.items() if k!='requestBody'}):
        raise RepairRefused('Other operation changes require human review')
    if digest({k:v for k,v in before.items() if k!='paths'})!=digest({k:v for k,v in after.items() if k!='paths'}):
        raise RepairRefused('Global contract changes require human review')
    target=origin.rstrip('/')+path
    impacts=[];edits=[];unresolved=[]
    for filename,source in files.items():
        try: tree=ast.parse(source,filename)
        except (SyntaxError,ValueError): raise RepairRefused('Every submitted file must parse as Python') from None
        if filename.startswith('tests/'):
            continue  # Never repair the assertions that gate the candidate.
        aliases=set();clients=set()
        for node in tree.body:
            if isinstance(node,ast.Import):
                aliases.update(a.asname or a.name for a in node.names if a.name=='requests')
            if isinstance(node,ast.ImportFrom) and node.module=='requests':
                clients.update((a.asname or a.name,a.name) for a in node.names if a.name==method)
        bound=aliases | {name for name,_ in clients}
        for child in ast.walk(tree):
            if isinstance(child,ast.Import) and any((a.asname or a.name) in bound and a.name!='requests' for a in child.names):
                raise RepairRefused('Conflicting requests import binding')
            if isinstance(child,ast.ImportFrom) and child.module!='requests' and any((a.asname or a.name) in bound for a in child.names):
                raise RepairRefused('Conflicting requests import binding')
            if ((isinstance(child,ast.Name) and isinstance(child.ctx,(ast.Store,ast.Del)) and child.id in bound) or
                (isinstance(child,ast.arg) and child.arg in bound) or
                (isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and child.name in bound) or
                (isinstance(child,ast.Attribute) and isinstance(child.ctx,(ast.Store,ast.Del)) and isinstance(child.value,ast.Name) and child.value.id in bound)):
                raise RepairRefused('Requests aliases are rebound; static repair is unsafe')
        if sum(1 for _ in ast.walk(tree))>30000:raise RepairRefused('Source AST exceeds complexity limit')
        changes=[]
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call):continue
            func=node.func
            matched=(isinstance(func,ast.Attribute) and isinstance(func.value,ast.Name) and func.value.id in aliases and func.attr==method) or (isinstance(func,ast.Name) and (func.id,method) in clients)
            if not matched:continue
            url=node.args[0] if node.args else next((k.value for k in node.keywords if k.arg=='url'),None)
            if not isinstance(url,ast.Constant) or not isinstance(url.value,str):
                unresolved.append({'file':filename,'line':node.lineno,'reason':'dynamic_url'});continue
            if url.value!=target:continue
            payload=next((k.value for k in node.keywords if k.arg=='json'),None)
            if not isinstance(payload,ast.Dict) or any(k is None or not isinstance(k,ast.Constant) or not isinstance(k.value,str) for k in payload.keys):
                unresolved.append({'file':filename,'line':node.lineno,'reason':'dynamic_payload'});continue
            keys=[k.value for k in payload.keys]
            if len(keys)!=len(set(keys)) or added in keys:
                raise RepairRefused('Ambiguous or already-mixed payload keys')
            for key in payload.keys:
                if key.value==removed:
                    impacts.append({'file':filename,'line':key.lineno,'column':key.col_offset+1,'kind':'request_property_rename'})
                    changes.append(key)
        if changes:
            # AST offsets are UTF-8 byte offsets; edit bytes to preserve Unicode and formatting.
            lines=source.encode().splitlines(keepends=True);offsets=[0]
            for line in lines:offsets.append(offsets[-1]+len(line))
            candidate=source.encode()
            for key in sorted(changes,key=lambda k:(k.lineno,k.col_offset),reverse=True):
                start=offsets[key.lineno-1]+key.col_offset;end=offsets[key.end_lineno-1]+key.end_col_offset
                candidate=candidate[:start]+repr(added).encode()+candidate[end:]
            patched=candidate.decode();ast.parse(patched)
            edits.append({'file':filename,'before_hash':hashlib.sha256(source.encode()).hexdigest(),
                          'after_hash':hashlib.sha256(patched.encode()).hexdigest(),'after':patched})
    if unresolved:raise RepairRefused('Dynamic requests calls require human review; no partial patch is released')
    if not impacts:raise RepairRefused('No statically resolved affected requests JSON call in the submitted scope')
    diff_parts=[]
    for edit in edits:
        for line in difflib.unified_diff(files[edit['file']].splitlines(True),edit['after'].splitlines(True),fromfile='a/'+edit['file'],tofile='b/'+edit['file']):
            diff_parts.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
    diff=''.join(diff_parts)
    return {'adapter':'python-requests-json-rename-v1','impacts':impacts,'edits':edits,'diff':diff,
            'patch_hash':hashlib.sha256(diff.encode()).hexdigest(),'source_hash':digest(files),
            'scope':list(files),'rule':rule,'limitations':['Explicit submitted file scope only; dynamic calls and other SDKs are unsupported',
             'A matching schema is not provider semantic approval; human review remains mandatory']}
