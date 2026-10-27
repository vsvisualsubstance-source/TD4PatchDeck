"""
build_asemic.py  —  v19
-------------------------------------------------------------------
Costruisce /project1/asemic_marks: segni asemici audioreattivi in
TouchDesigner, porting dello sketch p5.

Uso: nuovo Text DAT -> incolla -> tasto destro -> Run Script.
Rilanciarlo ricostruisce la rete da zero, rileggendo e riapplicando
i parametri custom (non perdi la taratura).

Build 2025.33070 / macOS.

Correzioni rispetto alle versioni precedenti:
 - Cd creato senza valore di default (e' un attributo standard)
 - lettura audio sul massimo di tutti i canali, senza numSamples
 - riuso del DAT di callback creato in automatico dallo Script OP
 - Fondo salita a 0 di default: con un file audio il fondo adattivo
   inseguiva il segnale e azzerava l'energia
 - Feedback TOP collegato al render
 - parametro Energia manuale per tarare senza audio
-------------------------------------------------------------------
"""

import td

ROOT = op('/project1')
NAME = 'asemic_marks'

warnings = []


# ------------------------------------------------------------------
# helper difensivi
# ------------------------------------------------------------------

def TYPE(*names):
    for n in names:
        t = getattr(td, n, None)
        if t is not None:
            return t
    raise RuntimeError('Nessuna di queste classi OP esiste in questa build: %s' % (names,))


def setattr_safe(o, name, value):
    try:
        setattr(o, name, value)
        return True
    except Exception as err:
        warnings.append('%s.%s = %r -> %s' % (o.name, name, value, err))
        return False


def setpar(o, value, *names):
    for n in names:
        p = getattr(o.par, n, None)
        if p is not None:
            try:
                p.val = value
                return True
            except Exception as err:
                warnings.append('%s.%s = %r -> %s' % (o.name, n, value, err))
    warnings.append('%s: nessun parametro tra %s' % (o.name, names))
    return False


def setexpr(o, expression, *names):
    for n in names:
        p = getattr(o.par, n, None)
        if p is not None:
            try:
                p.expr = expression
                return True
            except Exception as err:
                warnings.append('%s.%s expr -> %s' % (o.name, n, err))
    warnings.append('%s: nessun parametro tra %s' % (o.name, names))
    return False


def setmenu(o, targets, *names):
    if isinstance(targets, str):
        targets = (targets,)
    wanted = [t.lower() for t in targets]
    for n in names:
        p = getattr(o.par, n, None)
        if p is None:
            continue
        try:
            for mn, ml in zip(p.menuNames, p.menuLabels):
                if mn.lower() in wanted or ml.lower() in wanted:
                    p.val = mn
                    return True
        except Exception:
            continue
    warnings.append('%s: voce di menu %s non trovata in %s' % (o.name, targets, names))
    return False


def callbacks_dat(script_op, parent_comp, fallback_name):
    """Gli Script OP creano gia' un DAT di callback: riusalo invece di
    crearne un secondo (era l'origine dei nomi con la '1' in coda)."""
    d = None
    try:
        d = script_op.par.callbacks.eval()
    except Exception:
        d = None
    if not (d is not None and hasattr(d, 'isDAT') and d.isDAT):
        d = parent_comp.op(fallback_name)
    if not (d is not None and hasattr(d, 'isDAT') and d.isDAT):
        d = parent_comp.create(TYPE('textDAT'), fallback_name)
    setpar(script_op, d.name, 'callbacks')
    return d


def fpar(page, name, label, default, lo, hi):
    try:
        p = page.appendFloat(name, label=label)[0]
        p.normMin, p.normMax = lo, hi
        p.default = default
        p.val = default
        return p
    except Exception as err:
        warnings.append('parametro %s -> %s' % (name, err))
        return None


def ipar(page, name, label, default, lo, hi):
    try:
        p = page.appendInt(name, label=label)[0]
        p.normMin, p.normMax = lo, hi
        p.default = default
        p.val = default
        return p
    except Exception as err:
        warnings.append('parametro %s -> %s' % (name, err))
        return None


def tpar(page, name, label, default):
    try:
        p = page.appendToggle(name, label=label)[0]
        p.default = default
        p.val = default
        return p
    except Exception as err:
        warnings.append('parametro %s -> %s' % (name, err))
        return None


