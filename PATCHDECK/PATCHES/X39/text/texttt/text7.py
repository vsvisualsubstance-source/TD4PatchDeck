# =============================================================
#  UI TEXTTT v2 — pagine di controllo + testi tuoi per /project1/texttt
#  Incolla in un Text DAT (NON dentro texttt) -> Run Script
#  Rilanciabile: i parametri già esistenti mantengono i tuoi valori.
#  Log nel Textport: le righe "!!" sono da controllare.
# =============================================================

def ui_texttt():
    import traceback

    COMP = '/project1/texttt'
    W, H = 1280, 720

    BRAIN = r'''# brain v6 — kick adattivo + testo generativo con i tuoi testi
import random
import re
import numpy
from collections import deque

# ---------- livelli ----------
# TOP: (par sorgente, par 2D, par 3D, DAT testi del livello)
LAYERS = {
    'text1':       ('Mode1',      'Text1to2d',  'Text1to3d',  'src_text1'),
    'text_phrase': ('Modephrase', 'Phraseto2d', 'Phraseto3d', 'src_phrase'),
    'text2':       ('Mode2',      'Text2to2d',  'Text2to3d',  'src_text2'),
    'text3':       ('Mode3',      'Text3to2d',  'Text3to3d',  'src_text3'),
}
TARGETS = {'all': list(LAYERS), 'text1': ['text1'], 'phrase': ['text_phrase'],
           'text2': ['text2'], 'text3': ['text3']}
SHARED_DAT, CODE_DAT, QUEUE_DAT = 'src_all', 'code_phrases', 'inject_queue'
BLOCK_TOP, PHRASE_TOP = 'text1', 'text_phrase'
SCROLL_TOPS, COLOR_TOP = ['text2', 'text3'], 'text1'
BLOCK_EVERY, BLOCK_LINES = 8, 42
PHRASE_EVERY = 90
SCROLL_EVERY, SCROLL_LINES, SCROLL_CHANGES = 4, 80, 5
COLOR_EVERY = 4
SEP = '\\n'   # backslash-n letterale (Text TOP con legacyparsing)

KEYWORDS  = ['let', 'const', 'if', 'for', 'return', 'while']
FUNCS     = ['Math.sin', 'noise', 'fbm', 'hash2', 'sqrt']
VARS      = ['x', 'y', 'dx', 'dy', 'pts', 'time', 'speed', 'index', 'buffer']
OPERATORS = ['+', '-', '*', '/', '=', '=>', '&&', '||']
SYMBOLS   = ['{', '}', '(', ')', '[', ']', ';']
DEFAULT_CODE_PHRASES = ["while (depth < \u221e) deeper();", "feelFree();"]

# ---------- kick / pose ----------
POSES   = [(0.0, 90.0, 0.0), (-60.0, -40.0, -40.0), (90.0, 0.0, 110.0)]
ATTRACT = (1.0, 1.5)
HOLD_FRAMES = 8
HISTORY = 120
AUTO_EVERY = 30

_S = {'tick': 0, 'buf': {}, 'warned': set(), 'armed': True, 'last': -999,
      'count': 0, 'pose': 0, 'att': 0, 'hist': deque(maxlen=HISTORY),
      'src': {}, 'merged': {}, 'held': {k: [] for k in LAYERS}, 'force': set()}


def _get(name):
    o = me.parent().op(name)
    if o is None and name not in _S['warned']:
        _S['warned'].add(name)
        print('[brain] non trovo', name)
    return o


def _par(name, default):
    p = getattr(me.parent().par, name, None) if name else None
    return p.eval() if p is not None else default


def _rate():
    try:
        return float(me.time.rate)
    except Exception:
        return 60.0


# ================= SORGENTI DI TESTO =================
def _clean(s):
    return s.replace('\\', '/').replace('\t', ' ').strip()


def _read(dat_name):
    d = me.parent().op(dat_name)
    if d is None:
        return None
    txt = d.text
    c = _S['src'].get(dat_name)
    if c is not None and c['text'] == txt:
        return c
    lines = [_clean(l) for l in txt.splitlines()]
    lines = [l for l in lines if l and not l.startswith('#')]
    c = {'text': txt, 'lines': lines}
    _S['src'][dat_name] = c
    return c


def _build(lines):
    words, chain, starts = [], {}, []
    for l in lines:
        ws = l.split()
        if not ws:
            continue
        words.extend(ws)
        starts.append(ws[0])
        for a, b in zip(ws, ws[1:]):
            chain.setdefault(a, []).append(b)
    return {'lines': lines, 'words': words, 'chain': chain, 'starts': starts}


def _pool(layer):
    """testi del livello + testi comuni"""
    a = _read(LAYERS[layer][3])
    b = _read(SHARED_DAT)
    ta = a['text'] if a else ''
    tb = b['text'] if b else ''
    m = _S['merged'].get(layer)
    if m is None or m['key'] != (ta, tb):
        lines = (a['lines'] if a else []) + (b['lines'] if b else [])
        m = _build(lines)
        m['key'] = (ta, tb)
        _S['merged'][layer] = m
    return m if m['lines'] else None


def _code_phrases():
    c = _read(CODE_DAT)
    return c['lines'] if c and c['lines'] else DEFAULT_CODE_PHRASES


def _ident(w):
    w = re.sub(r'\W+', '_', w.lower()).strip('_')
    return w or 'x'


# ================= GENERATORI =================
def code_line(words=None):
    parts = []
    for _ in range(random.randint(6, 15)):
        r = random.random()
        if r < 0.15:
            parts.append(random.choice(KEYWORDS))
        elif r < 0.30:
            parts.append(random.choice(FUNCS))
        elif r < 0.60:
            if words and random.random() < 0.7:
                parts.append(_ident(random.choice(words)))
            else:
                parts.append(random.choice(VARS))
        elif r < 0.75:
            parts.append('%0.2f' % random.uniform(0, 100))
        elif r < 0.90:
            parts.append(random.choice(OPERATORS))
        else:
            parts.append(random.choice(SYMBOLS))
    return '   '.join(parts)


def any_line(words=None):
    if random.random() < _par('Phraseprob', 0.18):
        return random.choice(_code_phrases())
    return code_line(words)


def cutup(c):
    return ' '.join(random.choice(c['words']) for _ in range(random.randint(3, 9)))


def markov(c):
    w = random.choice(c['starts'])
    out = [w]
    for _ in range(random.randint(3, 14)):
        nxt = c['chain'].get(w)
        if not nxt:
            break
        w = random.choice(nxt)
        out.append(w)
    return ' '.join(out)


def line_for(layer, phrase=False):
    mode = _par(LAYERS[layer][0], 'code')
    c = _pool(layer) if mode != 'code' else None
    code = (lambda: random.choice(_code_phrases())) if phrase else any_line
    if c is None:
        return code()
    if mode == 'words':
        return code_line(c['words']) if not phrase else _ident_phrase(c)
    if mode == 'mine':
        return random.choice(c['lines'])
    own = {'mix': lambda: random.choice(c['lines']),
           'cutup': lambda: cutup(c),
           'markov': lambda: markov(c)}.get(mode)
    if own is None:
        return code()
    return own() if random.random() < _par('Mix', 0.35) else code()


def _ident_phrase(c):
    w = _ident(random.choice(c['words']))
    return random.choice(['%s();', 'let %s = feel();', 'while (%s) deeper();',
                          'if (!%s) return;', 'const %s = query();']) % w


# ================= TESTO IN DIRETTA =================
def _process_queue(t):
    d = me.parent().op(QUEUE_DAT)
    if d is None:
        return
    txt = d.text
    if not txt.strip():
        return
    d.text = ''
    hold = int(_par('Injecthold', 5.0) * _rate())
    for raw in txt.splitlines():
        target, msg = raw.split('\t', 1) if '\t' in raw else ('all', raw)
        msg = _clean(msg)
        if not msg:
            continue
        for layer in TARGETS.get(target.strip(), list(LAYERS)):
            _S['held'][layer].append([msg, t + hold, None])
            _S['force'].add(layer)


def _held(layer, t):
    lst = [h for h in _S['held'][layer] if h[1] > t]
    _S['held'][layer] = lst
    return lst


def inject(msg, target='all'):
    """utile dal Textport: op('.../brain').module.inject('ciao')"""
    d = me.parent().op(QUEUE_DAT)
    if d is not None:
        d.text = (d.text + '\n' if d.text else '') + target + '\t' + msg


# ================= KICK =================
def _level():
    a = _get('audio_lp')
    if a is None or a.numChans == 0 or a.numSamples == 0:
        return 0.0
    arr = a.numpyArray()
    return float(numpy.sqrt(numpy.mean(arr * arr)))


def _audio(frame):
    lvl = _level() * _par('Gain', 1.0)
    sens = _par('Sensitivity', 1.6)
    floor = _par('Floor', 0.002)
    hist = _S['hist']
    hist.append(lvl)
    base = float(numpy.median(hist))
    trig = max(base * sens, floor)

    auto = _par('Autokick', False) and frame - _S['last'] >= AUTO_EVERY
    hit = False
    if auto or (_S['armed'] and lvl > trig and frame - _S['last'] >= HOLD_FRAMES):
        hit = True
        _S['armed'] = False
        _S['last'] = frame
        _S['count'] += 1
        _S['pose'] = (_S['pose'] + 1) % len(POSES)
        _S['att'] = 1 - _S['att']
    elif lvl < max(base * (1 + (sens - 1) * 0.5), floor):
        _S['armed'] = True

    k = _get('kick_out')
    if k is not None:
        k.par.const0value = lvl
        k.par.const1value = 1.0 if hit else 0.0
        k.par.const2value = _S['count']
        k.par.const3value = trig

    p = _get('pose')
    if p is not None:
        rx, ry, rz = POSES[_S['pose']]
        p.par.const0value = rx
        p.par.const1value = ry
        p.par.const2value = rz
        p.par.const3value = ATTRACT[_S['att']]

    if _par('Debug', False) and frame % 30 == 0:
        print('[brain] level %.4f  soglia %.4f  kick %d' % (lvl, trig, _S['count']))


# ================= AGGIORNAMENTO TESTI =================
def _on(layer):
    _, a, b, _d = LAYERS[layer]
    return bool(_par(a, True)) or bool(_par(b, True))


def _due(layer, every_par, default, t):
    if layer in _S['force']:
        _S['force'].discard(layer)
        return True
    return t % max(1, int(_par(every_par, default))) == 0


def _clamp(v):
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def _scroll(name, t):
    buf = _S['buf'].get(name)
    if buf is None:
        buf = _S['buf'][name] = [line_for(name) for _ in range(SCROLL_LINES)]
    protected = set()
    for h in _held(name, t):
        if h[2] is None:
            h[2] = random.randrange(SCROLL_LINES)
            buf[h[2]] = h[0]
        protected.add(h[2])
    for _ in range(max(0, int(_par('Scrollchanges', SCROLL_CHANGES)))):
        i = random.randrange(SCROLL_LINES)
        if i not in protected:
            buf[i] = line_for(name)
    return SEP.join(buf)


def _text(t):
    _process_queue(t)
    if _par('Freeze', False):
        return

    if _on(BLOCK_TOP) and _due(BLOCK_TOP, 'Blockevery', BLOCK_EVERY, t):
        o = _get(BLOCK_TOP)
        if o is not None:
            n = max(1, int(_par('Blocklines', BLOCK_LINES)))
            lines = [line_for(BLOCK_TOP) for _ in range(n)]
            for h in _held(BLOCK_TOP, t):
                lines[random.randrange(n)] = h[0]
            o.par.text = SEP.join(lines)

    if _on(PHRASE_TOP) and _due(PHRASE_TOP, 'Phraseevery', PHRASE_EVERY, t):
        o = _get(PHRASE_TOP)
        if o is not None:
            held = _held(PHRASE_TOP, t)
            o.par.text = held[-1][0] if held else line_for(PHRASE_TOP, phrase=True)

    for name in SCROLL_TOPS:
        if _on(name) and _due(name, 'Scrollevery', SCROLL_EVERY, t):
            o = _get(name)
            if o is not None:
                o.par.text = _scroll(name, t)

    if _on(COLOR_TOP) and t % COLOR_EVERY == 0:
        o = _get(COLOR_TOP)
        if o is not None:
            r = _par('Color1r', 0.56)
            g = _par('Color1g', 0.88)
            b = _par('Color1b', 0.40)
            if _par('Colorcycle', True):
                r = _clamp(r + (random.random() - 0.5) * 0.3)
                g = _clamp(g + (random.random() - 0.5) * 0.3)
                b = _clamp(b + (random.random() - 0.5) * 0.3)
            o.par.fontcolorr = r
            o.par.fontcolorg = g
            o.par.fontcolorb = b


def onFrameStart(frame):
    _S['tick'] += 1
    t = _S['tick']
    try:
        _audio(t)
    except Exception as e:
        key = 'audio:' + type(e).__name__
        if key not in _S['warned']:
            _S['warned'].add(key)
            print('[brain] errore audio:', repr(e))
    try:
        _text(t)
    except Exception as e:
        key = 'text:' + type(e).__name__
        if key not in _S['warned']:
            _S['warned'].add(key)
            print('[brain] errore testo:', repr(e))
    return


# ---- callback non usati: presenti così nessun toggle genera errori ----
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

    UIEXEC = r'''# ui_exec — pulsanti e campo "Testo live" del pannello texttt
