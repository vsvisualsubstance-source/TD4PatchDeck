
SCALES = {
    'chromatic': [0,1,2,3,4,5,6,7,8,9,10,11],
    'major':     [0,2,4,5,7,9,11],
    'minor':     [0,2,3,5,7,8,10],
    'dorian':    [0,2,3,5,7,9,10],
    'penta':     [0,3,5,7,10],
    'whole':     [0,2,4,6,8,10],
}

# Intervalli in semitoni rispetto all'ancora, per i blob collegati
HARMONY = {
    'fifths':  [0, 7, 12, 19],
    'thirds':  [0, 3, 7, 10, 15],
    'octaves': [0, 12, -12, 24],
    'cluster': [0, 1, 2, -1, 3],
}

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
    debug('blob_audio - colonne:', header, '->', found)
    return found


def read_blobs(comp):
    """Legge blobs_in da .text con uno split: cella per cella costa troppo."""
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

    out = []
    for line in lines[1:MAXROWS + 1]:
        if not line:
            continue
        f = line.split('\t')
        try:
            bid = int(float(f[ii]))
            u = float(f[iu])
            v = float(f[iv])
            area = float(f[ia]) if ia is not None else 0.0
            age = int(float(f[ig])) if ig is not None else 999
        except (ValueError, IndexError):
            continue
        out.append((bid, u, v, area, age))
    return out


def read_links(comp):
    """links_table: ida idb dist. Ritorna {id: set(id collegati)}."""
    src = comp.op('links_in')
    if src is None:
        return {}
    txt = src.text
    if not txt:
        return {}
    lines = txt.split('\n')
    if len(lines) < 2:
        return {}
    adj = {}
    for line in lines[1:MAXROWS * 4 + 1]:
        if not line:
            continue
        f = line.split('\t')
        try:
            a = int(float(f[0]))
            b = int(float(f[1]))
        except (ValueError, IndexError):
            continue
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return adj


def select(comp, blobs):
    """Filtra e ordina secondo Selectmode. Ritorna la lista gia' in ordine
    di priorita': le prime N prendono le voci."""
    mode = str(comp.par.Selectmode.eval()).lower()
    inv = bool(comp.par.Invertsel.eval())
    minarea = float(comp.par.Minarea.eval())

    keep = [b for b in blobs if b[3] >= minarea]

    if mode == 'zone':
        u0 = float(comp.par.Zoneumin.eval())
        u1 = float(comp.par.Zoneumax.eval())
        v0 = float(comp.par.Zonevmin.eval())
        v1 = float(comp.par.Zonevmax.eval())
        inside = lambda b: (u0 <= b[1] <= u1) and (v0 <= b[2] <= v1)
        keep = [b for b in keep if inside(b) != inv]
        keep.sort(key=lambda b: b[3], reverse=True)

    elif mode == 'age':
        keep.sort(key=lambda b: b[4], reverse=not inv)

    elif mode == 'id':
        wanted = set()
        for tok in str(comp.par.Idlist.eval()).replace(',', ' ').split():
            try:
                wanted.add(int(tok))
            except ValueError:
                continue
        if wanted:
            keep = [b for b in keep if (b[0] in wanted) != inv]
        keep.sort(key=lambda b: b[3], reverse=True)

    else:  # area
        keep.sort(key=lambda b: b[3], reverse=not inv)

    return keep


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
                  'u%d' % i, 'v%d' % i, 'area%d' % i, 'id%d' % i,
                  'linked%d' % i]
    names += ['count', 'density', 'height', 'blobs_raw', 'selected']

    def emit(values):
        # Ricostruiti a ogni cook: numChans non e' leggibile mentre il CHOP
        # cuoce, quindi non c'e' modo di sapere se quelli esistenti valgono.
        scriptOp.clear()
        scriptOp.numSamples = 1
        for n, v in zip(names, values):
            scriptOp.appendChan(n)[0] = float(v)

    rate = max(1, int(comp.par.Rate.eval()))
    if rate > 1 and (absTime.frame % rate) != 0:
        prev = comp.fetch('last_vals', None)
        emit(prev if (prev and len(prev) == len(names)) else [0.0] * len(names))
        return

    allblobs = read_blobs(comp)
    chosen = select(comp, allblobs)
    picked = chosen[:voices]

    root      = int(comp.par.Rootnote.eval())
    octaves   = int(comp.par.Octaves.eval())
    scale     = str(comp.par.Scale.eval()).lower()
    velmin    = int(comp.par.Velmin.eval())
    velmax    = int(comp.par.Velmax.eval())
    velcurve  = float(comp.par.Velcurve.eval())
    areascale = float(comp.par.Areascale.eval())
    minage    = int(comp.par.Minage.eval())

    # --- allocazione voci sugli id del tracker (persistenti) ---
    slots = comp.fetch('slots', {}, storeDefault=True)
    present = {b[0]: b for b in picked}

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

    # --- altezze: prima quelle indipendenti ---
    notes = {}
    for bid, b in present.items():
        notes[bid] = quantize(b[1], root, octaves, scale)

    # --- correlazione: i blob collegati all'ancora si allineano a lei ---
    linked = set()
    if comp.par.Uselinks.eval() and present:
        harmony = HARMONY.get(str(comp.par.Harmony.eval()).lower())
        if harmony:
            adj = read_links(comp)
            # l'ancora e' il blob piu' grande fra quelli che suonano
            anchor = max(present.values(), key=lambda b: b[3])[0]
            neighbours = adj.get(anchor, set())
            k = 0
            for bid in sorted(present):
                if bid == anchor or bid not in neighbours:
                    continue
                k += 1
                off = harmony[k % len(harmony)]
                notes[bid] = int(max(0, min(127, notes[anchor] + off)))
                linked.add(bid)

    # --- scrittura ---
    vals = [0.0] * len(names)
    live = 0
    total_area = 0.0
    sum_v = 0.0

    for vi in range(voices):
        b = by_slot.get(vi)
        if b is None:
            continue
        bid, u, v, area, age = b
        o = vi * 8
        vals[o + 3] = u
        vals[o + 4] = v
        vals[o + 5] = area
        vals[o + 6] = bid
        vals[o + 7] = 1.0 if bid in linked else 0.0
        if age < minage:
            continue
        a = max(0.0, min(1.0, area / max(1e-6, areascale)))
        vals[o]     = 1.0
        vals[o + 1] = notes[bid]
        vals[o + 2] = max(1, min(127, int(velmin + (velmax - velmin)
                                          * (a ** velcurve))))
        live += 1
        total_area += area
        sum_v += v

    base = voices * 8
    vals[base]     = live
    vals[base + 1] = min(1.0, total_area / max(1e-6, areascale * voices))
    vals[base + 2] = (sum_v / live) if live else 0.0
    vals[base + 3] = len(allblobs)
    vals[base + 4] = len(chosen)

    comp.store('last_vals', vals)
    emit(vals)