def rgbpar(page, name, label, default):
    try:
        page.appendRGB(name, label=label)
        for ch, v in zip('rgb', default):
            q = getattr(base.par, name + ch)
            q.default = v
            q.val = v
    except Exception as err:
        warnings.append('parametro %s -> %s' % (name, err))


def menupar(page, name, label, names, labels, default):
    try:
        m = page.appendMenu(name, label=label)[0]
        m.menuNames = names
        m.menuLabels = labels
        m.default = default
        m.val = default
        return m
    except Exception as err:
        warnings.append('parametro %s -> %s' % (name, err))
        return None


def header(page, text):
    try:
        page.appendHeader(tdu.legalName(text), label=text)
    except Exception:
        pass


def save_custom(base):
    if base is None:
        return {}
    out = {}
    for p in base.customPars:
        try:
            if p.style in ('Pulse', 'Momentary'):
                continue
            out[p.name] = p.val
        except Exception:
            pass
    return out


def restore_custom(base, values):
    for name, val in values.items():
        p = getattr(base.par, name, None)
        if p is not None:
            try:
                p.val = val
            except Exception:
                pass


# ------------------------------------------------------------------
# ricostruzione
# ------------------------------------------------------------------

old = ROOT.op(NAME)
saved = save_custom(old)
if old:
    old.destroy()

base = ROOT.create(TYPE('baseCOMP'), NAME)
base.nodeX, base.nodeY = 0, 0
setattr_safe(base, 'color', (0.10, 0.10, 0.12))


# ---------------------------- parametri ----------------------------

page = base.appendCustomPage('Asemic')

t = page.appendToggle('Active')[0]
t.default = True
t.val = True
page.appendPulse('Clear')
ipar(page, 'Seed', 'Seed', 1, 0, 9999)

header(page, 'Audio')
fpar(page, 'Gain', 'Gain ingresso', 3.0, 0.0, 20.0)
fpar(page, 'Sensitivity', 'Sensibilita', 0.8, 0.0, 1.0)
fpar(page, 'Attack', 'Attack', 0.35, 0.01, 1.0)
tpar(page, 'Stereo', 'Ingresso stereo', True)
fpar(page, 'Pitchlow', 'Registro: grave (Hz)', 80.0, 20.0, 500.0)
fpar(page, 'Pitchhigh', 'Registro: acuto (Hz)', 5000.0, 1000.0, 12000.0)
fpar(page, 'Brightsmooth', 'Smussatura registro', 0.25, 0.01, 1.0)
fpar(page, 'Pansmooth', 'Smussatura pan', 0.3, 0.01, 1.0)
tpar(page, 'Panmap', 'Pan -> posizione X', True)
fpar(page, 'Panspread', 'Aderenza al pan', 0.7, 0.0, 1.0)
tpar(page, 'Automode', 'Normalizza automatica', True)
fpar(page, 'Peakfall', 'Decadimento soffitto', 0.6, 0.0, 4.0)
fpar(page, 'Floorfall', 'Fondo discesa', 0.05, 0.0, 0.5)
# 0 = fondo congelato sul minimo. Con un file audio continuo un valore
# maggiore di zero fa inseguire il segnale al fondo, azzerando l'energia.
fpar(page, 'Floorrise', 'Fondo salita', 0.0, 0.0, 0.02)
fpar(page, 'Testenergy', 'Energia manuale', 0.0, 0.0, 1.0)

header(page, 'Segni')
fpar(page, 'Spawnrate', 'Densita', 1.0, 0.0, 4.0)
ipar(page, 'Maxmarks', 'Segni max', 48, 1, 400)
life = page.appendFloat('Life', label='Durata', size=2)
for p, d in zip(life, (1.4, 2.8)):
    p.normMin, p.normMax = 0.1, 10.0
    p.default = d
    p.val = d
fpar(page, 'Size', 'Scala', 1.0, 0.05, 3.0)
fpar(page, 'Wobble', 'Wobble', 0.03, 0.0, 0.2)
fpar(page, 'Wobblespeed', 'Wobble speed', 0.6, 0.0, 4.0)
ipar(page, 'Resample', 'Suddivisione curve', 6, 1, 16)

fpar(page, 'Geowobble', 'Wobble geometrici', 0.008, 0.0, 0.2)

