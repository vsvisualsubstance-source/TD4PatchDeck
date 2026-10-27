
SCALES = {
    'chromatic': [0,1,2,3,4,5,6,7,8,9,10,11],
    'major':     [0,2,4,5,7,9,11],
    'minor':     [0,2,3,5,7,8,10],
    'dorian':    [0,2,3,5,7,9,10],
    'penta':     [0,3,5,7,10],
    'whole':     [0,2,4,6,8,10],
}

# Colonne scritte dal tracker: id u v area w h age
COLS = {
    'id':   ['id', 'blobid', 'index'],
    'u':    ['u', 'x', 'tx', 'centerx', 'posx'],
    'v':    ['v', 'y', 'ty', 'centery', 'posy'],
    'area': ['area', 'size', 'pixels'],
    'age':  ['age', 'life', 'frames'],
}

MAXROWS = 400


def _cols(header, comp):
    cached = comp.fetch('cols_cache', None)
    if cached and cached[0] == header:
        return cached[1]
    low = [h.strip().lower() for h in header]
    found = {}
    for key, cands in COLS.items():
        for cand in cands:
            if cand in low:
                found[key] = low.index(cand)
                break
    comp.store('cols_cache', (header, found))
    debug('blob_audio - colonne in ingresso:', header, '-> mappate:', found)
    for k in ('id', 'u', 'v'):
        if k not in found:
            debug('blob_audio - MANCA la colonna', k)
    return found


def read_blobs(comp):
    """Legge la tabella da .text con uno split.

    Cella per cella (dat.row(r)[i].val) costa molto di piu': su 40 blob
    per frame si sente.
    """
    src = comp.op('blobs_in')
    if src is None:
        return []
    txt = src.text
    if not txt:
        return []
    lines = txt.split('\n')
    if len(lines) < 2:
        return []
    cols = _cols(lines[0].split('\t'), comp)
    ii, iu, iv = cols.get('id'), cols.get('u'), cols.get('v')
    if ii is None or iu is None or iv is None:
        return []
    ia, ig = cols.get('area'), cols.get('age')

    minarea = float(comp.par.Minarea.eval())
    out = []
    for line in lines[1:MAXROWS + 1]:
        if not line:
            continue
        f = line.split('\t')
        try:
            bid = int(float(f[ii]))
            u = float(f[iu])
            v = float(f[iv])
            area = float(f[ia]) if ia is not None else minarea
            age = int(float(f[ig])) if ig is not None else 999
        except (ValueError, IndexError):
            continue
        if area < minarea:
            continue
        out.append((bid, u, v, area, age))
    out.sort(key=lambda b: b[3], reverse=True)
    return out


def quantize(norm, root, octaves, scale_name):
    steps = SCALES.get(scale_name, SCALES['minor'])
    total = len(steps) * max(1, octaves)
    idx = int(max(0.0, min(0.999999, norm)) * total)
    octv, deg = divmod(idx, len(steps))
    return int(max(0, min(127, root + octv * 12 + steps[deg])))


def onCook(scriptOp):
    comp = me.parent()
    voices = int(comp.par.Voices.eval())

    names = []
    for i in range(1, voices + 1):
        names += ['gate%d' % i, 'note%d' % i, 'vel%d' % i,
                  'u%d' % i, 'v%d' % i, 'area%d' % i, 'id%d' % i]
    names += ['count', 'density', 'height', 'blobs_raw']

    def emit(values):
        # I canali si ricostruiscono a ogni cook: numChans non e' leggibile
        # mentre il CHOP cuoce, quindi non c'e' modo di sapere se quelli
        # esistenti sono ancora buoni. Su una sessantina di canali il costo
        # e' trascurabile.
        scriptOp.clear()
        scriptOp.numSamples = 1
        for n, v in zip(names, values):
            scriptOp.appendChan(n)[0] = float(v)

    # --- divisore di frame: leva diretta sugli fps ---
    rate = max(1, int(comp.par.Rate.eval()))
    if rate > 1 and (absTime.frame % rate) != 0:
        prev = comp.fetch('last_vals', None)
        emit(prev if (prev and len(prev) == len(names)) else [0.0] * len(names))
        return

    blobs = read_blobs(comp)
    raw_n = len(blobs)
    blobs = blobs[:voices]

    root      = int(comp.par.Rootnote.eval())
    octaves   = int(comp.par.Octaves.eval())
    scale     = str(comp.par.Scale.eval()).lower()
    velmin    = int(comp.par.Velmin.eval())
    velmax    = int(comp.par.Velmax.eval())
    velcurve  = float(comp.par.Velcurve.eval())
    areascale = float(comp.par.Areascale.eval())
    minage    = int(comp.par.Minage.eval())

    # Gli id del tracker sono persistenti, quindi uno slot resta del suo id
    # finche' l'id esiste. Niente riaggancio per posizione: lo fa gia' lui.
    slots = comp.fetch('slots', {}, storeDefault=True)
    present = {b[0]: b for b in blobs}

    for bid in [k for k in slots if k not in present]:
        del slots[bid]

    used = set(slots.values())
    free = [i for i in range(voices) if i not in used]
    for bid in present:
        if bid not in slots and free:
            slots[bid] = free.pop(0)
    comp.store('slots', slots)

    by_slot = {}
    for bid, sl in slots.items():
        if sl < voices:
            by_slot[sl] = present[bid]

    vals = [0.0] * len(names)
    live = 0
    total_area = 0.0
    sum_v = 0.0

    for vi in range(voices):
        b = by_slot.get(vi)
        if b is None:
            continue
        bid, u, v, area, age = b
        o = vi * 7
        vals[o + 3] = u
        vals[o + 4] = v
        vals[o + 5] = area
        vals[o + 6] = bid
        if age < minage:
            continue
        a = max(0.0, min(1.0, area / max(1e-6, areascale)))
        vals[o]     = 1.0
        vals[o + 1] = quantize(u, root, octaves, scale)
        vals[o + 2] = max(1, min(127, int(velmin + (velmax - velmin)
                                          * (a ** velcurve))))
        live += 1
        total_area += area
        sum_v += v

    base = voices * 7
    vals[base]     = live
    vals[base + 1] = min(1.0, total_area / max(1e-6, areascale * voices))
    vals[base + 2] = (sum_v / live) if live else 0.0
    vals[base + 3] = raw_n

    comp.store('last_vals', vals)
    emit(vals)
