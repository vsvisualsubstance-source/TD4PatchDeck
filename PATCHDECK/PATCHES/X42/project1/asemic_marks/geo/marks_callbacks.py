
# Tre famiglie di segni: asemica (gesto scritto), geometrica (figura
# regolare) e testuale (font a tratto singolo). Ogni segno e' fatto di
# una o piu' polilinee con colore per punto: l'alpha porta la dissolvenza.

import colorsys
import math
import random

marks = []
state = {'t': 0.0, 'since': 0.0, 'seed': None, 'armed': True,
         'lastspawn': -9.0, 'textidx': 0, 'pan': 0.0, 'bright': 0.5}


def onSetupParameters(scriptOp):
    # Senza input niente obbligherebbe il SOP a ricuocere: la dipendenza
    # da absTime.frame la crea.
    try:
        p = scriptOp.appendCustomPage('Cook').appendFloat('Frame')[0]
        p.expr = 'absTime.frame'
    except Exception as err:
        debug('marks: cook per frame non impostato -> %s' % err)
    return


def par(b, name, default=0.0):
    """Lettura tollerante: se un parametro manca il segno nasce comunque."""
    try:
        return float(getattr(b.par, name))
    except Exception:
        return default


# ---------- value noise ----------

def _hash(n):
    n = (int(n) << 13) ^ int(n)
    return 1.0 - ((n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff) / 1073741824.0


def vnoise(x, seed=0):
    i = int(math.floor(x))
    f = x - i
    f = f * f * (3.0 - 2.0 * f)
    a = _hash(i + seed * 57)
    b = _hash(i + 1 + seed * 57)
    return a + (b - a) * f


# ---------- Catmull-Rom ----------

def smooth(pts, sub, closed):
    if sub <= 1 or len(pts) < 3:
        return pts
    n = len(pts)
    out = []
    span = n if closed else n - 1
    for i in range(span):
        p0 = pts[(i - 1) % n] if closed else pts[max(i - 1, 0)]
        p1 = pts[i % n]
        p2 = pts[(i + 1) % n] if closed else pts[min(i + 1, n - 1)]
        p3 = pts[(i + 2) % n] if closed else pts[min(i + 2, n - 1)]
        for s in range(sub):
            t = s / float(sub)
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    if not closed:
        out.append(pts[-1])
    return out


# ---------- colore del singolo segno ----------

def rgb(b, name, default=(1.0, 1.0, 1.0)):
    return (par(b, name + 'r', default[0]),
            par(b, name + 'g', default[1]),
            par(b, name + 'b', default[2]))


def jitter(col, amt):
    """Variazione per segno in HSV. Un colore quasi bianco non ha tinta
    da spostare, quindi in quel caso ne viene introdotta un po'."""
    if amt <= 0.0:
        return col
    r, g, bl = [max(0.0, min(1.0, c)) for c in col]
    h, sat, val = colorsys.rgb_to_hsv(r, g, bl)
    h = (h + random.uniform(-1.0, 1.0) * amt * 0.12) % 1.0
    if sat < 0.05:
        sat = random.uniform(0.0, amt * 0.25)
    else:
        sat = sat * (1.0 + random.uniform(-1.0, 1.0) * amt * 0.5)
    val = val * (1.0 + random.uniform(-1.0, 1.0) * amt * 0.45)
    sat = max(0.0, min(1.0, sat))
    val = max(0.05, min(1.0, val))
    return colorsys.hsv_to_rgb(h, sat, val)


def palette_at(b, t):
    """Punto lungo la palette a 4 colori. La dispersione dice quanto il
    singolo segno puo' allontanarsi dal punto indicato: a 0 la palette e'
    una scala rigida, a 1 il colore e' libero e resta solo una tendenza."""
    cols = [rgb(b, 'Pal%d' % i) for i in range(1, 5)]
    last = len(cols) - 1
    t = max(0.0, min(1.0, t)) * last
    t += random.uniform(-1.0, 1.0) * par(b, 'Palspread', 0.35) * last
    t = max(0.0, min(float(last), t))
    i0 = int(t)
    i1 = min(i0 + 1, last)
    f = t - i0
    return tuple(cols[i0][k] + (cols[i1][k] - cols[i0][k]) * f for k in range(3))


def mark_color(b, e, fam):
    """Il colore viene deciso alla nascita e resta col segno per tutta
    la sua vita: cambiare modo non ridipinge quelli gia' in scena."""
    try:
        mode = str(b.par.Colormode)
    except Exception:
        mode = 'single'

    base_col = rgb(b, 'Inkcolor')

    if mode == 'family':
        if fam == 'geo':
            return rgb(b, 'Geocolor', (0.55, 0.85, 1.0))
        if fam == 'text':
            return rgb(b, 'Textcolor', (1.0, 0.82, 0.35))
        return base_col

    if mode == 'palette':
        return jitter(rgb(b, 'Pal%d' % random.randint(1, 4)),
                      par(b, 'Paljitter', 0.15))

    if mode == 'palenergy':
        return jitter(palette_at(b, e), par(b, 'Paljitter', 0.15))

    if mode == 'pitch':
        # Stessa scala, ma percorsa dal registro invece che dal volume:
        # Palette 1 sui gravi, Palette 4 sugli acuti.
        return jitter(palette_at(b, state['bright']), par(b, 'Paljitter', 0.15))

    if mode == 'energy':
        hi = rgb(b, 'Hicolor', (1.0, 0.35, 0.18))
        t = max(0.0, min(1.0, e))
        return tuple(base_col[i] + (hi[i] - base_col[i]) * t for i in range(3))

    if mode == 'random':
        h = random.random()
        s_ = max(0.0, min(1.0, par(b, 'Randsat', 0.6)))
        v = max(0.0, min(1.0, par(b, 'Randval', 1.0)))
        return colorsys.hsv_to_rgb(h, s_, v)

    return base_col


# ---------- rotazione asse-angolo (Rodrigues) ----------

def axis_matrix(axis, ang):
    # L'asse va normalizzato qui: con un asse non unitario la matrice
    # non e' ortonormale e scala il segno mentre lo ruota.
    x, y, z = axis
    n = math.sqrt(x * x + y * y + z * z)
    if n < 1e-9:
        return (1., 0., 0., 0., 1., 0., 0., 0., 1.)
    x, y, z = x / n, y / n, z / n
    c = math.cos(ang)
    s = math.sin(ang)
    t = 1.0 - c
    return (t * x * x + c,     t * x * y - s * z, t * x * z + s * y,
            t * x * y + s * z, t * y * y + c,     t * y * z - s * x,
            t * x * z - s * y, t * y * z + s * x, t * z * z + c)


# ---------- famiglia asemica ----------

def g_walk(e, s, b):
    n = random.randint(6, 16)
    step = random.uniform(0.012, 0.032) * s * (0.7 + e * 0.7)
    a = random.uniform(0, math.tau)
    x = y = 0.0
    pts = []
    for _ in range(n):
        a += random.uniform(-1.1, 1.1)
        x += math.cos(a) * step
        y += math.sin(a) * step
        pts.append((x, y))
    return pts, False


def g_orbit(e, s, b):
    n = random.randint(5, 11)
    r = random.uniform(0.04, 0.14) * s * (0.8 + e * 0.7)
    start = random.uniform(0, math.tau)
    pts = []
    for i in range(n):
        a = start + math.tau / n * i + random.uniform(-0.25, 0.25)
        rr = r * random.uniform(0.55, 1.0)
        pts.append((math.cos(a) * rr, math.sin(a) * rr))
    return pts, True


def g_spiral(e, s, b):
    n = random.randint(18, 40)
    turns = random.uniform(1.2, 3.4)
    r = random.uniform(0.03, 0.12) * s * (0.8 + e)
    d = random.choice((1, -1))
    pts = []
    for i in range(n):
        t = i / float(n - 1)
        a = t * math.tau * turns * d
        rr = r * (0.12 + t * 0.88)
        pts.append((math.cos(a) * rr, math.sin(a) * rr))
    return pts, False


def g_ribbon(e, s, b):
    n = random.randint(14, 30)
    L = random.uniform(0.10, 0.34) * s * (0.6 + e * 0.9)
    a = random.uniform(0, math.tau)
    amp = random.uniform(0.01, 0.05) * s
    freq = random.uniform(1.5, 5.0)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for i in range(n):
        t = i / float(n - 1)
        u = (t - 0.5) * L
        v = math.sin(t * math.tau * freq) * amp * math.sin(t * math.pi)
        pts.append((u * ca - v * sa, u * sa + v * ca))
    return pts, False


def g_burst(e, s, b):
    n = random.randint(4, 9)
    r = random.uniform(0.03, 0.11) * s * (0.7 + e)
    start = random.uniform(0, math.tau)
    pts = []
    for i in range(n):
        a = start + math.tau / n * i
        pts.append((0.0, 0.0))
        pts.append((math.cos(a) * r * random.uniform(0.5, 1.0),
                    math.sin(a) * r * random.uniform(0.5, 1.0)))
    return pts, False


def g_glyph(e, s, b):
    cell = random.uniform(0.018, 0.05) * s
    x = y = 0.0
    pts = [(0.0, 0.0)]
    for _ in range(random.randint(4, 10)):
        if random.random() < 0.5:
            x += random.choice((-1, 1)) * cell * random.randint(1, 3)
        else:
            y += random.choice((-1, 1)) * cell * random.randint(1, 3)
        pts.append((x, y))
    return pts, False


# ---------- famiglia geometrica ----------
# Vertici regolari: la deformazione arriva solo dal wobble geometrico,
# che va tenuto basso perche' la figura resti riconoscibile.

def _ngon(sides, r, rot=0.0):
    return [(math.cos(rot + math.tau / sides * i) * r,
             math.sin(rot + math.tau / sides * i) * r)
            for i in range(sides)]


def g_circle(e, s, b):
    r = random.uniform(0.04, 0.13) * s * (0.8 + e * 0.6)
    return _ngon(48, r), True


def g_poly(e, s, b):
    sides = max(3, int(par(b, 'Polysides', 6)))
    r = random.uniform(0.04, 0.13) * s * (0.8 + e * 0.6)
    return _ngon(sides, r, random.uniform(0, math.tau)), True


def g_square(e, s, b):
    r = random.uniform(0.04, 0.12) * s * (0.8 + e * 0.6)
    return _ngon(4, r, random.choice((0.0, math.pi / 4))), True


def g_tri(e, s, b):
    r = random.uniform(0.05, 0.14) * s * (0.8 + e * 0.6)
    return _ngon(3, r, random.uniform(0, math.tau)), True


def g_arc(e, s, b):
    r = random.uniform(0.05, 0.16) * s * (0.8 + e * 0.6)
    start = random.uniform(0, math.tau)
    sweep = random.uniform(math.pi * 0.4, math.pi * 1.6)
    n = max(8, int(sweep / math.tau * 48))
    return [(math.cos(start + sweep * i / (n - 1.0)) * r,
             math.sin(start + sweep * i / (n - 1.0)) * r)
            for i in range(n)], False


def g_cross(e, s, b):
    r = random.uniform(0.03, 0.10) * s * (0.8 + e * 0.6)
    rot = random.uniform(0, math.tau)
    ca, sa = math.cos(rot), math.sin(rot)
    raw = [(-r, 0.0), (r, 0.0), (0.0, 0.0), (0.0, -r), (0.0, r)]
    return [(x * ca - y * sa, x * sa + y * ca) for x, y in raw], False


# ---------- famiglia testuale ----------
# Font a tratto singolo: ogni carattere e' una lista di polilinee su una
# griglia 4x6. Niente Text SOP, cosi' le lettere sono segni come gli
# altri e ricevono wobble e dissolvenza dalla stessa pipeline.
# Per aggiungere un carattere basta copiare lo schema di una lettera.

FONT = {
    ' ': [],
    'A': [[(0, 0), (2, 6), (4, 0)], [(0.8, 2.2), (3.2, 2.2)]],
    'B': [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)],
          [(3, 3), (4, 2), (4, 1), (3, 0), (0, 0)]],
    'C': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1)]],
    'D': [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 1), (3, 0), (0, 0)]],
    'E': [[(4, 6), (0, 6), (0, 0), (4, 0)], [(0, 3), (3, 3)]],
    'F': [[(4, 6), (0, 6), (0, 0)], [(0, 3), (3, 3)]],
    'G': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0),
           (4, 1), (4, 3), (2, 3)]],
    'H': [[(0, 6), (0, 0)], [(4, 6), (4, 0)], [(0, 3), (4, 3)]],
    'I': [[(1, 6), (3, 6)], [(2, 6), (2, 0)], [(1, 0), (3, 0)]],
    'J': [[(3, 6), (3, 1), (2, 0), (1, 0), (0, 1)]],
    'K': [[(0, 6), (0, 0)], [(4, 6), (0, 3), (4, 0)]],
    'L': [[(0, 6), (0, 0), (4, 0)]],
    'M': [[(0, 0), (0, 6), (2, 3), (4, 6), (4, 0)]],
    'N': [[(0, 0), (0, 6), (4, 0), (4, 6)]],
    'O': [[(1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6)]],
    'P': [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)]],
    'Q': [[(1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6)],
          [(2, 2), (4, 0)]],
    'R': [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)],
          [(2, 3), (4, 0)]],
    'S': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 4), (1, 3), (3, 3),
           (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)]],
    'T': [[(0, 6), (4, 6)], [(2, 6), (2, 0)]],
    'U': [[(0, 6), (0, 1), (1, 0), (3, 0), (4, 1), (4, 6)]],
    'V': [[(0, 6), (2, 0), (4, 6)]],
    'W': [[(0, 6), (1, 0), (2, 4), (3, 0), (4, 6)]],
    'X': [[(0, 6), (4, 0)], [(4, 6), (0, 0)]],
    'Y': [[(0, 6), (2, 3), (4, 6)], [(2, 3), (2, 0)]],
    'Z': [[(0, 6), (4, 6), (0, 0), (4, 0)]],
    '0': [[(1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6)],
          [(0, 1), (4, 5)]],
    '1': [[(1, 5), (2, 6), (2, 0)], [(1, 0), (3, 0)]],
    '2': [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (0, 0), (4, 0)]],
    '3': [[(0, 6), (4, 6), (2, 3.4), (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)]],
    '4': [[(3, 0), (3, 6), (0, 2), (4, 2)]],
    '5': [[(4, 6), (0, 6), (0, 3), (3, 3), (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)]],
    '6': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0),
           (4, 1), (4, 2), (3, 3), (1, 3), (0, 2)]],
    '7': [[(0, 6), (4, 6), (1, 0)]],
    '8': [[(1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3),
           (1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3)]],
    '9': [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6),
           (0, 5), (0, 4), (1, 3), (3, 3), (4, 4)]],
    '.': [[(1.8, 0), (2.2, 0)]],
    ',': [[(2.2, 1), (1.6, -0.6)]],
    '-': [[(1, 3), (3, 3)]],
    '/': [[(0, 0), (4, 6)]],
    "'": [[(2, 6), (2, 4.6)]],
    '!': [[(2, 6), (2, 1.6)], [(1.8, 0), (2.2, 0)]],
    '?': [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (2, 2.6), (2, 1.6)],
          [(1.8, 0), (2.2, 0)]],
    ':': [[(1.8, 4), (2.2, 4)], [(1.8, 1), (2.2, 1)]],
}


