"""
export_td_structure2.py
-----------------------
Esporta la struttura del progetto in JSON, con il testo dei DAT e i valori
reali dei parametri custom.

Differenza dalla v1: il filtro sui DAT usa la famiglia, non i nomi di
classe. o.type restituisce 'text', 'script', 'chopexec' - non 'textDAT' -
e per quello la v1 tornava sempre a mani vuote.

USO
  Text DAT in /project1, incolla, tasto destro > Run Script.
  Il percorso del JSON esce nel Textport.
"""

import json
import os

ROOT        = '/project1'
MAX_DEPTH   = 6
MAX_TEXT    = 40000   # caratteri per singolo DAT di script
TABLE_ROWS  = 6       # righe di esempio per i DAT tabellari
OUT_NAME    = 'td_structure2.json'

# DAT che contengono dati, non codice: ne bastano poche righe
TABLE_TYPES = ('table', 'info', 'select', 'in', 'out', 'null',
               'merge', 'sort', 'reorder', 'substitute', 'evaluate')

count = {'ops': 0}


def safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def dump_pars(o):
    out = {}
    for p in safe(lambda: o.pars(), []) or []:
        try:
            if p.readOnly:
                continue
            mode = str(p.mode).upper()
            if 'EXPRESSION' in mode:
                out[p.name] = {'expr': p.expr}
                continue
            if 'EXPORT' in mode:
                out[p.name] = {'export': str(safe(lambda: p.exportOP.path, '?'))}
                continue
            if p.isDefault and not p.isCustom:
                continue
            v = p.val
            if isinstance(v, (int, float, bool, str)):
                if isinstance(v, str) and len(v) > 400:
                    v = v[:400] + '...[taglio]'
                out[p.name] = v
            else:
                out[p.name] = str(v)[:200]
        except Exception:
            continue
    return out


def dat_content(o, t):
    """Codice per intero, tabelle solo a campione."""
    if t in TABLE_TYPES:
        rows = []
        try:
            for r in range(min(o.numRows, TABLE_ROWS)):
                rows.append([str(c.val) for c in o.row(r)])
        except Exception:
            pass
        return {'numRows': safe(lambda: o.numRows, 0),
                'numCols': safe(lambda: o.numCols, 0),
                'sample': rows}
    txt = safe(lambda: o.text, '') or ''
    if len(txt) > MAX_TEXT:
        txt = txt[:MAX_TEXT] + '\n...[tagliato, %d caratteri]' % len(txt)
    return {'text': txt} if txt else None


def dump_op(o, depth):
    count['ops'] += 1
    t = safe(lambda: o.type, '?')
    fam = safe(lambda: o.family, '?')
    d = {'name': o.name, 'path': o.path, 'type': t, 'family': fam}

    ins = safe(lambda: [i.path for i in o.inputs], []) or []
    if ins:
        d['inputs'] = ins

    pars = dump_pars(o)
    if pars:
        d['pars'] = pars

    for key, fn in (('errors', lambda: o.errors()), ('warnings', lambda: o.warnings())):
        v = safe(fn, '') or ''
        if v:
            d[key] = v[:800]

    if fam == 'DAT':
        c = dat_content(o, t)
        if c:
            d['content'] = c

    if fam == 'CHOP':
        d['chans'] = safe(lambda: [c.name for c in o.chans()][:80], [])
        d['numSamples'] = safe(lambda: o.numSamples, 0)

    # per l'Audio VST: i metodi di invio, che sono l'interfaccia utile
    if t == 'audiovst':
        d['send_methods'] = [m for m in dir(o) if m.startswith('send')]

    if safe(lambda: o.isCOMP, False):
        cp = []
        for p in safe(lambda: o.customPars, []) or []:
            try:
                cp.append({'name': p.name, 'label': p.label,
                           'style': str(p.style),
                           'val': str(p.val)[:120],
                           'default': str(p.default)[:120]})
            except Exception:
                continue
        if cp:
            d['custom_pars'] = cp
        if depth < MAX_DEPTH:
            kids = safe(lambda: list(o.children), []) or []
            if kids:
                d['children'] = [x for x in (dump_op(k, depth + 1) for k in kids)
                                 if x is not None]
    return d


root_op = op(ROOT)
if root_op is None:
    raise RuntimeError('non trovo %s' % ROOT)

report = {
    'td_version': safe(lambda: app.version, '?'),
    'td_build': safe(lambda: app.build, '?'),
    'os': safe(lambda: app.osName, '?'),
    'project_file': safe(lambda: project.name, '?'),
    'fps': safe(lambda: me.time.rate, '?'),
    'root': ROOT,
    'tree': dump_op(root_op, 0),
}

folder = safe(lambda: project.folder, '') or ''
if not folder or not os.path.isdir(folder):
    folder = os.path.expanduser('~/Desktop')
out_path = os.path.join(folder, OUT_NAME)

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=1, ensure_ascii=False)

size = os.path.getsize(out_path)
print('=' * 62)
print(' file      :', out_path)
print(' peso      : %.1f KB' % (size / 1024.0))
print(' operatori :', count['ops'])
print('')
print(' se supera 1 MB: abbassa MAX_TEXT, o metti ROOT su un solo COMP')
print('=' * 62)