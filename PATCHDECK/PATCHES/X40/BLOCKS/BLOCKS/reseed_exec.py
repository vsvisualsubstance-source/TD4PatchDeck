import random

SIGLE = ['a','b','c','d','e','f','g']

def onPulse(par):
    c = par.owner
    if par.name == 'Reseed':
        c.par.Seed = random.randint(0, 99999)
    elif par.name == 'Reseedcolor':
        c.par.Colorseed = random.randint(0, 99999)
    elif par.name == 'Palcopy':
        src = c.op('pal_%d' % c.par.Palette.menuIndex)
        if src is None:
            return   # gia' su Custom: niente da copiare
        for n, s in enumerate(SIGLE):
            for ch in 'rgb':
                try:
                    setattr(c.par, 'Palcol%s%s' % (s, ch), src[ch][n])
                except Exception:
                    pass
    return
