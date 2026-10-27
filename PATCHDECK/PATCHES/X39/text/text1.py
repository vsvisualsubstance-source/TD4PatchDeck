# =============================================================
#  TIMELINE — preset e sequenza di scene per texttt (+ flux)
#  Per il progetto aperto: incolla in un Text DAT -> Run Script.
#  Rilanciabile: preset e sequenza esistenti vengono conservati.
#  (Stesso blocco incluso in textual_totale.py)
# =============================================================


def timeline_setup():
    """Preset e timeline per /project1/texttt (+ flux)"""
    import traceback
    COMP = '/project1/texttt'

    ENGINE = r'''# seq_engine — preset e timeline di texttt (+ flux)
import json
import random
import copy

EXCLUDE_PAGES = ('Live', 'Presets', 'Timeline')
EXCLUDE = {'Song', 'Speakers', 'Gain', 'Sensitivity', 'Floor', 'Debug',
           'Audioinput', 'Micgain', 'Threshold', 'Sourcecomp', 'Fluxcomp'}
FLOAT_STYLES = ('Float', 'RGB', 'RGBA', 'XY', 'XYZ', 'UV', 'UVW', 'WH')
DISCRETE_STYLES = ('Int', 'Toggle', 'Menu', 'StrMenu')
KICK_WAIT_MAX = 4.0

STARTERS = (
    ('base', {}),
    ('taglio', {'texttt': {'Text1to2d': True, 'Text2to2d': True,
                           'Cutmode1': 'cols', 'Cutmode2': 'rows', 'Cutjitter': 0.6,
                           'Cutscroll': 0.15, 'Cutamount': 0.1, 'Cutscrollpattern': 'alt'}}),
    ('rarefatto', {'texttt': {'Text1to2d': False, 'Text2to2d': False, 'Text3to2d': True,
                              'Op3d': 0.6, 'Showflux': False, 'Cutmode1': 'off',
                              'Cutmode2': 'off', 'Cutmode3': 'off', 'Bloomamount': 0.4,
                              'Phraseevery': 150}}),
    ('flux', {'texttt': {'Showflux': True, 'Opflux': 1.0, 'Show3d': False,
                         'Text1op2d': 0.4, 'Text2op2d': 0.4, 'Cutmodeflux': 'grid',
                         'Cutholes': 0.2},
              'flux': {'Speed': 10.0}}),
    ('denso', {'texttt': {'Text1to2d': True, 'Phraseto2d': True, 'Text2to2d': True,
                          'Text3to2d': True, 'Show3d': True, 'Blend2d': 'add',
                          'Bloomamount': 1.2, 'Cutmode3': 'bricks', 'Cutholes': 0.15}}),
)

_S = {'playing': False, 'order': [], 'pos': 0, 'cycle': 0, 'nrows': 0,
      'rng': random.Random(1), 'step_t0': 0.0, 'dur': 0.0, 'name': '',
      'frm': {}, 'to': {}, 'trans_t0': 0.0, 'trans': 0.0, 'trans_active': False,
      'last_count': None, 'last_now': None, 'last_status': 0.0, 'warned': set()}


def T():
    return me.parent()


def now():
    return float(absTime.seconds)


def _p(name, default):
    p = getattr(T().par, name, None)
    return p.eval() if p is not None else default


def _warn(msg):
    if msg not in _S['warned']:
        _S['warned'].add(msg)
        print('[timeline]', msg)


def comps():
    out = {'texttt': T()}
    path = _p('Fluxcomp', '../flux')
    f = T().op(path) if path else None
    if f is not None:
        out['flux'] = f
    return out


# ---------------- preset ----------------
def _storable(par):
    try:
        page = par.page.name
    except Exception:
        page = ''
    if page in EXCLUDE_PAGES or par.name in EXCLUDE:
        return False
    return par.style in FLOAT_STYLES or par.style in DISCRETE_STYLES


def snapshot():
    snap = {}
    for key, c in comps().items():
        d = {}
        for par in c.customPars:
            if _storable(par):
                v = par.eval()
                if par.style == 'Toggle':
                    v = bool(v)
                d[par.name] = v
        snap[key] = d
    return snap


def load_all():
    d = T().op('presets_json')
    if d is None:
        return {}
    try:
        data = json.loads(d.text or '{}')
        return data if isinstance(data, dict) else {}
    except Exception:
        _warn('presets_json non è JSON valido')
        return {}


def save_all(data):
    d = T().op('presets_json')
    if d is not None:
        d.text = json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True)
    refresh_menu(data)


def refresh_menu(data=None):
    data = load_all() if data is None else data
    par = getattr(T().par, 'Presetlist', None)
    if par is None:
        return
    cur = par.eval()
    names = sorted(data) or ['-']
    par.menuNames = names
    par.menuLabels = names
    if cur in names:
        par.val = cur


def make_starters():
    base = snapshot()
    data = load_all()
    for name, mods in STARTERS:
        p = copy.deepcopy(base)
        for key, vals in mods.items():
            if key in p:
                p[key].update({k: v for k, v in vals.items() if k in p[key]})
        data[name] = p
    save_all(data)


def _target(name, rng, variation):
    pre = load_all().get(name)
    if not pre:
        return None
    tgt = {}
    for key, c in comps().items():
        for pname, v in pre.get(key, {}).items():
            par = getattr(c.par, pname, None)
            if par is None:
                continue
            if (variation > 0 and par.style in FLOAT_STYLES
                    and isinstance(v, (int, float)) and not isinstance(v, bool)):
                v = v * (1.0 + rng.uniform(-variation, variation))
                lo, hi = par.normMin, par.normMax
                if hi > lo:
                    v = min(max(v, lo), hi)
            tgt[(key, pname)] = v
    return tgt


def start_transition(tgt, secs):
    cs = comps()
    frm = {}
    for (key, pname), v in tgt.items():
        c = cs.get(key)
        par = getattr(c.par, pname, None) if c is not None else None
        if par is None:
            continue
        if par.style in FLOAT_STYLES:
            frm[(key, pname)] = par.eval()
        else:
            try:
                par.val = v
            except Exception:
                pass
    _S.update(frm=frm, to=tgt, trans_t0=now(), trans=max(0.0, secs), trans_active=True)
    if secs <= 0:
        _apply(1.0)


def _apply(k):
    e = k * k * (3.0 - 2.0 * k)
    cs = comps()
    for kp, a in _S['frm'].items():
        c = cs.get(kp[0])
        par = getattr(c.par, kp[1], None) if c is not None else None
        b = _S['to'].get(kp)
        if par is None or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            continue
        try:
            par.val = a + (b - a) * e
        except Exception:
            pass
    if k >= 1.0:
        _S['trans_active'] = False


# ---------------- sequenza ----------------
def _rows():
    t = T().op('sequence')
    rows = []
    if t is None:
        return rows
    for r in range(1, t.numRows):
        cell = t[r, 0]
        name = cell.val.strip() if cell is not None else ''
        if not name or name.startswith('#'):
            continue

        def num(c, d):
            try:
                return float(t[r, c].val)
            except Exception:
                return d
        rows.append((name, num(1, 20.0), num(2, 3.0), max(0.0, num(3, 1.0))))
    return rows


def _make_order(rows, cycle):
    seed = int(_p('Seqseed', 1)) + (cycle if _p('Seqvary', True) else 0)
    rng = random.Random(seed)
    n = len(rows)
    mode = _p('Seqorder', 'list')
    if mode == 'shuffle':
        order = list(range(n))
        rng.shuffle(order)
    elif mode == 'weighted':
        order, last = [], None
        for _ in range(n):
            cands = [i for i in range(n) if i != last] or list(range(n))
            w = [rows[i][3] for i in cands]
            i = rng.choices(cands, weights=w if sum(w) > 0 else None)[0]
            order.append(i)
            last = i
    else:
        order = list(range(n))
    return order, rng


def _begin_cycle(rows):
    order, rng = _make_order(rows, _S['cycle'])
    _S.update(order=order, rng=rng, pos=0, nrows=len(rows))


def _goto(pos):
    rows = _rows()
    if not rows:
        _S['playing'] = False
        _status('sequenza vuota: aggiungi righe in "sequence"')
        return
    if not _S['order'] or _S['nrows'] != len(rows):
        _begin_cycle(rows)
        pos = max(0, min(pos, len(rows) - 1))
    if pos >= len(_S['order']):
        if not _p('Seqloop', True):
            _S['playing'] = False
            _stop_toggle()
            _status('fine sequenza')
            return
        _S['cycle'] += 1
        _begin_cycle(rows)
        pos = 0
    if pos < 0:
        pos = len(_S['order']) - 1
    _S['pos'] = pos
    name, dur, trans, _w = rows[_S['order'][pos]]
    rng = _S['rng']
    jit = min(0.95, max(0.0, _p('Seqjitter', 0.0)))
    dur = dur * _p('Seqscale', 1.0) * (1.0 + rng.uniform(-jit, jit))
    trans = trans * _p('Seqtransscale', 1.0)
    tgt = _target(name, rng, _p('Seqvariation', 0.0))
    if tgt is None:
        _warn('preset "%s" non trovato: salto' % name)
        dur = 0.2
    else:
        start_transition(tgt, trans)
    _S.update(step_t0=now(), dur=max(0.2, dur), name=name)
    _status(force=True)


def _stop_toggle():
    par = getattr(T().par, 'Seqplay', None)
    if par is not None:
        par.val = False


def _kick():
    k = T().op('kick_out')
    if k is None:
        return False
    try:
        c = k['count'].eval()
    except Exception:
        return False
    hit = _S['last_count'] is not None and c > _S['last_count']
    _S['last_count'] = c
    return hit


def _status(msg=None, force=False):
    par = getattr(T().par, 'Seqstatus', None)
    if par is None:
        return
    t = now()
    if not force and msg is None and t - _S['last_status'] < 0.25:
        return
    _S['last_status'] = t
    if msg is None:
        if _S['playing']:
            el = t - _S['step_t0']
            msg = 'giro %d · scena %d/%d · %s · %.0f/%.0f s' % (
                _S['cycle'] + 1, _S['pos'] + 1, len(_S['order']),
                _S['name'], min(el, _S['dur']), _S['dur'])
            if _p('Seqhold', False):
                msg += ' · in pausa'
        else:
            msg = 'fermo'
    par.val = msg
    tot = getattr(T().par, 'Seqtotal', None)
    if tot is not None:
        secs = sum(r[1] for r in _rows()) * _p('Seqscale', 1.0)
        tot.val = '%d:%02d (±%d%%)' % (int(secs // 60), int(secs % 60),
                                       int(_p('Seqjitter', 0.0) * 100))


# ---------------- comandi dal pannello ----------------
def _commands():
    q = T().op('seq_cmd')
    if q is None or not q.text.strip():
        return
    txt = q.text
    q.text = ''
    for line in txt.splitlines():
        cmd, _, arg = line.partition('\t')
        cmd, arg = cmd.strip(), arg.strip()
        if cmd == 'save' and arg:
            data = load_all()
            data[arg] = snapshot()
            save_all(data)
            par = getattr(T().par, 'Presetlist', None)
            if par is not None:
                par.val = arg
            print('[timeline] preset salvato:', arg)
        elif cmd == 'delete' and arg:
            data = load_all()
            if data.pop(arg, None) is not None:
                save_all(data)
                print('[timeline] preset eliminato:', arg)
        elif cmd == 'load' and arg:
            tgt = _target(arg, random.Random(), 0.0)
            if tgt is None:
                _warn('preset "%s" non trovato' % arg)
            else:
                start_transition(tgt, _p('Presettransition', 2.0))
        elif cmd == 'next':
            _goto(_S['pos'] + 1)
            _S['playing'] = bool(_p('Seqplay', False))
        elif cmd == 'prev':
            _goto(_S['pos'] - 1)
            _S['playing'] = bool(_p('Seqplay', False))
        elif cmd == 'restart':
            _S.update(cycle=0, order=[])
            _goto(0)
            _S['playing'] = bool(_p('Seqplay', False))
        elif cmd == 'starters':
            make_starters()
        elif cmd == 'refresh':
            refresh_menu()


def onFrameStart(frame):
    try:
        _commands()
        t = now()
        last = _S['last_now'] if _S['last_now'] is not None else t
        _S['last_now'] = t
        hit = _kick()

        if _S['trans_active']:
            k = 1.0 if _S['trans'] <= 0 else min(1.0, (t - _S['trans_t0']) / _S['trans'])
            _apply(k)

        playing = bool(_p('Seqplay', False))
        if playing and not _S['playing']:
            _S.update(playing=True, cycle=0, order=[])
            _goto(0)
        elif not playing and _S['playing']:
            _S['playing'] = False

        if _S['playing']:
            if _p('Seqhold', False):
                _S['step_t0'] += t - last          # il tempo della scena si ferma
            else:
                el = t - _S['step_t0']
                if el >= _S['dur']:
                    waiting = (_p('Seqkicksync', False) and not hit
                               and el < _S['dur'] + KICK_WAIT_MAX)
                    if not waiting:
                        _goto(_S['pos'] + 1)
        _status()
    except Exception as e:
        _warn('errore: %r' % (e,))
    return


# ---- callback non usati ----
def onStart(*args):
    return

def onCreate(*args):
    return

def onExit(*args):
    return

def onFrameEnd(*args):
    return

def onPlayStateChange(*args):
    return

def onDeviceChange(*args):
    return

def onProjectPreSave(*args):
    return

def onProjectPostSave(*args):
    return
'''
    SEQUI = r'''# seq_ui — pulsanti delle pagine Presets e Timeline


def _cmd(comp, line):
    q = comp.op('seq_cmd')
    if q is not None:
        q.text = (q.text + '\n' if q.text else '') + line


def _open(d):
    if d is None:
        return
    try:
        d.par.edit.pulse()
    except Exception:
        d.openViewer()


def onPulse(par):
    c = par.owner
    n = par.name
    if n == 'Presetsave':
        name = c.par.Presetname.eval().strip() or 'preset'
        _cmd(c, 'save\t' + name)
    elif n == 'Presetload':
        _cmd(c, 'load\t' + c.par.Presetlist.eval())
    elif n == 'Presetdelete':
        _cmd(c, 'delete\t' + c.par.Presetlist.eval())
    elif n == 'Presetstarters':
        _cmd(c, 'starters')
    elif n == 'Seqnext':
        _cmd(c, 'next')
    elif n == 'Seqprev':
        _cmd(c, 'prev')
    elif n == 'Seqrestart':
        _cmd(c, 'restart')
    elif n == 'Editpresets':
        _open(c.op('presets_json'))
    elif n == 'Editsequence':
        _open(c.op('sequence'))
    return


def onValueChange(par, prev):
    return


def onExpressionChange(*args):
    return

def onExportChange(*args):
    return

def onEnableChange(*args):
    return

def onModeChange(*args):
    return
'''

    def say(*a):
        print('[timeline]', *a)

    def sp(o, **kw):
        for k, v in kw.items():
            p = getattr(o.par, k, None)
            if p is None:
                say('!! %s: parametro "%s" inesistente' % (o.name, k))
                continue
            try:
                p.val = v
            except Exception as e:
                say('!! %s.%s = %r non accettato (%s)' % (o.name, k, v, e))

    def page_of(C, name):
        for pg in C.customPages:
            if pg.name == name:
                return pg
        return C.appendCustomPage(name)

    def add(page, kind, name, label, default=None, lo=None, hi=None, menu=None):
        C = page.owner
        if getattr(C.par, name, None) is not None:
            return getattr(C.par, name)
        if kind == 'f':
            page.appendFloat(name, label=label)
        elif kind == 'i':
            page.appendInt(name, label=label)
        elif kind == 't':
            page.appendToggle(name, label=label)
        elif kind == 'm':
            page.appendMenu(name, label=label)
        elif kind == 's':
            page.appendStr(name, label=label)
        elif kind == 'p':
            page.appendPulse(name, label=label)
            return getattr(C.par, name)
        p = getattr(C.par, name)
        if kind == 'm':
            p.menuNames = [m[0] for m in menu]
            p.menuLabels = [m[1] for m in menu]
        if default is not None:
            p.default = default
            p.val = default
        if lo is not None:
            p.normMin, p.normMax = lo, hi
        return p

    try:
        C = op(COMP)
        if C is None:
            say('non trovo', COMP)
            return

        # ---------- pagina Presets ----------
        pg = page_of(C, 'Presets')
        add(pg, 's', 'Presetname', 'Nome del nuovo preset', 'scena')
        add(pg, 'p', 'Presetsave', 'Salva lo stato attuale')
        add(pg, 'm', 'Presetlist', 'Preset', '-', menu=[('-', '-')])
        add(pg, 'p', 'Presetload', 'Richiama preset')
        add(pg, 'f', 'Presettransition', 'Transizione richiamo (s)', 2.0, 0, 20)
        add(pg, 'p', 'Presetdelete', 'Elimina preset selezionato')
        add(pg, 'p', 'Presetstarters', 'Ricrea i preset d\'esempio')
        add(pg, 'p', 'Editpresets', 'Apri i preset (JSON)')
        add(pg, 's', 'Fluxcomp', 'Componente flux', '../flux')

        # ---------- pagina Timeline ----------
        pg = page_of(C, 'Timeline')
        add(pg, 't', 'Seqplay', 'Play', False)
        add(pg, 't', 'Seqhold', 'Pausa (tieni la scena)', False)
        add(pg, 'p', 'Seqnext', 'Scena successiva')
        add(pg, 'p', 'Seqprev', 'Scena precedente')
        add(pg, 'p', 'Seqrestart', 'Ricomincia')
        st = add(pg, 's', 'Seqstatus', 'Stato', 'fermo')
        tt = add(pg, 's', 'Seqtotal', 'Durata di un giro', '')
        for p in (st, tt):
            try:
                p.readOnly = True
            except Exception:
                pass
        add(pg, 't', 'Seqloop', 'Ripeti', True)
        add(pg, 'm', 'Seqorder', 'Ordine', 'list',
            menu=[('list', 'In fila'), ('shuffle', 'Mescolato'),
                  ('weighted', 'Casuale pesato')])
        add(pg, 'i', 'Seqseed', 'Seme (stesso seme = stessa sequenza)', 1, 0, 999)
        add(pg, 't', 'Seqvary', 'Ordine e variazioni nuovi a ogni giro', True)
        add(pg, 'f', 'Seqscale', 'Durate: moltiplicatore', 1.0, 0.1, 5)
        add(pg, 'f', 'Seqjitter', 'Durate: variazione ±', 0.2, 0, 0.9)
        add(pg, 'f', 'Seqtransscale', 'Transizioni: moltiplicatore', 1.0, 0, 5)
        add(pg, 'f', 'Seqvariation', 'Variazione dei valori ±', 0.1, 0, 0.5)
        add(pg, 't', 'Seqkicksync', 'Cambia scena sul kick', False)
        add(pg, 'p', 'Editsequence', 'Modifica la sequenza')

        # ---------- DAT ----------
        br = C.op('brain')
        bx, by = (br.nodeX, br.nodeY) if br is not None else (0, 0)
        x0, y0 = bx - 700, by + 300

        pj = C.op('presets_json')
        if pj is None:
            pj = C.create(textDAT, 'presets_json')
            pj.nodeX, pj.nodeY = x0, y0
            pj.text = '{}'
        seq = C.op('sequence')
        if seq is None:
            seq = C.create(tableDAT, 'sequence')
            seq.nodeX, seq.nodeY = x0 + 175, y0
            seq.clear()
            for row in (['preset', 'durata', 'transizione', 'peso'],
                        ['base', 20, 3, 1], ['taglio', 15, 2, 1],
                        ['rarefatto', 20, 4, 1], ['flux', 25, 3, 1],
                        ['denso', 15, 2, 1]):
                seq.appendRow(row)
            say('creata la sequenza d\'esempio')
        q = C.op('seq_cmd')
        if q is None:
            q = C.create(textDAT, 'seq_cmd')
            q.nodeX, q.nodeY = x0 + 350, y0
        q.text = ''

        eng = C.op('seq_engine')
        if eng is None:
            eng = C.create(executeDAT, 'seq_engine')
            eng.nodeX, eng.nodeY = x0, y0 - 150
        eng.text = ENGINE
        for p in ('start', 'create', 'exit', 'frameend', 'playstatechange',
                  'devicechange', 'projectpresave', 'projectpostsave'):
            if getattr(eng.par, p, None) is not None:
                setattr(eng.par, p, False)
        sp(eng, framestart=True, active=True)

        ui_ = C.op('seq_ui')
        if ui_ is None:
            ui_ = C.create(parameterexecuteDAT, 'seq_ui')
            ui_.nodeX, ui_.nodeY = x0 + 175, y0 - 150
        ui_.text = SEQUI
        sp(ui_, op=C.path, pars='Preset* Seq* Editpresets Editsequence')
        for p, v in (('custom', True), ('builtin', False), ('valuechange', False),
                     ('onpulse', True), ('expressionchange', False),
                     ('exportchange', False), ('enablechange', False),
                     ('modechange', False), ('active', True)):
            if getattr(ui_.par, p, None) is not None:
                sp(ui_, **{p: v})

        # preset d'esempio al primo avvio (li crea il motore dallo stato attuale)
        try:
            empty = not pj.text.strip() or pj.text.strip() == '{}'
        except Exception:
            empty = True
        q.text = 'refresh' + ('\nstarters' if empty else '')
        if empty:
            say('i 5 preset d\'esempio vengono creati al prossimo frame')

        try:
            names = [p.name for p in C.customPages]
            order = [n for n in ('Timeline', 'Presets', 'Layers', 'Cut', 'Sources', 'Live',
                                 'Text', 'Motion', 'Look', 'Output', 'Texttt') if n in names]
            C.sortCustomPages(*order)
        except Exception:
            pass
        say('pronto: pagine Timeline e Presets')
    except Exception:
        print('[timeline] ERRORE:')
        traceback.print_exc()


timeline_setup()