def _glyph(ch):
    return FONT.get(ch.upper(), FONT.get('?', []))


def g_text(e, s, b):
    """Restituisce una lista di polilinee: un carattere o una parola."""
    try:
        mode = str(b.par.Textmode)
    except Exception:
        mode = 'rand'
    try:
        src = str(b.par.Textstring)
    except Exception:
        src = ''

    if mode == 'word':
        txt = src if src else 'ASEMIC'
    elif mode == 'seq':
        pool = src if src else 'ASEMIC'
        txt = pool[state['textidx'] % len(pool)]
        state['textidx'] += 1
    else:
        pool = src if src else 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        txt = random.choice(pool)

    scale = 0.030 * s * par(b, 'Textsize', 1.0) * (0.8 + e * 0.5)
    adv = 5.0 * scale
    x0 = -adv * len(txt) * 0.5
    rot = random.uniform(-1, 1) * par(b, 'Textrotate', 0.0) * math.pi
    ca, sa = math.cos(rot), math.sin(rot)

    out = []
    for k, ch in enumerate(txt):
        ox = x0 + adv * k
        for stroke in _glyph(ch):
            pts = []
            for px, py in stroke:
                x = px * scale + ox
                y = (py - 3.0) * scale
                pts.append((x * ca - y * sa, x * sa + y * ca))
            if len(pts) >= 2:
                out.append((pts, False))
    return out