header(page, 'Forme asemiche')
for key, lab, d in [('walk', 'Cammino', 1.0), ('orbit', 'Orbita', 1.0),
                    ('spiral', 'Spirale', 0.5), ('ribbon', 'Nastro', 0.5),
                    ('burst', 'Raggiera', 0.3), ('glyph', 'Glifo', 0.5)]:
    tpar(page, 'On' + key, lab, True)
    fpar(page, 'W' + key, lab + ' peso', d, 0.0, 2.0)

header(page, 'Forme geometriche')
for key, lab in [('circle', 'Cerchio'), ('poly', 'Poligono'),
                 ('square', 'Quadrato'), ('tri', 'Triangolo'),
                 ('arc', 'Arco'), ('cross', 'Croce')]:
    tpar(page, 'On' + key, lab, False)
    fpar(page, 'W' + key, lab + ' peso', 0.5, 0.0, 2.0)
ipar(page, 'Polysides', 'Lati poligono', 6, 3, 12)

header(page, 'Testo')
tpar(page, 'Ontext', 'Testo', False)
fpar(page, 'Wtext', 'Testo peso', 0.6, 0.0, 2.0)
try:
    _ts = page.appendStr('Textstring', label='Stringa')[0]
    _ts.default = 'ASEMIC'
    _ts.val = 'ASEMIC'
except Exception as err:
    warnings.append('parametro Textstring -> %s' % err)
try:
    _tm = page.appendMenu('Textmode', label='Modo')[0]
    _tm.menuNames = ['rand', 'seq', 'word']
    _tm.menuLabels = ['Carattere casuale', 'Carattere in sequenza', 'Parola intera']
    _tm.default = 'rand'
    _tm.val = 'rand'
except Exception as err:
    warnings.append('parametro Textmode -> %s' % err)
fpar(page, 'Textsize', 'Dimensione testo', 1.0, 0.2, 4.0)
fpar(page, 'Textwobble', 'Wobble testo', 0.012, 0.0, 0.2)
fpar(page, 'Textrotate', 'Rotazione testo', 0.0, 0.0, 1.0)

header(page, 'Attacchi')
tpar(page, 'Onsetmode', 'Nascita su attacco', False)
fpar(page, 'Onsetthresh', 'Soglia attacco', 0.12, 0.0, 1.0)
fpar(page, 'Onsetrelease', 'Rilascio inviluppo', 0.06, 0.005, 0.5)
ipar(page, 'Refractory', 'Pausa minima (ms)', 90, 0, 1000)

header(page, 'Resa')
page.appendRGB('Inkcolor', label='Colore segno')
for ch in 'rgb':
    p = getattr(base.par, 'Inkcolor' + ch)
    p.default = 1.0
    p.val = 1.0
page.appendRGB('Bgcolor', label='Fondo')
for ch in 'rgb':
    p = getattr(base.par, 'Bgcolor' + ch)
    p.default = 0.0
    p.val = 0.0
# Il Line MAT espande le linee in geometria, quindi accetta spessori
# sotto il pixel: sono legittimi, solo piu' tenui.
fpar(page, 'Linewidth', 'Spessore', 1.0, 0.02, 8.0)
fpar(page, 'Inkalpha', 'Opacita tratto', 1.0, 0.05, 1.0)
menupar(page, 'Colormode', 'Modo colore',
        ['single', 'family', 'palette', 'palenergy', 'pitch', 'energy',
         'random'],
        ['Unico', 'Per famiglia', 'Palette', 'Palette da energia',
         'Palette da altezza', 'Da energia', 'Casuale'],
        'single')
rgbpar(page, 'Geocolor', 'Colore geometrici', (0.55, 0.85, 1.0))
rgbpar(page, 'Textcolor', 'Colore testo', (1.0, 0.82, 0.35))
rgbpar(page, 'Hicolor', 'Colore energia alta', (1.0, 0.35, 0.18))
for _i, _c in enumerate([(1.0, 1.0, 1.0), (0.95, 0.45, 0.25),
                         (0.35, 0.75, 0.95), (0.85, 0.95, 0.45)]):
    rgbpar(page, 'Pal%d' % (_i + 1), 'Palette %d' % (_i + 1), _c)
