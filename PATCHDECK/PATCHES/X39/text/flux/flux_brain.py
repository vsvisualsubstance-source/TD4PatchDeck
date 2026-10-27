# flux_brain v2 — velocità, kick, token (testi flux/texttt), live, glifo
import random
import re

K_WHITE = 16
QUEUE_DAT = 'inject_flux'
TEXTTT_DATS = ('src_all', 'src_text1', 'src_phrase', 'src_text2',
               'src_text3', 'code_phrases')
KEYWORDS = ['let', 'const', 'if', 'for', 'return', 'while', 'fn', 'var']
FUNCS    = ['sin()', 'noise()', 'fbm()', 'hash2()', 'sqrt()', 'emit()', 'flux()']
VARS     = ['x', 'y', 'dx', 'pts', 'time', 'idx', 'buf', 'zo', 'zz']
SYMBOLS  = ['{}', '()', '[]', ';', '=>', '&&', '||', '::', '/*', '*/', '?', '!=']

_S = {'tick': 0, 'd': 0.0, 'env': 0.0, 'last_count': None, 'last_kick': -999,
      'hero_t': None, 'sig': None, 'warned': set(), 'src_key': None,
      'units': [], 'pinned': {}}


def _p(name, default):
    p = getattr(me.parent().par, name, None)
    return p.eval() if p is not None else default


def _rate():
    try:
        return float(me.time.rate)
    except Exception:
        return 60.0


def _src():
    path = _p('Sourcecomp', '')
    return me.parent().op(path) if path else None


# ---------- testi ----------
def _texts():
    mode = _p('Fluxsource', 'both')
    texts = []
    if mode in ('own', 'both'):
        d = me.parent().op('src_flux')
        if d is not None:
            texts.append(d.text)
    if mode in ('texttt', 'both'):
        s = _src()
        if s is not None:
            for n in TEXTTT_DATS:
                d = s.op(n)
                if d is not None:
                    texts.append(d.text)
    return texts


def _units():
    texts = _texts()
    unit = _p('Tokenunit', 'word')
    key = (tuple(texts), unit)
    if key != _S['src_key']:
        lines = []
        for t in texts:
            for line in t.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    lines.append(line)
        if unit == 'line':
            units = lines
        elif unit == 'pair':
            units = []
            for l in lines:
                ws = l.split()
                if len(ws) == 1:
                    units.append(ws[0])
                for i in range(len(ws) - 1):
                    units.append(ws[i] + ' ' + ws[i + 1])
        else:
            units = [w for l in lines for w in re.split(r'\s+', l) if w]
        _S['units'] = units
        _S['src_key'] = key
    return _S['units']


def _glyph(lo=2, hi=6):
    chars = _p('Glyphs', 'ZO?1IXEAHK7#%=<>') or 'ZO?1'
    return ''.join(random.choice(chars) for _ in range(random.randint(lo, hi)))


def _code_token():
    r = random.random()
    if r < 0.2:
        return random.choice(KEYWORDS)
    if r < 0.35:
        return random.choice(FUNCS)
    if r < 0.5:
        return random.choice(VARS) + ' ' + random.choice(SYMBOLS)
    if r < 0.62:
        return '%0.2f' % random.uniform(0, 100)
    if r < 0.72:
        return '0x%02X' % random.randint(0, 255)
    if r < 0.82:
        return random.choice(SYMBOLS)
    return _glyph()


def _finish(tok):
    tok = tok.replace('\\', '/')
    return tok.upper() if _p('Uppercase', True) else tok


def make_token():
    mode = _p('Tokensource', 'mix')
    units = _units() if mode != 'code' else []
    if units and (mode == 'words' or (mode == 'mix' and random.random() < _p('Wordshare', 0.4))):
        tok = random.choice(units)
        limit = int(_p('Linechars', 24)) if _p('Tokenunit', 'word') == 'line' \
            else int(_p('Maxchars', 14))
        tok = tok[:max(1, limit)].rstrip()
    else:
        tok = _code_token()
    return _finish(tok)


def _set_token(i, text):
    t = me.parent().op('tok%d' % i)
    if t is not None:
        t.par.text = text


def _free_slots(t):
    return [i for i in range(K_WHITE) if _S['pinned'].get(i, 0) <= t]