EDIT = {'Editall': 'src_all', 'Edit1': 'src_text1', 'Editphrase': 'src_phrase',
        'Edit2': 'src_text2', 'Edit3': 'src_text3', 'Editcode': 'code_phrases'}
KEEP = {'all': 'src_all', 'text1': 'src_text1', 'phrase': 'src_phrase',
        'text2': 'src_text2', 'text3': 'src_text3'}


def _send(comp):
    msg = comp.par.Inject.eval().strip()
    if not msg:
        return
    target = comp.par.Injectto.eval()
    q = comp.op('inject_queue')
    if q is not None:
        q.text = (q.text + '\n' if q.text else '') + target + '\t' + msg
    if comp.par.Injectkeep.eval():
        d = comp.op(KEEP.get(target, 'src_all'))
        if d is not None:
            d.text = d.text.rstrip('\n') + '\n' + msg
    if comp.par.Injectclear.eval():
        comp.par.Inject.val = ''


def onPulse(par):
    comp = par.owner
    if par.name == 'Send':
        _send(comp)
    elif par.name in EDIT:
        d = comp.op(EDIT[par.name])
        if d is not None:
            try:
                d.par.edit.pulse()
            except Exception:
                d.openViewer()
    return


def onValueChange(par, prev):
    if par.name == 'Inject' and par.eval().strip():
        _send(par.owner)
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

    issues = []

    def say(*a):
        print('[ui]', *a)

    def warn(msg):
        issues.append(msg)
        print('[ui] !!', msg)

    # ---------- helper rete ----------
    def get_or_make(C, optype, name, x, y):
        o = C.op(name)
        if o is None:
            o = C.create(optype, name)
            o.nodeX, o.nodeY = x, y
        return o

    def sp(o, **kw):
        for k, v in kw.items():
            p = getattr(o.par, k, None)
            if p is None:
                warn('%s: parametro "%s" inesistente' % (o.name, k))
                continue
            try:
                p.val = v
            except Exception as e:
                warn('%s.%s = %r non accettato (%s)' % (o.name, k, v, e))

    def ex(o, **kw):
        for k, e in kw.items():
            p = getattr(o.par, k, None)
            if p is None:
                warn('%s: parametro "%s" inesistente' % (o.name, k))
                continue
            try:
                p.expr = e
                p.mode = ParMode.EXPRESSION
            except Exception as err:
                warn('%s.%s expr non accettata (%s)' % (o.name, k, err))

    def set_inputs(dst, srcs):
        for c in list(dst.inputConnectors):
            if c.connections:
                c.disconnect()
        for i, s in enumerate(srcs):
            try:
                dst.inputConnectors[i].connect(s)
            except Exception:
                try:
                    s.outputConnectors[0].connect(dst)
                except Exception as e:
                    warn('collegamento %s -> %s[%d] fallito (%s)' % (s.name, dst.name, i, e))

    # ---------- helper parametri ----------
    def page_of(C, name):
        for pg in C.customPages:
            if pg.name == name:
                return pg
        return C.appendCustomPage(name)

    def add(page, kind, name, label, default, lo=None, hi=None, menu=None):
        C = page.owner
        if kind == 'rgb':
            exists = getattr(C.par, name + 'r', None) is not None
        else:
            exists = getattr(C.par, name, None) is not None
        if exists:
            return
        try:
            if kind == 'f':
                page.appendFloat(name, label=label)
            elif kind == 'i':
                page.appendInt(name, label=label)
            elif kind == 't':
                page.appendToggle(name, label=label)
            elif kind == 'm':
                page.appendMenu(name, label=label)
            elif kind == 'rgb':
                page.appendRGB(name, label=label)
            elif kind == 's':
                page.appendStr(name, label=label)
            elif kind == 'p':
                page.appendPulse(name, label=label)
                return
        except Exception as e:
            warn('parametro %s non creato (%s)' % (name, e))
            return
        if kind == 'rgb':
            for suffix, v in zip('rgb', default):
                p = getattr(C.par, name + suffix)
                p.default = v
                p.val = v
            return
        p = getattr(C.par, name)
        if kind == 'm':
            p.menuNames = [m[0] for m in menu]
            p.menuLabels = [m[1] for m in menu]
        p.default = default
        p.val = default
        if lo is not None:
            p.normMin, p.normMax = lo, hi

    BLENDS = [('difference', 'Difference'), ('add', 'Add'),
              ('screen', 'Screen'), ('maximum', 'Maximum'), ('over', 'Over')]

    try:
        C = op(COMP)
        if C is None:
            say('non trovo', COMP)
            return

        # ================= PARAMETRI =================
        pg = page_of(C, 'Layers')
        add(pg, 't', 'Text1to2d',  'Text 1 (blocco) 2D', True)
        add(pg, 't', 'Text1to3d',  'Text 1 (blocco) 3D', True)
        add(pg, 't', 'Phraseto2d', 'Frase 2D', True)
        add(pg, 't', 'Phraseto3d', 'Frase 3D', True)
        add(pg, 't', 'Text2to2d',  'Text 2 (scroll giallo) 2D', True)
        add(pg, 't', 'Text2to3d',  'Text 2 (scroll giallo) 3D', True)
        add(pg, 't', 'Text3to2d',  'Text 3 (scroll azzurro) 2D', True)
        add(pg, 't', 'Text3to3d',  'Text 3 (scroll azzurro) 3D', True)
        add(pg, 't', 'Show3d',     'Livello 3D (render)', True)

        pg = page_of(C, 'Text')
        add(pg, 't', 'Freeze',        'Congela testo', False)
        add(pg, 'i', 'Blockevery',    'Text 1: nuovo blocco ogni N frame', 8, 1, 60)
        add(pg, 'i', 'Blocklines',    'Text 1: righe', 42, 1, 80)
        add(pg, 'i', 'Phraseevery',   'Frase: nuova ogni N frame', 90, 1, 600)
        add(pg, 'i', 'Scrollevery',   'Text 2/3: aggiorna ogni N frame', 4, 1, 60)
        add(pg, 'i', 'Scrollchanges', 'Text 2/3: righe cambiate', 5, 0, 40)
        add(pg, 'f', 'Phraseprob',    'Probabilità frasi', 0.18, 0, 1)
        add(pg, 'f', 'Size1',         'Text 1 dimensione', 28, 4, 120)
        add(pg, 'f', 'Sizephrase',    'Frase dimensione', 28, 4, 200)
        add(pg, 'f', 'Size2',         'Text 2 dimensione', 19.4, 4, 120)
        add(pg, 'f', 'Size3',         'Text 3 dimensione', 18, 4, 120)
        add(pg, 'rgb', 'Color1',      'Text 1 colore', (0.56, 0.88, 0.40))
        add(pg, 't', 'Colorcycle',    'Text 1 colore variabile', True)
        add(pg, 'rgb', 'Colorphrase', 'Frase colore', (1.0, 0.0, 0.0))
        add(pg, 'rgb', 'Color2',      'Text 2 colore', (0.91, 1.0, 0.0))
        add(pg, 'rgb', 'Color3',      'Text 3 colore', (0.0, 0.73, 1.0))

        pg = page_of(C, 'Motion')
        add(pg, 'f', 'Lfo1freq',    'Frase A velocità (LFO1)', 0.2, 0, 3)
        add(pg, 'f', 'Lfo2freq',    'Frase B / Text 2 velocità (LFO2)', 0.56, 0, 3)
        add(pg, 'f', 'Lfo4freq',    'Mirror Y ritmo (LFO4)', 0.18, 0, 3)
        add(pg, 'f', 'Phrasescale', 'Frase A scala', 2.0, 0.1, 6)
        add(pg, 'f', 'Text2scale',  'Text 2 scala', 3.0, 0.1, 6)

        pg = page_of(C, 'Look')
        add(pg, 'm', 'Blend2d',    'Fusione testi', 'difference', menu=BLENDS)
        add(pg, 'm', 'Blendfinal', 'Fusione 2D + 3D', 'difference', menu=BLENDS)
        add(pg, 'f', 'Geoscale',   '3D scala', 2.5, 0.1, 10)
        add(pg, 'f', 'Zspread',    '3D distanza tra strati', 1.0, 0, 10)
        add(pg, 'f', 'Brightness', '3D luminosità', 1.99, 0, 5)
        add(pg, 'f', 'Contrast',   '3D contrasto', 2.3, 0, 5)
        MODES = [('code', 'Solo pseudo-codice'),
                 ('words', 'Codice con le tue parole'),
                 ('mine', 'Solo i tuoi testi'),
                 ('mix', 'Tuoi testi + codice'),
                 ('cutup', 'Cut-up + codice'),
                 ('markov', 'Markov + codice')]
        pg = page_of(C, 'Sources')
        add(pg, 'm', 'Mode1',      'Text 1 sorgente', 'words', menu=MODES)
        add(pg, 'm', 'Modephrase', 'Frase sorgente', 'mix', menu=MODES)
        add(pg, 'm', 'Mode2',      'Text 2 sorgente', 'mix', menu=MODES)
        add(pg, 'm', 'Mode3',      'Text 3 sorgente', 'cutup', menu=MODES)
        add(pg, 'f', 'Mix',        'Quota tuoi testi (modi +codice)', 0.35, 0, 1)
        add(pg, 'p', 'Editall',    'Modifica testi comuni', None)
        add(pg, 'p', 'Edit1',      'Modifica testi Text 1', None)
        add(pg, 'p', 'Editphrase', 'Modifica testi Frase', None)
        add(pg, 'p', 'Edit2',      'Modifica testi Text 2', None)
        add(pg, 'p', 'Edit3',      'Modifica testi Text 3', None)
        add(pg, 'p', 'Editcode',   'Modifica frasi-codice', None)

        pg = page_of(C, 'Live')
        add(pg, 's', 'Inject',      'Testo live (Invio = manda)', '')
        add(pg, 'm', 'Injectto',    'Destinazione', 'all',
            menu=[('all', 'Tutti i livelli'), ('text1', 'Text 1'),
                  ('phrase', 'Frase'), ('text2', 'Text 2'), ('text3', 'Text 3')])
        add(pg, 'p', 'Send',        'Invia di nuovo', None)
        add(pg, 'f', 'Injecthold',  'Resta visibile (secondi)', 5.0, 0.5, 30)
        add(pg, 't', 'Injectkeep',  'Aggiungi anche ai testi salvati', False)
        add(pg, 't', 'Injectclear', 'Svuota il campo dopo l\'invio', True)
        say('parametri pronti')

        # ================= RETE =================
        need = ['text1', 'text_phrase', 'text2', 'text3', 'xf1', 'xf2', 'xf3',
                'comp_add', 'comp_diff', 'mirror', 'final', 'geo', 'level',
                'lfo1', 'lfo2', 'lfo4', 'brain',
                'low1', 'low2', 'low3', 'low4',
                'zoff1', 'zoff2', 'zoff3', 'zoff4']
        missing = [n for n in need if C.op(n) is None]
        if missing:
            say('!! mancano', missing, '- rilancia build_texttt.py prima')
            return
        o = C.op

        blank = get_or_make(C, constantTOP, 'blank',
                            o('comp_diff').nodeX, o('comp_diff').nodeY - 400)
        sp(blank, colorr=0, colorg=0, colorb=0, alpha=0,
           resolutionw=W, resolutionh=H)

        # sorgente di ogni livello testo (come in build_texttt)
        layers = [  # nome switch, sorgente, par 2D, par 3D, low che alimenta
            ('text1',  o('xf1'),       'Text1to2d',  'Text1to3d',  'low3'),
            ('phrase', o('comp_add'),  'Phraseto2d', 'Phraseto3d', 'low4'),
            ('text2',  o('xf3'),       'Text2to2d',  'Text2to3d',  'low2'),
            ('text3',  o('text3'),     'Text3to2d',  'Text3to3d',  'low1'),
        ]
        sw2d = {}
        for key, src, p2, p3, low in layers:
            a = get_or_make(C, switchTOP, 'sw2d_' + key, src.nodeX + 175, src.nodeY + 60)
            set_inputs(a, [blank, src])
            ex(a, index="1 if parent().par.%s else 0" % p2)
            sw2d[key] = a

            b = get_or_make(C, switchTOP, 'sw3d_' + key, src.nodeX + 175, src.nodeY - 60)
            set_inputs(b, [blank, src])
            ex(b, index="1 if parent().par.%s else 0" % p3)
            set_inputs(o(low), [b])

        # stesso ordine di prima: frase, text1, text2, text3
        set_inputs(o('comp_diff'), [sw2d['phrase'], sw2d['text1'],
                                    sw2d['text2'], sw2d['text3']])

        sw3 = get_or_make(C, switchTOP, 'sw_3d',
                          o('mirror').nodeX + 175, o('mirror').nodeY)
        set_inputs(sw3, [blank, o('mirror')])
        ex(sw3, index="1 if parent().par.Show3d else 0")
        set_inputs(o('final'), [o('comp_diff'), sw3])
        say('switch dei livelli collegati (i livelli spenti non vengono calcolati)')

        # ---------- espressioni ----------
        for n, s in (('text1', 'Size1'), ('text_phrase', 'Sizephrase'),
                     ('text2', 'Size2'), ('text3', 'Size3')):
            ex(o(n), fontsizex='parent().par.' + s)
        ex(o('text2'), fontsizey='parent().par.Size2 * 0.747')
        for n, c in (('text_phrase', 'Colorphrase'), ('text2', 'Color2'),
                     ('text3', 'Color3')):
            ex(o(n), fontcolorr='parent().par.%sr' % c,
               fontcolorg='parent().par.%sg' % c,
               fontcolorb='parent().par.%sb' % c)

        ex(o('lfo1'), frequency='parent().par.Lfo1freq')
        ex(o('lfo2'), frequency='parent().par.Lfo2freq')
        ex(o('lfo4'), frequency='parent().par.Lfo4freq')
        ex(o('xf2'), sx='parent().par.Phrasescale', sy='parent().par.Phrasescale')
        ex(o('xf3'), sx='parent().par.Text2scale', sy='parent().par.Text2scale')

        ex(o('comp_diff'), operand='parent().par.Blend2d')
        ex(o('final'), operand='parent().par.Blendfinal')
        ex(o('geo'), scale='parent().par.Geoscale')
        ex(o('level'), brightness1='parent().par.Brightness',
           contrast='parent().par.Contrast')
        for i, z in enumerate((0.0, 0.2, 0.3, 0.15)):
            ex(o('zoff%d' % (i + 1)), tz='%s * parent().par.Zspread' % z)
        say('espressioni collegate')

        # ---------- DAT dei testi ----------
        bx, by = o('brain').nodeX, o('brain').nodeY
        SRC = [
            ('src_all', '# TESTI COMUNI - una riga = una frase (le righe con # sono ignorate)\n'
                        '# valgono per tutti i livelli, in aggiunta ai testi del livello\n'
                        'il segnale non è il messaggio\n'
                        'ogni riga è un respiro\n'
                        'la macchina sogna in frammenti\n'
                        'ascolto il rumore sotto il silenzio\n'
                        'quello che resta è la traccia\n'
                        'scrivo per non dimenticare di esistere\n'),
            ('src_text1', '# testi solo per Text 1 (blocco verde)\n'),
            ('src_phrase', '# testi solo per la Frase (rossa)\n'),
            ('src_text2', '# testi solo per Text 2 (scroll giallo)\n'),
            ('src_text3', '# testi solo per Text 3 (scroll azzurro)\n'),
            ('code_phrases', '# frasi-codice che compaiono tra lo pseudo-codice\n'
                             + '\n'.join([
                                 "if (state !== 'awake') return 'Am I awake?';",
                                 "const dream = query('Is it a dream?');",
                                 "let reality = check('is this reality?');",
                                 "look(); breath(); think();",
                                 "feelFree();",
                                 "haveNoRegrets();",
                                 "while (depth < \u221e) deeper();",
                                 "feel(); feel(); feel();",
                                 "rage(); rage();",
                                 "lightBreaksWhereNoSunShines();"]) + '\n'),
            ('inject_queue', ''),
        ]
        for i, (name, default) in enumerate(SRC):
            if C.op(name) is None:
                d = C.create(textDAT, name)
                d.nodeX, d.nodeY = bx + 200 + i * 175, by
                d.text = default
                say('creato', name)
        o('inject_queue').text = ''

        ue = get_or_make(C, parameterexecuteDAT, 'ui_exec', bx, by - 150)
        ue.text = UIEXEC
        sp(ue, op=C.path, pars='Inject Send Edit*')
        for p, v in (('custom', True), ('builtin', False), ('valuechange', True),
                     ('onpulse', True), ('expressionchange', False),
                     ('exportchange', False), ('enablechange', False),
                     ('modechange', False), ('active', True)):
            if getattr(ue.par, p, None) is not None:
                sp(ue, **{p: v})
        say('ui_exec pronto (Invia / Modifica)')

        # ---------- brain ----------
        b = o('brain')
        b.text = BRAIN
        for p in ('start', 'create', 'exit', 'frameend', 'playstatechange',
                  'devicechange', 'projectpresave', 'projectpostsave'):
            if getattr(b.par, p, None) is not None:
                setattr(b.par, p, False)
        sp(b, framestart=True, active=True)
        say('brain aggiornato (v6: testi tuoi + live)')

        try:
            C.sortCustomPages('Layers', 'Sources', 'Live', 'Text', 'Motion', 'Look', 'Texttt')
        except Exception:
            pass
        try:
            C.openParameters()
        except Exception:
            pass

        say('fatto. Problemi da controllare: %d' % len(issues))
        for i in issues:
            say('  -', i)

    except Exception:
        print('[ui] ERRORE:')
        traceback.print_exc()


ui_texttt()