fpar(page, 'Palspread', 'Dispersione palette', 0.35, 0.0, 1.0)
fpar(page, 'Paljitter', 'Variazione colore', 0.15, 0.0, 1.0)
fpar(page, 'Randsat', 'Saturazione casuale', 0.6, 0.0, 1.0)
fpar(page, 'Randval', 'Luminosita casuale', 1.0, 0.1, 1.0)

fpar(page, 'Glow', 'Glow', 0.0, 0.0, 3.0)
fpar(page, 'Glowsize', 'Glow raggio', 12.0, 0.0, 80.0)
fpar(page, 'Trail', 'Scia', 0.0, 0.0, 0.99)
fpar(page, 'Zoom', 'Zoom', 1.0, 0.2, 4.0)

header(page, 'Rampa in uscita')
tpar(page, 'Rampmode', 'Rimappa con rampa', False)
rgbpar(page, 'Rampcola', 'Rampa: scuri', (0.04, 0.02, 0.12))
rgbpar(page, 'Rampcolb', 'Rampa: chiari', (1.0, 0.88, 0.62))

header(page, 'Rotazione 3D')
try:
    _rot = page.appendFloat('Rotate', label='Rotazione scena', size=3)
    for _p in _rot:
        _p.normMin, _p.normMax = -180.0, 180.0
        _p.default = 0.0
        _p.val = 0.0
except Exception as err:
    warnings.append('parametro Rotate -> %s' % err)
try:
    _spin = page.appendFloat('Spin', label='Rotazione continua', size=3)
    for _p in _spin:
        _p.normMin, _p.normMax = -90.0, 90.0
        _p.default = 0.0
        _p.val = 0.0
except Exception as err:
    warnings.append('parametro Spin -> %s' % err)
fpar(page, 'Tumble', 'Rotazione dei segni', 0.0, 0.0, 1.0)
fpar(page, 'Tumblespeed', 'Velocita rotazione segni', 0.3, 0.0, 3.0)
fpar(page, 'Depth', 'Profondita', 0.0, 0.0, 1.0)
resp = page.appendInt('Resolution', label='Risoluzione', size=2)
for p, d in zip(resp, (1280, 720)):     # licenza Non-Commercial: max 1280
    p.default = d
    p.val = d

restore_custom(base, saved)


# ------------------------------- audio -----------------------------

audioin = base.create(TYPE('audiodeviceinCHOP'), 'audio_in')
audioin.nodeX, audioin.nodeY = -800, 400

# I canali non vengono piu' combinati: L e R arrivano separati allo
# script, che li unisce solo se "Ingresso stereo" e' spento.
mono = base.create(TYPE('mathCHOP'), 'audio_src')
mono.nodeX, mono.nodeY = -640, 400
mono.inputConnectors[0].connect(audioin)
setmenu(mono, ('off', 'Off'), 'chanop')

rms = base.create(TYPE('analyzeCHOP'), 'audio_rms')
rms.nodeX, rms.nodeY = -480, 400
rms.inputConnectors[0].connect(mono)
setmenu(rms, ('rms', 'RMS Power', 'RMS'), 'function')

energy = base.create(TYPE('scriptCHOP'), 'energy')
energy.nodeX, energy.nodeY = -320, 400
energy.inputConnectors[0].connect(rms)

# Spettro per stimare il registro. E' il SECONDO ingresso dello script:
# se il nodo non esistesse o l'analisi fallisse, il primo ingresso e
# tutto il resto continuerebbero a funzionare.
try:
    spec = base.create(TYPE('audiospectrumCHOP'), 'audio_spectrum')
    spec.nodeX, spec.nodeY = -640, 300
    spec.inputConnectors[0].connect(mono)
    energy.inputConnectors[1].connect(spec)
except Exception as err:
    warnings.append('audio_spectrum non collegato -> %s' % err)

energy_dat = callbacks_dat(energy, base, 'energy_callbacks')
energy_dat.nodeX, energy_dat.nodeY = -320, 520