def _refresh(n, t):
    free = _free_slots(t)
    for _ in range(n):
        if not free:
            return
        _set_token(random.choice(free), make_token())


def _launch_hero(text):
    _S['hero_t'] = 0
    h = me.parent().op('tok_hero')
    if h is not None:
        h.par.text = text


# ---------- live ----------
def _process_queue(t, rate):
    d = me.parent().op(QUEUE_DAT)
    if d is None:
        return
    txt = d.text
    if not txt.strip():
        return
    d.text = ''
    hold = int(_p('Injecthold', 5.0) * rate)
    for raw in txt.splitlines():
        target, msg = raw.split('\t', 1) if '\t' in raw else ('both', raw)
        msg = _finish(msg.strip())
        if not msg:
            continue
        target = target.strip()
        if target in ('tokens', 'both'):
            pieces = msg.split() if _p('Injectsplit', True) else [msg]
            n = max(len(pieces), int(_p('Injectslots', 4)))
            slots = _free_slots(t) or list(range(K_WHITE))
            random.shuffle(slots)
            for j, i in enumerate(slots[:n]):
                _set_token(i, pieces[j % len(pieces)])
                _S['pinned'][i] = t + hold
        if target in ('hero', 'both'):
            _launch_hero(msg)


# ---------- kick ----------
def _kicked(t):
    hit = False
    s = _src()
    if s is not None:
        k = s.op('kick_out')
        if k is not None and k.numChans >= 3:
            ch = k['count']
            if ch is not None:
                c = ch.eval()
                if _S['last_count'] is not None and c > _S['last_count']:
                    hit = True
                _S['last_count'] = c
    if _p('Autokick', False) and t - _S['last_kick'] >= int(_p('Autoevery', 30)):
        hit = True
    if hit:
        _S['last_kick'] = t
    return hit


# ---------- ciclo ----------
def _reseed_if_needed():
    sig = tuple(_p(n, 0) for n in ('Count', 'Depth', 'Near', 'Lanes', 'Width',
                                    'Height', 'Seed', 'Sizemin', 'Sizemax',
                                    'Bluefrac', 'Centerbias'))
    if sig != _S['sig']:
        _S['sig'] = sig
        s = me.parent().op('seeds')
        if s is not None:
            s.cook(force=True)


def onFrameStart(frame):
    _S['tick'] += 1
    t = _S['tick']
    rate = _rate()
    try:
        _reseed_if_needed()
        if t == 1:
            for i in range(K_WHITE):
                _set_token(i, make_token())
        _process_queue(t, rate)

        hit = _kicked(t)
        if hit:
            _S['env'] = 1.0
            _refresh(int(_p('Kickchanges', 6)), t)
            if _p('Heroon', True) and _S['hero_t'] is None:
                _launch_hero(_glyph(2, 3) if random.random() < 0.6 else make_token()[:6])
        else:
            _S['env'] *= _p('Envdecay', 0.9)

        every = max(1, int(_p('Tokenevery', 6)))
        if t % every == 0:
            _refresh(int(_p('Tokenchanges', 2)), t)

        depth = _p('Depth', 60.0)
        near = _p('Near', 4.5)
        span = depth + near
        speed = _p('Speed', 6.0) * (1.0 + _p('Kickboost', 3.0) * _S['env'])
        if _p('Pause', False):
            speed = 0.0
        _S['d'] = (_S['d'] + speed / rate) % span

        heroz, heros = -depth, 0.0
        if _S['hero_t'] is not None:
            _S['hero_t'] += 1
            dur = max(1.0, _p('Herotime', 1.2) * rate)
            prog = _S['hero_t'] / dur
            if prog >= 1.0:
                _S['hero_t'] = None
            else:
                heroz = -depth + (prog ** 2) * (span + 2.0)
                heros = _p('Heroscale', 1.5)

        tr = me.parent().op('travel')
        if tr is not None:
            tr.par.const0value = _S['d']
            tr.par.const1value = _S['env']
            tr.par.const2value = heroz
            tr.par.const3value = heros
    except Exception as e:
        key = type(e).__name__ + str(e)[:40]
        if key not in _S['warned']:
            _S['warned'].add(key)
            print('[flux_brain] errore:', repr(e))
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
