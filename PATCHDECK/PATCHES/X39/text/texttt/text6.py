# =============================================================
#  UI TEXTTT — pagine di controllo per /project1/texttt
#  Incolla in un Text DAT (NON dentro texttt) -> Run Script
#  Rilanciabile: i parametri già esistenti mantengono i tuoi valori.
#  Log nel Textport: le righe "!!" sono da controllare.
# =============================================================

def ui_texttt():
    import traceback

    COMP = '/project1/texttt'
    W, H = 1280, 720

    BRAIN = r'''# brain v5 — kick adattivo + testo controllato dai parametri UI
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
    prob = _par('Phraseprob', 0.18)
    return random.choice(PHRASES) if random.random() < prob else code_line()


def _scroll(name):
    buf = _S['buf'].get(name)
    if buf is None:
        buf = _S['buf'][name] = [any_line() for _ in range(SCROLL_LINES)]
    for _ in range(max(0, int(_par('Scrollchanges', SCROLL_CHANGES)))):
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


LAYER_PARS = {
    'text1':       ('Text1to2d', 'Text1to3d'),
    'text_phrase': ('Phraseto2d', 'Phraseto3d'),
    'text2':       ('Text2to2d', 'Text2to3d'),
    'text3':       ('Text3to2d', 'Text3to3d'),
}


def _on(name):
    a, b = LAYER_PARS.get(name, (None, None))
    return bool(_par(a, True)) or bool(_par(b, True))


def _every(name, default):
    return max(1, int(_par(name, default)))


def _clamp(v):
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def _text(t):
    if _par('Freeze', False):
        return

    if _on(BLOCK_TOP) and t % _every('Blockevery', BLOCK_EVERY) == 0:
        o = _get(BLOCK_TOP)
        if o is not None:
            n = max(1, int(_par('Blocklines', BLOCK_LINES)))
            o.par.text = SEP.join(any_line() for _ in range(n))

    if _on(PHRASE_TOP) and t % _every('Phraseevery', PHRASE_EVERY) == 0:
        o = _get(PHRASE_TOP)
        if o is not None:
            o.par.text = random.choice(PHRASES)

    if t % _every('Scrollevery', SCROLL_EVERY) == 0:
        for name in SCROLL_TOPS:
            if not _on(name):
                continue
            o = _get(name)
            if o is not None:
                o.par.text = _scroll(name)

    if _on(COLOR_TOP) and t % COLOR_EVERY == 0:
        o = _get(COLOR_TOP)
        if o is not None:
            r = _par('Color1r', 0.56)
            g = _par('Color1g', 0.88)
            b = _par('Color1b', 0.40)
            if _par('Colorcycle', True):
                amt = 0.3
                r = _clamp(r + (random.random() - 0.5) * amt)
                g = _clamp(g + (random.random() - 0.5) * amt)
                b = _clamp(b + (random.random() - 0.5) * amt)
            o.par.fontcolorr = r
            o.par.fontcolorg = g
            o.par.fontcolorb = b


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

        # ---------- brain ----------
        b = o('brain')
        b.text = BRAIN
        sp(b, framestart=True, active=True)
        say('brain aggiornato (v5)')

        try:
            C.sortCustomPages('Layers', 'Text', 'Motion', 'Look', 'Texttt')
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