energy_dat.text = '''
import math

# Stereo: i due canali restano separati. Oltre al livello esce anche la
# posizione nell'immagine stereofonica, che i segni usano per decidere
# dove nascere. Il pavimento e il soffitto sono entrambi adattivi:
# normalizzare rispetto al solo pavimento faceva saturare l'energia a 1.

try:
    import numpy as _np
except Exception:
    _np = None

state = {'level': 0.0, 'floor': 0.004, 'peak': 0.05, 'env': 0.0,
         't': 0.0, 'pan': 0.0, 'bright': 0.5}


def _centroid(src, nyq):
    """Centroide spettrale in Hz: il baricentro dell'energia lungo la
    frequenza. E' una stima grezza del registro, non un riconoscitore di
    altezza, ma per distinguere gravi da acuti basta e avanza."""
    try:
        if _np is not None:
            arr = src.numpyArray()
            mag = arr.mean(axis=0) if getattr(arr, 'ndim', 1) > 1 else arr
            n = len(mag)
            if n < 4:
                return None
            tot = float(mag.sum())
            if tot <= 1e-9:
                return None
            freqs = _np.linspace(0.0, nyq, n)
            return float((mag * freqs).sum() / tot)
        # senza numpy: campionamento rado, abbastanza per il registro
        ch = src.chans()[0]
        n = len(ch)
        if n < 4:
            return None
        step = max(1, n // 64)
        num = den = 0.0
        for i in range(0, n, step):
            m = abs(float(ch[i]))
            num += m * (i / float(n)) * nyq
            den += m
        return num / den if den > 1e-9 else None
    except Exception:
        return None


def onSetupParameters(scriptOp):
    return


def onCook(scriptOp):
    b = scriptOp.parent()
    scriptOp.clear()

    now = absTime.seconds
    dt = (now - state['t']) if state['t'] else 0.0
    state['t'] = now
    dt = max(0.0, min(dt, 0.064))

    vals = []
    if len(scriptOp.inputs):
        for c in scriptOp.inputs[0].chans():
            try:
                vals.append(abs(float(c)))
            except Exception:
                pass
    nch = len(vals)

    g = float(b.par.Gain)
    try:
        stereo = bool(b.par.Stereo)
    except Exception:
        stereo = True

    if stereo and nch >= 2:
        left, right = vals[0] * g, vals[1] * g
    elif nch:
        left = right = max(vals) * g
    else:
        left = right = 0.0

    raw = max(left, right)

    atk = max(0.001, min(1.0, float(b.par.Attack)))
    state['level'] += (raw - state['level']) * atk
    lvl = state['level']

    # pavimento: scende in fretta, risale piano
    k = float(b.par.Floorfall) if lvl < state['floor'] else float(b.par.Floorrise)
    state['floor'] += (lvl - state['floor']) * k

    # soffitto: sale subito sul picco, poi decade verso il pavimento
    try:
        pf = max(0.0, min(4.0, float(b.par.Peakfall)))
    except Exception:
        pf = 0.6
    if lvl > state['peak']:
        state['peak'] = lvl
    else:
        state['peak'] -= (state['peak'] - state['floor']) * pf * dt
    state['peak'] = max(state['peak'], state['floor'] + 1e-5)

    span = state['peak'] - state['floor']

    # Pan da -1 (sinistra) a +1 (destra). Sotto il pavimento il rapporto
    # fra due rumori di fondo non significa nulla, quindi il valore resta
    # fermo sull'ultimo utile invece di sbandare.
    tot = left + right
    if tot > 1e-6 and lvl > state['floor'] * 1.5:
        target = (right - left) / tot
        try:
            sm = max(0.01, min(1.0, float(b.par.Pansmooth)))
        except Exception:
            sm = 0.3
        state['pan'] += (target - state['pan']) * sm
    pan = max(-1.0, min(1.0, state['pan']))

    # Registro: secondo ingresso, opzionale. Se manca o fallisce, bright
    # resta a 0.5 e tutto il resto lavora esattamente come prima.
    cent = None
    if len(scriptOp.inputs) > 1 and lvl > state['floor'] * 1.5:
        try:
            rate = float(op('audio_src').rate)
        except Exception:
            rate = 44100.0
        cent = _centroid(scriptOp.inputs[1], rate * 0.5)
    if cent:
        try:
            lo = max(20.0, float(b.par.Pitchlow))
            hi = max(lo * 1.1, float(b.par.Pitchhigh))
        except Exception:
            lo, hi = 80.0, 5000.0
        t = (math.log(max(cent, lo)) - math.log(lo)) / (math.log(hi) - math.log(lo))
        t = max(0.0, min(1.0, t))
        try:
            bs = max(0.01, min(1.0, float(b.par.Brightsmooth)))
        except Exception:
            bs = 0.25
        state['bright'] += (t - state['bright']) * bs
    bright = max(0.0, min(1.0, state['bright']))

    try:
        auto = bool(b.par.Automode)
    except Exception:
        auto = True

    sens = max(0.0, min(1.0, float(b.par.Sensitivity)))
    if auto:
        # Sensibilita come curva, non come divisore: sotto 0.5 comprime
        # i passaggi deboli, sopra 0.5 li tira su.
        e = (lvl - state['floor']) / span if span > 1e-6 else 0.0
        e = max(0.0, min(1.0, e))
        e = pow(e, pow(4.0, 0.5 - sens))
        div = span
    else:
        div = 0.3 * pow(0.02 / 0.3, sens)
        e = max(0.0, min(1.0, (lvl - state['floor']) / div))

    # Inviluppo a rilascio lento: la differenza positiva col livello
    # istantaneo isola l'attacco di nota dalla coda che decade.
    try:
        rel = max(0.005, min(0.5, float(b.par.Onsetrelease)))
    except Exception:
        rel = 0.06
    prev_env = state['env']
    state['env'] = lvl if lvl > prev_env else prev_env + (lvl - prev_env) * rel
    attack = max(0.0, min(1.0, (lvl - prev_env) / div)) if div > 1e-6 else 0.0

    for name, val in (('left', left), ('right', right), ('pan', pan),
                      ('bright', bright), ('centroid', cent or 0.0),
                      ('level', lvl), ('floor', state['floor']),
                      ('peak', state['peak']), ('energy', e),
                      ('attack', attack), ('nchans', float(nch))):
        scriptOp.appendChan(name)[0] = val
    return
'''

