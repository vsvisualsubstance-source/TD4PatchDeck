# brain v6 - kick adattivo + testo generativo con i tuoi testi
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
SCROLL_TOPS, COLOR_TOP = ['text2'], 'text1'
THOUGHT_TOP = 'text3'  # pensiero/voce: un solo testo alla volta, mai ripetuto su piu' righe
BLOCK_EVERY, BLOCK_LINES = 8, 42
PHRASE_EVERY = 90

# ---------- sync dati Gaia -> pool 'mine' (src_text1/2/3) ----------
# Rispecchia i DAT live di Gaia dentro i pool 'mine' cosi' 'brain' pesca
# frasi vere (non piu' i semi poetici originali) per i primi 3 blocchi.
# Ogni riga sorgente (script*.rows()[i][0]) = una frase candidata nel pool.
GAIA_SYNC = {
    'src_text1': ['../../data/script_detections'],
    'src_text2': ['../../data/script_detections'],
    'src_text3': ['../../data/script_lexicondream'],
    'src_phrase': ['../../data/script_detections', '../../data/script_lexicondream'],
}
NO_SHARED = {'text1', 'text2', 'text3', 'text_phrase'}  # solo dati Gaia, niente pool condiviso (src_all/poesie)
SCROLL_EVERY, SCROLL_LINES, SCROLL_CHANGES = 4, 80, 5
COLOR_EVERY = 4
SEP = '\\n'   # backslash-n letterale (Text TOP con legacyparsing)

KEYWORDS  = ['let', 'const', 'if', 'for', 'return', 'while']
FUNCS     = ['Math.sin', 'noise', 'fbm', 'hash2', 'sqrt']
VARS      = ['x', 'y', 'dx', 'dy', 'pts', 'time', 'speed', 'index', 'buffer']
OPERATORS = ['+', '-', '*', '/', '=', '=>', '&&', '||']
SYMBOLS   = ['{', '}', '(', ')', '[', ']', ';']
DEFAULT_CODE_PHRASES = ["while (depth < âˆž) deeper();", "feelFree();"]

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
    """testi del livello + testi comuni (esclusi per i livelli Gaia, vedi NO_SHARED)"""
    a = _read(LAYERS[layer][3])
    b = None if layer in NO_SHARED else _read(SHARED_DAT)
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


def _split2(s):
    """Spezza una frase in 2 righe, tagliando allo spazio piu' vicino al centro."""
    mid = len(s) // 2
    left = s.rfind(' ', 0, mid)
    right = s.find(' ', mid)
    if left == -1 and right == -1:
        return s
    if left == -1:
        cut = right
    elif right == -1:
        cut = left
    else:
        cut = left if (mid - left) <= (right - mid) else right
    return s[:cut] + SEP + s[cut + 1:]


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


def _sync_gaia():
    """Rispecchia i DAT live di Gaia dentro i pool 'mine' (src_text1/2/3/phrase)."""
    for dst_name, src_paths in GAIA_SYNC.items():
        dst = me.parent().op(dst_name)
        if dst is None:
            continue
        lines = []
        for src_path in src_paths:
            src = me.parent().op(src_path)
            if src is None:
                continue
            try:
                lines.extend(r[0].val for r in src.rows() if r[0].val.strip())
            except Exception as e:
                key = 'gaia_sync:' + dst_name
                if key not in _S['warned']:
                    _S['warned'].add(key)
                    print('[brain] errore sync gaia', dst_name, repr(e))
        text = '\n'.join(lines)
        # non svuotare il pool durante un vuoto momentaneo del sensore Gaia:
        # un pool vuoto fa ricadere line_for() sul codice generato (brutto).
        # tieni l'ultimo contenuto buono finche' non arriva un nuovo valore.
        if text and dst.text != text:
            dst.text = text


def _text(t):
    _sync_gaia()
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

    if _on(THOUGHT_TOP) and _due(THOUGHT_TOP, 'Scrollevery', SCROLL_EVERY, t):
        o = _get(THOUGHT_TOP)
        if o is not None:
            c = _pool(THOUGHT_TOP)
            held = _held(THOUGHT_TOP, t)
            if held:
                o.par.text = _split2(held[-1][0])
            elif c and c['lines']:
                o.par.text = _split2(c['lines'][0])

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


# ---- callback non usati: presenti cosi' nessun toggle genera errori ----
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