GENS = [('walk', g_walk, 'asemic'), ('orbit', g_orbit, 'asemic'),
        ('spiral', g_spiral, 'asemic'), ('ribbon', g_ribbon, 'asemic'),
        ('burst', g_burst, 'asemic'), ('glyph', g_glyph, 'asemic'),
        ('circle', g_circle, 'geo'), ('poly', g_poly, 'geo'),
        ('square', g_square, 'geo'), ('tri', g_tri, 'geo'),
        ('arc', g_arc, 'geo'), ('cross', g_cross, 'geo'),
        ('text', g_text, 'text')]


def pick(b):
    """Peso effettivo = peso x interruttore. Spento significa escluso."""
    entries = []
    tot = 0.0
    for key, fn, fam in GENS:
        try:
            on = 1.0 if int(getattr(b.par, 'On' + key)) else 0.0
        except Exception:
            on = 1.0 if key in ('walk', 'orbit') else 0.0
        w = max(0.0, par(b, 'W' + key, 0.0)) * on
        if w > 0:
            entries.append((w, fn, fam))
            tot += w
    if not entries:
        # Nessuna forma attiva: meglio un gesto che una scena vuota.
        return g_walk, 'asemic'
    r = random.random() * tot
    acc = 0.0
    for w, fn, fam in entries:
        acc += w
        if r <= acc:
            return fn, fam
    return entries[-1][1], entries[-1][2]


