
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
            if getattr(arr, 'size', 0) == 0:
                return None
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