energy_null = base.create(TYPE('nullCHOP'), 'energy_out')
energy_null.nodeX, energy_null.nodeY = -160, 400
energy_null.inputConnectors[0].connect(energy)


# ------------------------- geometria (dentro geo) -------------------

geo = base.create(TYPE('geometryCOMP', 'geoCOMP'), 'geo')
geo.nodeX, geo.nodeY = 0, 120
for child in list(geo.children):
    if child.name == 'torus1':
        child.destroy()

marks = geo.create(TYPE('scriptSOP'), 'marks')
marks.nodeX, marks.nodeY = 0, 0

marks_dat = callbacks_dat(marks, geo, 'marks_callbacks')
marks_dat.nodeX, marks_dat.nodeY = 0, 120

marks_dat.text = r'''
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
'''

marks_out = geo.create(TYPE('nullSOP'), 'marks_out')
marks_out.nodeX, marks_out.nodeY = 160, 0
marks_out.inputConnectors[0].connect(marks)
setattr_safe(marks_out, 'render', True)
setattr_safe(marks_out, 'display', True)


# ------------------------------ render -----------------------------

mat = base.create(TYPE('lineMAT', 'wireframeMAT', 'constantMAT'), 'line_mat')
mat.nodeX, mat.nodeY = 0, 240
setmenu(mat, ('point', 'Point Color', 'pointcolor'), 'colorsource', 'colorsrc')
setmenu(mat, ('point', 'Point Color Alpha', 'pointalpha'), 'alphasource', 'alphasrc')
setexpr(mat, "op('..').par.Linewidth", 'linewidth', 'width')
setpar(geo, mat, 'material')

# Rotazione della scena: valore fisso piu' deriva continua in gradi/sec.
# Con la camera ortografica diventa uno scorcio, non una prospettiva.
for _i, _ax in enumerate('xyz'):
    setexpr(geo,
            "op('..').par.Rotate%d.eval()"
            " + absTime.seconds * op('..').par.Spin%d.eval()" % (_i + 1, _i + 1),
            'r' + _ax)

cam = base.create(TYPE('cameraCOMP'), 'cam')
cam.nodeX, cam.nodeY = 0, 0
setmenu(cam, ('ortho', 'Orthographic'), 'projection')
setpar(cam, 5.0, 'tz')
# I segni vivono in x da -aspect a +aspect, y da -1 a 1. L'Ortho Width e'
# la larghezza orizzontale, quindi vale 2*aspect. Le .eval() sono
# necessarie: senza, max() confronta un int con un oggetto Par e
# l'espressione fallisce lasciando la camera invalida.
_ow = ("2.0 * op('..').par.Resolution1.eval()"
       " / max(1.0, op('..').par.Resolution2.eval())"
       " / max(0.01, op('..').par.Zoom.eval())")