def as_strokes(res):
    """I generatori semplici tornano (punti, chiuso); quello testuale una
    lista di polilinee. Qui diventano tutti liste."""
    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[1], bool):
        return [res]
    return list(res)


def spawn(b, e, aspect):
    fn, fam = pick(b)
    strokes = as_strokes(fn(e, par(b, 'Size', 1.0), b))
    if not strokes:
        return

    # Il centro resta separato dai punti: cosi' il segno puo' ruotare su
    # se stesso invece che attorno all'origine della scena.
    # Aderenza 1: il segno nasce esattamente dove sta il suono nel campo
    # stereo. Aderenza 0: posizione libera. In mezzo, il pan e' una
    # tendenza e il resto e' dispersione.
    panmap = False
    try:
        panmap = bool(b.par.Panmap)
    except Exception:
        pass
    if panmap:
        k = max(0.0, min(1.0, par(b, 'Panspread', 0.7)))
        cx = state['pan'] * aspect * k + random.uniform(-1.0, 1.0) * aspect * (1.0 - k)
        cx = max(-aspect, min(aspect, cx))
    else:
        cx = random.uniform(-aspect, aspect)
    cy = random.uniform(-1.0, 1.0)
    cz = random.uniform(-1.0, 1.0) * par(b, 'Depth', 0.0)

    if fam == 'geo':
        amp_par = par(b, 'Geowobble', 0.008)
    elif fam == 'text':
        amp_par = par(b, 'Textwobble', 0.012)
    else:
        amp_par = par(b, 'Wobble', 0.03)

    items = []
    for pts, closed in strokes:
        items.append({
            'pts': list(pts),
            'closed': closed,
            'seeds': [random.randint(0, 9999) for _ in pts],
        })

    # Asse di rotazione casuale ma normalizzato, sbilanciato su X e Y:
    # attorno a Z il segno girerebbe soltanto nel piano, senza scorcio.
    ax, ay, az = (random.uniform(-1, 1), random.uniform(-1, 1),
                  random.uniform(-0.35, 0.35))
    n = math.sqrt(ax * ax + ay * ay + az * az) or 1.0

    marks.append({
        'strokes': items,
        'col': mark_color(b, e, fam),
        'centre': (cx, cy, cz),
        'axis': (ax / n, ay / n, az / n),
        'ang0': random.uniform(0, math.tau),
        'spin': random.uniform(0.4, 1.6) * random.choice((1.0, -1.0)),
        'life': 1.0,
        'ttl': max(0.05, random.uniform(par(b, 'Life1', 1.4), par(b, 'Life2', 2.8))),
        'amp': (0.4 + e) * amp_par,
        'phase': random.uniform(0, 500),
        'fam': fam,
    })


