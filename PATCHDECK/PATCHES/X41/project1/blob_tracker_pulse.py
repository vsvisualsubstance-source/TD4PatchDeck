
def onPulse(par):
    comp = par.owner
    if par.name != 'Diagnose':
        return
    s = comp.op('script1')
    t = comp.op('blob_table')
    print('=' * 66)
    print('blob_tracker - diagnostica')
    print('-' * 66)
    src = comp.op('source')
    if src is not None:
        print('sorgente :', src.par.file.eval())
        print('           %d x %d' % (src.width, src.height))
        if src.width == 0:
            print('           -> filmato NON caricato, controlla il percorso')
    det = comp.op('detect_res')
    if det is not None:
        print('detect   : %d x %d | ridotto: %s'
              % (det.width, det.height, bool(comp.par.Downscale.eval())))
    if s is not None:
        print('script1  : %d x %d' % (s.width, s.height))
        print('           Outputdat =', s.par.Outputdat.eval())
        print('           Linksdat  =', s.par.Linksdat.eval())
        for p in ('Active', 'Blurw', 'Blocksize', 'Morph', 'Maxblobs', 'Minage'):
            try:
                print('           %-10s = %s' % (p, getattr(s.par, p).eval()))
            except Exception:
                print('           %-10s = (parametro assente)' % p)
        err = s.errors()
        if err:
            print('           ERRORI:', err[:500])
    if t is not None:
        print('tabella  : %d righe' % t.numRows)
        if t.numRows:
            print('           colonne:', [str(c.val) for c in t.row(0)])
    print('=' * 66)
    return
