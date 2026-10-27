# =============================================================
#  PATCH KICK — rilevazione adattiva per /project1/texttt
#  Incolla in un Text DAT (NON dentro texttt) -> Run Script
# =============================================================

def patch_kick():
    import traceback
    COMP = '/project1/texttt'

    BRAIN = r'''# brain v4 — contatore interno (la timeline che riparte non blocca piu' i kick)
import random
import numpy

# ---------- testo ----------
BLOCK_TOP, PHRASE_TOP = 'text1', 'text_phrase'
SCROLL_TOPS, COLOR_TOP = ['text2', 'text3'], 'text1'
BLOCK_EVERY, BLOCK_LINES = 8, 42
PHRASE_EVERY = 90
SCROLL_EVERY, SCROLL_LINES, SCROLL_CHANGES = 4, 80, 5
COLOR_EVERY = 4

KEYWORDS  = ['let', 'const', 'if', 'for', 'return', 'while']
FUNCS     = ['Math.sin', 'noise', 'fbm', 'hash2', 'sqrt']
VARS      = ['x', 'y', 'dx', 'dy', 'pts', 'time', 'speed', 'index', 'buffer']
OPERATORS = ['+', '-', '*', '/', '=', '=>', '&&', '||']
SYMBOLS   = ['{', '}', '(', ')', '[', ']', ';']
PHRASES = [
    "if (state !== 'awake') return 'Am I awake?';",
    "const dream = query('Is it a dream?');",
    "let reality = check('is this reality?');",
    "look(); breath(); think();",
    "feelFree();",
    "haveNoRegrets();",
    "while (depth < \u221e) deeper();",
    "feel(); feel(); feel();",
    "rage(); rage();",
    "lightBreaksWhereNoSunShines();",
]
SEP = '\\n'

# ---------- kick / pose ----------
POSES   = [(0.0, 90.0, 0.0), (-60.0, -40.0, -40.0), (90.0, 0.0, 110.0)]
ATTRACT = (1.0, 1.5)
HOLD_FRAMES = 8      # minimo distacco tra due kick
HISTORY = 120        # frame di storia per la mediana (~2 s)
AUTO_EVERY = 30      # Autokick: un kick ogni N frame

from collections import deque
_S = {'tick': 0, 'buf': {}, 'warned': set(), 'armed': True, 'last': -999,
      'count': 0, 'pose': 0, 'att': 0, 'hist': deque(maxlen=HISTORY)}


def _get(name):
    o = me.parent().op(name)
    if o is None and name not in _S['warned']:
        _S['warned'].add(name)
        print('[brain] non trovo', name)
    return o


def _par(name, default):
    p = getattr(me.parent().par, name, None)
    return p.eval() if p is not None else default


def code_line():
    parts = []
    for _ in range(random.randint(6, 15)):
        r = random.random()
        if r < 0.15:
            parts.append(random.choice(KEYWORDS))
        elif r < 0.30:
            parts.append(random.choice(FUNCS))
        elif r < 0.60:
            parts.append(random.choice(VARS))
        elif r < 0.75:
            parts.append('%0.2f' % random.uniform(0, 100))
        elif r < 0.90:
            parts.append(random.choice(OPERATORS))
        else:
            parts.append(random.choice(SYMBOLS))
    return '   '.join(parts)


def any_line():
    return random.choice(PHRASES) if random.random() < 0.18 else code_line()


def _scroll(name):
    buf = _S['buf'].get(name)
    if buf is None:
        buf = _S['buf'][name] = [any_line() for _ in range(SCROLL_LINES)]
    for _ in range(SCROLL_CHANGES):
        buf[random.randrange(SCROLL_LINES)] = any_line()
    return SEP.join(buf)


def _level():
    a = _get('audio_lp')
    if a is None or a.numChans == 0 or a.numSamples == 0:
        return 0.0
    arr = a.numpyArray()
    return float(numpy.sqrt(numpy.mean(arr * arr)))


def _audio(frame):
    lvl = _level() * _par('Gain', 1.0)
    sens = _par('Sensitivity', 1.5)
    floor = _par('Floor', 0.002)

    hist = _S['hist']
    hist.append(lvl)
    base = float(numpy.median(hist))        # la mediana ignora i picchi
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
        print('[brain] level %.4f  soglia %.4f  kick %d'
              % (lvl, trig, _S['count']))


def _text(frame):
    if frame % BLOCK_EVERY == 0:
        t = _get(BLOCK_TOP)
        if t is not None:
            t.par.text = SEP.join(any_line() for _ in range(BLOCK_LINES))
    if frame % PHRASE_EVERY == 0:
        t = _get(PHRASE_TOP)
        if t is not None:
            t.par.text = random.choice(PHRASES)
    if frame % SCROLL_EVERY == 0:
        for name in SCROLL_TOPS:
            t = _get(name)
            if t is not None:
                t.par.text = _scroll(name)
    if frame % COLOR_EVERY == 0:
        t = _get(COLOR_TOP)
        if t is not None:
            t.par.fontcolorr = 0.4 + random.random() * 0.3
            t.par.fontcolorg = 0.8 + random.random() * 0.2
            t.par.fontcolorb = 0.2 + random.random() * 0.3


def onFrameStart(frame):
    # 'frame' e' il frame della timeline e ricomincia a ogni loop:
    # uso un contatore interno che cresce sempre
    _S['tick'] += 1
    t = _S['tick']
    try:
        _audio(t)
    except Exception as e:
        key = 'audio:' + type(e).__name__
        if key not in _S['warned']:
            _S['warned'].add(key)
            print('[brain] errore audio:', repr(e))
    _text(t)
    return
'''

    def say(*a):
        print('[patch]', *a)

    try:
        C = op(COMP)
        if C is None:
            say('non trovo', COMP)
            return

        # nuovi parametri
        page = None
        for pg in C.customPages:
            if pg.name == 'Texttt':
                page = pg
        if page is None:
            page = C.appendCustomPage('Texttt')
        for name, label, kind, val, lo, hi in (
                ('Sensitivity', 'Kick sensitivity (x media)', 'f', 1.5, 1.0, 4.0),
                ('Floor', 'Kick min level', 'f', 0.002, 0.0, 0.1),
                ('Debug', 'Print levels', 't', False, None, None),
                ('Autokick', 'Autokick (test)', 't', False, None, None)):
            if getattr(C.par, name, None) is None:
                if kind == 'f':
                    page.appendFloat(name, label=label)
                else:
                    page.appendToggle(name, label=label)
                p = getattr(C.par, name)
                p.default = val
                p.val = val
                if lo is not None:
                    p.normMin, p.normMax = lo, hi
                say('aggiunto parametro', name)

        sp_ = getattr(C.par, 'Sensitivity', None)
        if sp_ is not None:
            sp_.default = 1.6
            if abs(sp_.eval() - 1.5) < 1e-6:
                sp_.val = 1.6

        # Threshold non serve più: lo nascondo
        th = getattr(C.par, 'Threshold', None)
        if th is not None:
            th.enable = False

        k = C.op('kick_out')
        if k is not None:
            k.par.const3name = 'trigger'
            say('kick_out: canali level / pulse / count / trigger')

        b = C.op('brain')
        if b is None:
            say('non trovo brain in', COMP)
            return
        b.text = BRAIN
        b.par.framestart = True
        b.par.active = True
        say('brain aggiornato (v4: contatore interno)')

        # diagnosi rapida
        lp = C.op('audio_lp')
        if lp is None:
            say('!! manca audio_lp')
        else:
            src = lp.inputs[0].name if lp.inputs else None
            say('audio_lp: ingresso =', src, '| canali =', lp.numChans,
                '| sample/frame =', lp.numSamples)
            if lp.numChans:
                import numpy
                arr = lp.numpyArray()
                say('audio_lp: livello RMS adesso = %.5f'
                    % float(numpy.sqrt(numpy.mean(arr * arr))))
        say('fatto. Attiva "Debug" su', COMP, 'per vedere i livelli nel Textport')

    except Exception:
        print('[patch] ERRORE:')
        traceback.print_exc()


patch_kick()