if not setexpr(cam, _ow, 'orthowidth'):
    setpar(cam, 2.0 * 1280 / 720.0, 'orthowidth')

render = base.create(TYPE('renderTOP'), 'render')
render.nodeX, render.nodeY = 200, 120
setpar(render, geo, 'geometry')
setpar(render, cam, 'camera')
setexpr(render, "op('..').par.Resolution1", 'resolutionw')
setexpr(render, "op('..').par.Resolution2", 'resolutionh')
# Le linee sotto il pixel hanno bisogno di multisampling alto, altrimenti
# si sgranano invece di assottigliarsi.
if not setmenu(render, ('8x', 'aa8', '8'), 'antialias'):
    setpar(render, 4, 'antialias')

# glow: sfocatura del render, riscalata e riaddizionata sopra
glow_blur = base.create(TYPE('blurTOP'), 'glow_blur')
glow_blur.nodeX, glow_blur.nodeY = 340, 260
glow_blur.inputConnectors[0].connect(render)
setexpr(glow_blur, "op('..').par.Glowsize", 'size', 'filtersize')

glow_lvl = base.create(TYPE('levelTOP'), 'glow_level')
glow_lvl.nodeX, glow_lvl.nodeY = 480, 260
glow_lvl.inputConnectors[0].connect(glow_blur)
setexpr(glow_lvl, "op('..').par.Glow", 'opacity')

glow = base.create(TYPE('compositeTOP'), 'glow')
glow.nodeX, glow.nodeY = 620, 160
glow.inputConnectors[0].connect(render)
glow.inputConnectors[1].connect(glow_lvl)
setmenu(glow, ('add', 'Add'), 'operand')

fb = base.create(TYPE('feedbackTOP'), 'trail_fb')
fb.nodeX, fb.nodeY = 620, 320
fb.inputConnectors[0].connect(glow)   # senza ingresso il Feedback va in errore

fade = base.create(TYPE('levelTOP'), 'trail_fade')
fade.nodeX, fade.nodeY = 360, 280
fade.inputConnectors[0].connect(fb)
setexpr(fade, "op('..').par.Trail", 'opacity')

ink = base.create(TYPE('compositeTOP'), 'ink')
ink.nodeX, ink.nodeY = 360, 120
ink.inputConnectors[0].connect(glow)
ink.inputConnectors[1].connect(fade)
setmenu(ink, ('add', 'Add'), 'operand')
setpar(fb, ink, 'top')

bg = base.create(TYPE('constantTOP'), 'bg')
bg.nodeX, bg.nodeY = 360, 0
for ch in 'rgb':
    setexpr(bg, "op('..').par.Bgcolor%s" % ch, 'color' + ch)
setexpr(bg, "op('..').par.Resolution1", 'resolutionw')
setexpr(bg, "op('..').par.Resolution2", 'resolutionh')

over = base.create(TYPE('overTOP'), 'over_bg')
over.nodeX, over.nodeY = 520, 60
over.inputConnectors[0].connect(ink)
over.inputConnectors[1].connect(bg)

# --- rampa in uscita: gradient map a due colori ---
# La rampa viene costruita con aritmetica di TOP invece che leggendo le
# chiavi di un Ramp TOP, i cui parametri cambiano nome fra le build.
ramp_src = base.create(TYPE('rampTOP'), 'ramp_src')
ramp_src.nodeX, ramp_src.nodeY = 680, 340
setmenu(ramp_src, ('horizontal', 'Horizontal'), 'type')
setpar(ramp_src, 256, 'resolutionw')
setpar(ramp_src, 2, 'resolutionh')

ramp_inv = base.create(TYPE('levelTOP'), 'ramp_inv')
ramp_inv.nodeX, ramp_inv.nodeY = 820, 400
ramp_inv.inputConnectors[0].connect(ramp_src)
setpar(ramp_inv, 1.0, 'invert')