# ---------------------------- cook ----------------------------

def onCook(scriptOp):
    b = scriptOp.parent(2)
    scriptOp.clear()

    if state['seed'] != int(par(b, 'Seed', 1)):
        state['seed'] = int(par(b, 'Seed', 1))
        random.seed(state['seed'])

    now = absTime.seconds
    dt = (now - state['t']) if state['t'] else 0.0
    state['t'] = now
    dt = max(0.0, min(dt, 0.064))

    e = att = pan = 0.0
    ec = op('../energy_out')
    if ec:
        if len(ec.chans('energy')):
            e = float(ec['energy'])
        if len(ec.chans('attack')):
            att = float(ec['attack'])
        if len(ec.chans('pan')):
            pan = float(ec['pan'])
        if len(ec.chans('bright')):
            state['bright'] = float(ec['bright'])
    state['pan'] = pan
    tst = par(b, 'Testenergy', 0.0)
    if tst > e:
        e = tst

    rx = max(1, int(par(b, 'Resolution1', 1280)))
    ry = max(1, int(par(b, 'Resolution2', 720)))
    aspect = rx / float(ry)

    active = True
    try:
        active = bool(b.par.Active)
    except Exception:
        pass

    if not active:
        marks.clear()
    else:
        # Densita continua: e' la modalita' di base, sempre attiva.
        rate = e * e * 50.0 * par(b, 'Spawnrate', 1.0)
        if rate > 0:
            state['since'] += dt
            if state['since'] > 0.045 and random.random() < rate * dt:
                spawn(b, e, aspect)
                state['since'] = 0.0

        # Nascita su attacco: opzionale, si somma alla densita' continua.
        # Su pianoforte da' un segno per nota invece che una nuvola sulla
        # coda del suono; va acceso apposta.
        onset = False
        try:
            onset = bool(b.par.Onsetmode)
        except Exception:
            pass
        if onset:
            thr = par(b, 'Onsetthresh', 0.12)
            gap = par(b, 'Refractory', 90) / 1000.0
            if att < thr * 0.6:
                state['armed'] = True
            if state['armed'] and att >= thr and (now - state['lastspawn']) > gap:
                spawn(b, max(e, att), aspect)
                state['armed'] = False
                state['lastspawn'] = now

        while len(marks) > int(par(b, 'Maxmarks', 48)):
            marks.pop(0)

    ink = (par(b, 'Inkcolorr', 1.0), par(b, 'Inkcolorg', 1.0), par(b, 'Inkcolorb', 1.0))
    # i segni nati prima dell'introduzione del colore ricadono su ink
    wsp = par(b, 'Wobblespeed', 0.6)
    sub = int(par(b, 'Resample', 6))
    inka = max(0.0, min(1.0, par(b, 'Inkalpha', 1.0)))
    tum = par(b, 'Tumble', 0.0)
    tsp = par(b, 'Tumblespeed', 0.3)

    try:
        scriptOp.pointAttribs.create('Cd')
    except Exception:
        pass

    dead = []
    for idx, m in enumerate(marks):
        m['life'] -= dt / m['ttl']
        m['phase'] += dt * wsp
        if m['life'] <= 0.0:
            dead.append(idx)
            continue

        alpha = pow(max(m['life'], 0.0), 0.65) * inka
        col = m.get('col', ink)
        amp = m['amp']
        phase = m['phase']
        cx, cy, cz = m['centre']

        # A tumble 0 la matrice e' l'identita' e non si paga nulla.
        mat3 = None
        if tum > 0.0:
            ang = (m['ang0'] + now * m['spin'] * tsp) * tum
            mat3 = axis_matrix(m['axis'], ang)

        for st in m['strokes']:
            wob = []
            for i, (x, y) in enumerate(st['pts']):
                sd = st['seeds'][i]
                wob.append((x + vnoise(phase, sd) * amp,
                            y + vnoise(phase + 13.7, sd + 991) * amp))

            # Solo i gesti asemici vengono risuddivisi: figure e lettere
            # perderebbero gli spigoli che le rendono leggibili.
            pts = smooth(wob, sub, st['closed']) if m['fam'] == 'asemic' else wob
            if len(pts) < 2:
                continue

            poly = scriptOp.appendPoly(len(pts), closed=st['closed'], addPoints=True)
            for i, (x, y) in enumerate(pts):
                if mat3 is None:
                    px, py, pz = x, y, 0.0
                else:
                    a, bb, c, d, ee, f, g, h, k = mat3
                    px = a * x + bb * y
                    py = d * x + ee * y
                    pz = g * x + h * y
                poly[i].point.x = px + cx
                poly[i].point.y = py + cy
                poly[i].point.z = pz + cz
                try:
                    poly[i].point.Cd = (col[0], col[1], col[2], alpha)
                except Exception:
                    pass

    for i in reversed(dead):
        marks.pop(i)

    return
