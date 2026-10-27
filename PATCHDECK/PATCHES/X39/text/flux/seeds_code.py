# seeds — posizioni casuali delle istanze (Script CHOP)
import numpy as np

K_WHITE = 16
K_BLUE = 4


def _p(owner, name, default):
    p = getattr(owner.par, name, None)
    return p.eval() if p is not None else default


def onSetupParameters(scriptOp):
    return


def onPulse(par):
    return


def onCook(scriptOp):
    C = scriptOp.parent()
    n = max(1, int(_p(C, 'Count', 1500)))
    depth = float(_p(C, 'Depth', 60.0))
    near = float(_p(C, 'Near', 4.5))
    lanes = max(1, int(_p(C, 'Lanes', 40)))
    width = float(_p(C, 'Width', 30.0))
    height = float(_p(C, 'Height', 8.0))
    smin = float(_p(C, 'Sizemin', 0.15))
    smax = float(_p(C, 'Sizemax', 0.6))
    bluefrac = float(_p(C, 'Bluefrac', 0.08))
    bias = float(_p(C, 'Centerbias', 0.0))
    rng = np.random.default_rng(int(_p(C, 'Seed', 1)))

    lane = rng.integers(0, lanes, n)
    v = (lane / max(1, lanes - 1)) * 2.0 - 1.0          # -1..1
    if bias > 0:                                          # corsie più fitte al centro
        v = np.sign(v) * np.abs(v) ** (1.0 + bias)
    ty = v * height
    tx = (rng.random(n) - 0.5) * 2.0 * width
    z0 = rng.random(n) * (depth + near) - depth
    tok = rng.integers(0, K_WHITE, n)
    size = smin + rng.random(n) * (smax - smin)
    blue = rng.random(n) < bluefrac

    scriptOp.clear()
    scriptOp.numSamples = n
    for name, arr in (('tx', tx), ('ty', ty), ('z0', z0)):
        scriptOp.appendChan(name).vals = arr.tolist()
    for k in range(K_WHITE):
        scriptOp.appendChan('w%d' % k).vals = np.where((tok == k) & ~blue, size, 0.0).tolist()
    for b in range(K_BLUE):
        scriptOp.appendChan('b%d' % b).vals = np.where(((tok % K_BLUE) == b) & blue, size, 0.0).tolist()
    return