ramp_a = base.create(TYPE('constantTOP'), 'ramp_col_a')
ramp_a.nodeX, ramp_a.nodeY = 820, 480
ramp_b = base.create(TYPE('constantTOP'), 'ramp_col_b')
ramp_b.nodeX, ramp_b.nodeY = 820, 260
for _c, _src in ((ramp_a, 'Rampcola'), (ramp_b, 'Rampcolb')):
    for _ch in 'rgb':
        setexpr(_c, "op('..').par.%s%s" % (_src, _ch), 'color' + _ch)
    setpar(_c, 256, 'resolutionw')
    setpar(_c, 2, 'resolutionh')

mix_a = base.create(TYPE('compositeTOP'), 'ramp_mix_a')
mix_a.nodeX, mix_a.nodeY = 960, 440
mix_a.inputConnectors[0].connect(ramp_a)
mix_a.inputConnectors[1].connect(ramp_inv)
setmenu(mix_a, ('multiply', 'Multiply'), 'operand')

mix_b = base.create(TYPE('compositeTOP'), 'ramp_mix_b')
mix_b.nodeX, mix_b.nodeY = 960, 300
mix_b.inputConnectors[0].connect(ramp_b)
mix_b.inputConnectors[1].connect(ramp_src)
setmenu(mix_b, ('multiply', 'Multiply'), 'operand')

gradient = base.create(TYPE('compositeTOP'), 'ramp_gradient')
gradient.nodeX, gradient.nodeY = 1100, 370
gradient.inputConnectors[0].connect(mix_a)
gradient.inputConnectors[1].connect(mix_b)
setmenu(gradient, ('add', 'Add'), 'operand')

lut = base.create(TYPE('lookupTOP'), 'ramp_lookup')
lut.nodeX, lut.nodeY = 820, 140
lut.inputConnectors[0].connect(over)
lut.inputConnectors[1].connect(gradient)

ramp_sw = base.create(TYPE('switchTOP'), 'ramp_switch')
ramp_sw.nodeX, ramp_sw.nodeY = 960, 60
ramp_sw.inputConnectors[0].connect(over)
ramp_sw.inputConnectors[1].connect(lut)
setexpr(ramp_sw, "op('..').par.Rampmode", 'index')

out = base.create(TYPE('nullTOP'), 'out')
out.nodeX, out.nodeY = 1100, 60
out.inputConnectors[0].connect(ramp_sw)
setattr_safe(out, 'viewer', True)

# Uscita del COMP: rende asemic_marks collegabile nella rete padre
out_top = base.create(TYPE('outTOP'), 'out_top')
out_top.nodeX, out_top.nodeY = 1240, 60
out_top.inputConnectors[0].connect(out)

# Anteprima sul nodo stesso: si vede l'effetto dei parametri senza entrare
setpar(base, './out', 'opviewer')


# -------------------------------- UI -------------------------------

try:
    ui = base.create(TYPE('parameterCOMP'), 'ui')
    ui.nodeX, ui.nodeY = 680, 300
    setpar(ui, base.path, 'ops', 'op')
    setpar(ui, 340, 'w')
    setpar(ui, 820, 'h')
except Exception as err:
    warnings.append('Parameter COMP non creato: %s' % err)


# ------------------------------ Clear ------------------------------

try:
    ex = base.create(TYPE('parameterexecuteDAT'), 'clear_exec')
    ex.nodeX, ex.nodeY = -320, -40
    setpar(ex, base.path, 'op', 'ops')
    setpar(ex, True, 'pulse', 'onpulse')
    setpar(ex, False, 'valuechange')
    ex.text = '''
def onPulse(par):
    if par.name == 'Clear':
        d = par.owner.op('geo').op('%s')
        mod(d).marks.clear()
    return
''' % marks_dat.name
except Exception as err:
    warnings.append('clear_exec non creato: %s' % err)


# ------------------------------ report -----------------------------

print('=' * 64)
print('asemic_marks costruito in %s' % base.path)
print('Uscita: %s/out_top (il COMP ora ha un connettore TOP)' % base.path)
print('Callback: %s , %s' % (energy_dat.path, marks_dat.path))
print('Materiale linee: %s  (con Wireframe o Constant lo spessore e\' fisso a 1px)'
      % mat.type)
print('UI: apri il Parameter COMP "ui" in un pannello')
print('Prova senza audio: alza "Energia manuale" a 0.5')
if warnings:
    print('\nDa verificare a mano (%d):' % len(warnings))
    for w in warnings:
        print('  - ' + w)
else:
    print('\nNessun avviso.')
print('=' * 64)