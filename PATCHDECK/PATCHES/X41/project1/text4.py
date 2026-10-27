"""
build_blob_audio_v2.py
----------------------
Ricostruisce SOLO /project1/blob_audio. Il blob_tracker non viene toccato.

I valori dei parametri custom che hai gia' tarato vengono letti prima di
distruggere il COMP e riscritti dopo: Voices 5, pentatonica, Rootnote 54,
Velcurve 2.14 e compagnia restano come li hai messi.

NOVITA'

1. MIXER A TRE BANDE
   surge -> main_pick -> [bassi | medi | alti] -> guadagni -> mix ->
   limiter -> audioout
   main_pick prende solo chan1/chan2: Surge esce con 6 canali e finora
   andavano tutti all'uscita audio.
   Parametri: Gainlow/Gainmid/Gainhigh, i due punti di incrocio, e un
   limiter con soglia regolabile - con voci che si accavallano i picchi
   arrivano, e in mostra e' quello che fa saltare l'impianto.

2. SELEZIONE BLOB
   Selectmode: per area (come prima), per zona dello schermo, per eta',
   o per lista di id. Invertibile.
   Cosi' puoi far suonare solo una porzione dell'inquadratura, o solo le
   incrostazioni piu' vecchie.

3. CORRELAZIONE ARMONICA
   Uselinks legge links_table, finora inutilizzata. Il blob piu' grande
   fa da ancora: i blob collegati a lui non prendono piu' l'altezza dalla
   loro posizione, ma un intervallo rispetto all'ancora.
   Harmony: quinte, terze, ottave, cluster.
   I blob non collegati restano indipendenti, quindi senti la differenza
   fra grappoli connessi e organismi isolati.

USO
  Text DAT in /project1, incolla, Run Script.
"""

PARENT_PATH = '/project1'
AUDIO_NAME  = 'blob_audio'
TRACKER     = '/project1/blob_tracker'
SURGE_PATH  = '/Library/Audio/Plug-Ins/VST3/Surge XT.vst3'


# ===========================================================================
VST_SEND = r'''
def _comp():
    return me.parent()


def _candidates(kind, ch, a, b):
    if kind == 'on':
        return [('sendNoteOn', (ch, a, b)), ('noteOn', (ch, a, b))]
    if kind == 'off':
        return [('sendNoteOff', (ch, a, 0)), ('noteOff', (ch, a))]
    return [('sendControl', (ch, a, b)), ('sendControlChange', (ch, a, b))]


def _dispatch(kind, ch, a, b):
    c = _comp()
    if c.fetch('vst_dead', False):
        return False
    vst = c.op('surge')
    if vst is None:
        return False

    cached = c.fetch('vst_m_' + kind, None)
    if cached is not None:
        for n, args in _candidates(kind, ch, a, b):
            if n == cached:
                try:
                    getattr(vst, n)(*args)
                    return True
                except Exception:
                    c.store('vst_m_' + kind, None)
                break

    for n, args in _candidates(kind, ch, a, b):
        fn = getattr(vst, n, None)
        if fn is None:
            continue
        try:
            fn(*args)
            c.store('vst_m_' + kind, n)
            return True
        except Exception:
            continue

    c.store('vst_dead', True)
    debug('blob_audio: invio fallito. metodi:',
          [m for m in dir(vst) if m.startswith('send')])
    return False


def note_on(ch, note, vel):
    return _dispatch('on', ch, int(note), int(vel))


def note_off(ch, note):
    return _dispatch('off', ch, int(note), 0)


def control(ch, num, val):
    return _dispatch('cc', ch, int(num), int(val))


def all_off(ch):
    c = _comp()
    c.store('vst_dead', False)
    vst = c.op('surge')
    if vst is None:
        return
    fn = getattr(vst, 'sendAllNotesOff', None)
    if fn is not None:
        try:
            fn(ch)
            return
        except Exception:
            pass
    for n in range(128):
        note_off(ch, n)
'''


# ===========================================================================
VOICES_SCRIPT = r'''
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
'''


# ===========================================================================
NOTE_EXEC = r'''
def _slot(name):
    try:
        return int(name[4:])
    except ValueError:
        return None


def onOffToOn(channel, sampleIndex, val, prev):
    comp = me.parent()
    if not comp.par.Audioon.eval():
        return
    i = _slot(channel.name)
    if i is None:
        return
    src = comp.op('blob_voices')
    note = int(src['note%d' % i][0])
    if note <= 0:
        return
    comp.store('held%d' % i, note)
    mod('vst_send').note_on(int(comp.par.Midichannel.eval()), note,
                            int(src['vel%d' % i][0]))


def onOnToOff(channel, sampleIndex, val, prev):
    comp = me.parent()
    i = _slot(channel.name)
    if i is None:
        return
    note = comp.fetch('held%d' % i, 0)
    if note:
        mod('vst_send').note_off(int(comp.par.Midichannel.eval()), note)
        comp.store('held%d' % i, 0)
'''


CC_EXEC = r'''
CC_FOR = {'count': 'Cccount', 'density': 'Ccdensity', 'height': 'Ccheight'}


def onValueChange(channel, sampleIndex, val, prev):
    comp = me.parent()
    if not comp.par.Audioon.eval() or not comp.par.Sendcc.eval():
        return
    parname = CC_FOR.get(channel.name)
    if parname is None:
        return
    num = int(getattr(comp.par, parname).eval())
    if num < 0:
        return
    v = val / max(1, int(comp.par.Voices.eval())) if channel.name == 'count' else val
    q = int(max(0, min(127, v * 127)))
    key = 'cc_last_' + channel.name
    if comp.fetch(key, -1) == q:
        return
    comp.store(key, q)
    mod('vst_send').control(int(comp.par.Midichannel.eval()), num, q)
'''


PAR_EXEC = r'''
def onPulse(par):
    comp = par.owner
    if par.name == 'Panic':
        mod(comp.path + '/vst_send').all_off(int(comp.par.Midichannel.eval()))
        comp.store('slots', {})
        comp.store('vst_dead', False)
        for k in ('on', 'off', 'cc'):
            comp.store('vst_m_' + k, None)
        print('blob_audio: note spente, invio riabilitato')
    elif par.name == 'Testnote':
        mod(comp.path + '/vst_send').note_on(int(comp.par.Midichannel.eval()), 60, 100)
        run("mod('%s/vst_send').note_off(%d, 60)"
            % (comp.path, int(comp.par.Midichannel.eval())), delayFrames=45)
    elif par.name == 'Flatmix':
        for p in ('Gainlow', 'Gainmid', 'Gainhigh'):
            getattr(comp.par, p).val = 1.0
        print('blob_audio: mixer azzerato a guadagno unitario')
    elif par.name == 'Diagnose':
        diagnose(comp)
    elif par.name == 'Openvst':
        vst = comp.op('surge')
        for m in ('openViewer', 'openPluginUI'):
            fn = getattr(vst, m, None)
            if fn is not None:
                try:
                    fn()
                    return
                except Exception:
                    pass
        print('apri la UI dal parametro Display Plugin GUI del nodo surge')
    return


def diagnose(comp):
    print('=' * 66)
    print('blob_audio')
    print('-' * 66)
    v = comp.op('blob_voices')
    if v is not None:
        nv = int(comp.par.Voices.eval())
        try:
            print('blob totali %d, selezionati %d, in voce %d'
                  % (int(v['blobs_raw'][0]), int(v['selected'][0]),
                     int(v['count'][0])))
            print('gate  ', [int(v['gate%d' % (i + 1)][0]) for i in range(nv)])
            print('note  ', [int(v['note%d' % (i + 1)][0]) for i in range(nv)])
            print('id    ', [int(v['id%d' % (i + 1)][0]) for i in range(nv)])
            print('legati', [int(v['linked%d' % (i + 1)][0]) for i in range(nv)])
        except Exception as e:
            print('voci non leggibili:', e)
    print('selezione: %s%s' % (comp.par.Selectmode.eval(),
                               ' (invertita)' if comp.par.Invertsel.eval() else ''))
    print('correlazione:', bool(comp.par.Uselinks.eval()), comp.par.Harmony.eval())
    for n in ('surge', 'main_pick', 'mix', 'limiter', 'audioout'):
        o = comp.op(n)
        if o is None:
            print('%-10s ASSENTE' % n)
        else:
            print('%-10s %s | %d canali' % (n, o.type, o.numChans))
            err = o.errors()
            if err:
                print('           ERRORI:', err[:300])
    print('=' * 66)
'''


# ===========================================================================
REPORT = []


def _cls(*names):
    import td
    for n in names:
        c = getattr(td, n, None)
        if c is not None:
            return c
    return None


def _make(comp, name, *cn):
    c = _cls(*cn)
    if c is None:
        REPORT.append('MANCA      %-14s (%s)' % (name, ', '.join(cn)))
        return None
    o = comp.create(c, name)
    REPORT.append('ok         %-14s %s' % (name, o.type))
    return o


def _set(o, value, *parnames):
    if o is None:
        return False
    for p in parnames:
        try:
            setattr(o.par, p, value)
            return True
        except Exception:
            continue
    REPORT.append('   %s: nessuno di %s accetta %r'
                  % (o.name, '/'.join(parnames), value))
    return False


def _expr(o, expr, *parnames):
    if o is None:
        return False
    for p in parnames:
        try:
            getattr(o.par, p).expr = expr
            return True
        except Exception:
            continue
    REPORT.append('   %s: espressione non applicata a %s'
                  % (o.name, '/'.join(parnames)))
    return False


def _link(a, b, i=0):
    if a is None or b is None:
        return
    try:
        b.inputConnectors[i].connect(a)
    except Exception as e:
        REPORT.append('   collegamento %s -> %s fallito (%s)' % (a.name, b.name, e))


# ===========================================================================
def build():
    REPORT.clear()
    parent_comp = op(PARENT_PATH)
    old = parent_comp.op(AUDIO_NAME)

    # --- salva le tarature ---
    saved = {}
    if old is not None:
        for p in old.customPars:
            try:
                if str(p.style) == 'Pulse':
                    continue
                saved[p.name] = p.val
            except Exception:
                continue
        REPORT.append('salvati    %d valori dal COMP precedente' % len(saved))

    tmp = AUDIO_NAME + '_building'
    if parent_comp.op(tmp):
        parent_comp.op(tmp).destroy()
    comp = parent_comp.create(_cls('baseCOMP'), tmp)

    _pars(comp)
    filt = _network(comp)
    _layout(comp)

    if old is not None:
        old.destroy()
    comp.name = AUDIO_NAME
    comp.nodeX, comp.nodeY = 450, 300

    # --- ripristina le tarature ---
    n = 0
    for name, val in saved.items():
        par = getattr(comp.par, name, None)
        if par is None:
            continue
        try:
            par.val = val
            n += 1
        except Exception:
            continue
    REPORT.append('ripristinati %d valori' % n)

    _pulse_handler(parent_comp, comp)

    print('=' * 66)
    print('blob_audio v2 - report')
    print('-' * 66)
    for r in REPORT:
        print(' ', r)
    if filt is not None:
        print('-' * 66)
        print(' PARAMETRI DEL FILTRO AUDIO (%s):' % filt.type)
        print('  ', [p.name for p in filt.pars()])
    print('=' * 66)


def _pars(comp):
    p = comp.appendCustomPage('Blob Audio')
    p.appendToggle('Audioon', label='Audio attivo')[0].default = True
    p.appendToggle('Sendcc', label='Invia CC')[0].default = True
    p.appendPulse('Testnote', label='Nota di prova')
    p.appendPulse('Panic', label='Panic')
    p.appendPulse('Diagnose', label='Diagnostica')
    p.appendPulse('Openvst', label='Apri UI VST')
    p.appendFile('Plugin', label='Plugin VST3')[0].default = SURGE_PATH
    r = p.appendInt('Rate', label='Elabora 1 frame ogni')[0]
    r.default, r.normMin, r.normMax = 1, 1, 10
    vo = p.appendInt('Voices', label='Voci')[0]
    vo.default, vo.normMin, vo.normMax = 8, 1, 24
    ma = p.appendInt('Minage', label='Eta minima per suonare')[0]
    ma.default, ma.normMin, ma.normMax = 4, 1, 60
    mc = p.appendInt('Midichannel', label='Canale MIDI')[0]
    mc.default, mc.normMin, mc.normMax = 1, 1, 16

    # --- selezione ---
    p = comp.appendCustomPage('Selezione')
    sm = p.appendMenu('Selectmode', label='Criterio')[0]
    sm.menuNames = ['area', 'zone', 'age', 'id']
    sm.menuLabels = ['Area', 'Zona schermo', 'Eta', 'Lista ID']
    sm.default = 'area'
    p.appendToggle('Invertsel', label='Inverti selezione')
    m = p.appendFloat('Minarea', label='Area minima')[0]
    m.default, m.normMin, m.normMax = 0.0, 0.0, 0.02
    for name, label, dv in (('Zoneumin', 'Zona U da', 0.0),
                            ('Zoneumax', 'Zona U a', 1.0),
                            ('Zonevmin', 'Zona V da', 0.0),
                            ('Zonevmax', 'Zona V a', 1.0)):
        z = p.appendFloat(name, label=label)[0]
        z.default, z.normMin, z.normMax = dv, 0.0, 1.0
    p.appendStr('Idlist', label='ID (separati da spazio)')

    # --- musica ---
    p = comp.appendCustomPage('Musica')
    s = p.appendMenu('Scale', label='Scala')[0]
    s.menuNames = ['chromatic', 'major', 'minor', 'dorian', 'penta', 'whole']
    s.menuLabels = ['Cromatica', 'Maggiore', 'Minore', 'Dorico',
                    'Pentatonica', 'Toni interi']
    s.default = 'minor'
    rn = p.appendInt('Rootnote', label='Fondamentale')[0]
    rn.default, rn.normMin, rn.normMax = 36, 0, 96
    oc = p.appendInt('Octaves', label='Ottave')[0]
    oc.default, oc.normMin, oc.normMax = 3, 1, 6
    v1 = p.appendInt('Velmin', label='Velocity min')[0]
    v1.default, v1.normMin, v1.normMax = 40, 1, 127
    v2 = p.appendInt('Velmax', label='Velocity max')[0]
    v2.default, v2.normMin, v2.normMax = 110, 1, 127
    vc = p.appendFloat('Velcurve', label='Curva velocity')[0]
    vc.default, vc.normMin, vc.normMax = 0.6, 0.2, 3.0
    ar = p.appendFloat('Areascale', label='Area di riferimento')[0]
    ar.default, ar.normMin, ar.normMax = 0.01, 0.0005, 0.1
    p.appendToggle('Uselinks', label='Correlazione fra blob')
    hm = p.appendMenu('Harmony', label='Intervalli')[0]
    hm.menuNames = ['fifths', 'thirds', 'octaves', 'cluster']
    hm.menuLabels = ['Quinte', 'Terze', 'Ottave', 'Cluster']
    hm.default = 'fifths'
    for name, label, default in (('Cccount', 'CC numero blob', 1),
                                 ('Ccdensity', 'CC densita', 11),
                                 ('Ccheight', 'CC altezza', 74)):
        c = p.appendInt(name, label=label)[0]
        c.default, c.normMin, c.normMax = default, -1, 127

    # --- mixer ---
    p = comp.appendCustomPage('Mixer')
    for name, label in (('Gainlow', 'Bassi'), ('Gainmid', 'Medi'),
                        ('Gainhigh', 'Alti')):
        g = p.appendFloat(name, label=label)[0]
        g.default, g.normMin, g.normMax = 1.0, 0.0, 2.0
    xl = p.appendFloat('Xoverlow', label='Incrocio bassi/medi (Hz)')[0]
    xl.default, xl.normMin, xl.normMax = 250.0, 40.0, 1000.0
    xh = p.appendFloat('Xoverhigh', label='Incrocio medi/alti (Hz)')[0]
    xh.default, xh.normMin, xh.normMax = 3000.0, 800.0, 12000.0
    p.appendToggle('Limiton', label='Limiter')[0].default = True
    ce = p.appendFloat('Ceiling', label='Soglia limiter')[0]
    ce.default, ce.normMin, ce.normMax = 0.9, 0.1, 1.0
    vol = p.appendFloat('Volume', label='Volume uscita')[0]
    vol.default, vol.normMin, vol.normMax = 0.7, 0.0, 1.0
    p.appendPulse('Flatmix', label='Azzera mixer')

    # i default non diventano valori da soli: vanno scritti
    for par in comp.customPars:
        try:
            if str(par.style) == 'Pulse':
                continue
            par.val = par.default
        except Exception:
            pass


def _network(comp):
    sel = _make(comp, 'blobs_in', 'selectDAT')
    _set(sel, TRACKER + '/blob_table', 'dat')
    lnk = _make(comp, 'links_in', 'selectDAT')
    _set(lnk, TRACKER + '/links_table', 'dat')

    send = _make(comp, 'vst_send', 'textDAT')
    if send is not None:
        send.text = VST_SEND

    cbd = _make(comp, 'blob_voices_callbacks', 'textDAT')
    if cbd is not None:
        cbd.text = VOICES_SCRIPT
    vs = _make(comp, 'blob_voices', 'scriptCHOP')
    _set(vs, 'blob_voices_callbacks', 'callbacks')

    vout = _make(comp, 'voices_out', 'outCHOP')
    _link(vs, vout)

    ne = _make(comp, 'note_exec', 'chopexecuteDAT')
    if ne is not None:
        ne.text = NOTE_EXEC
        _set(ne, 'blob_voices', 'chop')
        _expr(ne, 'parent()', 'fromop')
        _set(ne, 'gate*', 'channels', 'channel')
        _set(ne, True, 'offtoon')
        _set(ne, True, 'ontooff')
        _set(ne, False, 'valuechange')

    ce = _make(comp, 'cc_exec', 'chopexecuteDAT')
    if ce is not None:
        ce.text = CC_EXEC
        _set(ce, 'blob_voices', 'chop')
        _expr(ce, 'parent()', 'fromop')
        _set(ce, 'count density height', 'channels', 'channel')
        _set(ce, True, 'valuechange')
        _set(ce, False, 'offtoon')
        _set(ce, False, 'ontooff')

    # --- plugin ---
    _make(comp, 'surge_callbacks', 'textDAT')
    vst = _make(comp, 'surge', 'audiovstCHOP')
    _expr(vst, 'parent().par.Plugin', 'file')
    _set(vst, 'surge_callbacks', 'callbacks')
    _set(vst, True, 'timeslice')

    # --- mixer ---
    # Surge esce con 6 canali: il main stereo e' chan1/chan2, il resto sono
    # uscite di scena che finora andavano dritte all'impianto.
    pick = _make(comp, 'main_pick', 'selectCHOP')
    _link(vst, pick)
    _set(pick, 'chan1 chan2', 'channames', 'channel')

    flow = _make(comp, 'f_low', 'audiofilterCHOP')
    _link(pick, flow)
    _set(flow, 'lowpass', 'filter', 'type', 'filtertype')
    _expr(flow, 'parent().par.Xoverlow', 'cutofflog', 'cutoff', 'frequency')

    fmid_hi = _make(comp, 'f_mid_hp', 'audiofilterCHOP')
    _link(pick, fmid_hi)
    _set(fmid_hi, 'highpass', 'filter', 'type', 'filtertype')
    _expr(fmid_hi, 'parent().par.Xoverlow', 'cutofflog', 'cutoff', 'frequency')

    fmid = _make(comp, 'f_mid', 'audiofilterCHOP')
    _link(fmid_hi, fmid)
    _set(fmid, 'lowpass', 'filter', 'type', 'filtertype')
    _expr(fmid, 'parent().par.Xoverhigh', 'cutofflog', 'cutoff', 'frequency')

    fhigh = _make(comp, 'f_high', 'audiofilterCHOP')
    _link(pick, fhigh)
    _set(fhigh, 'highpass', 'filter', 'type', 'filtertype')
    _expr(fhigh, 'parent().par.Xoverhigh', 'cutofflog', 'cutoff', 'frequency')

    gains = []
    for src, name, par in ((flow, 'g_low', 'Gainlow'),
                           (fmid, 'g_mid', 'Gainmid'),
                           (fhigh, 'g_high', 'Gainhigh')):
        g = _make(comp, name, 'mathCHOP')
        _link(src, g)
        _expr(g, 'parent().par.%s' % par, 'gain')
        gains.append(g)

    mix = _make(comp, 'mix', 'mathCHOP')
    for i, g in enumerate(gains):
        _link(g, mix, i)
    _set(mix, 'add', 'chopop', 'chanop')

    lim = _make(comp, 'limiter', 'limitCHOP')
    _link(mix, lim)
    _set(lim, 'clamp', 'type', 'limittype')
    _expr(lim, '-parent().par.Ceiling if parent().par.Limiton else -10', 'min')
    _expr(lim, 'parent().par.Ceiling if parent().par.Limiton else 10', 'max')

    dev = _make(comp, 'audioout', 'audiodeviceoutCHOP', 'audiodevoutCHOP')
    _link(lim if lim is not None else mix, dev)
    _expr(dev, 'parent().par.Volume', 'volume')

    aout = _make(comp, 'audio_out', 'outCHOP')
    _link(lim if lim is not None else mix, aout)

    return flow


def _layout(comp):
    coords = {
        'blobs_in': (0, 500), 'links_in': (0, 400),
        'blob_voices_callbacks': (0, 300), 'blob_voices': (250, 450),
        'voices_out': (500, 450),
        'vst_send': (0, 150), 'note_exec': (250, 200), 'cc_exec': (500, 200),
        'surge_callbacks': (250, 60), 'surge': (250, -40),
        'main_pick': (450, -40),
        'f_low': (650, 60), 'f_mid_hp': (650, -40), 'f_mid': (800, -40),
        'f_high': (650, -140),
        'g_low': (950, 60), 'g_mid': (950, -40), 'g_high': (950, -140),
        'mix': (1150, -40), 'limiter': (1300, -40),
        'audioout': (1450, -40), 'audio_out': (1450, -160),
    }
    for n, (x, y) in coords.items():
        o = comp.op(n)
        if o is not None:
            o.nodeX, o.nodeY = x, y


def _pulse_handler(parent_comp, comp):
    name = AUDIO_NAME + '_pulse'
    if parent_comp.op(name):
        parent_comp.op(name).destroy()
    p = parent_comp.create(_cls('parameterexecuteDAT'), name)
    p.text = PAR_EXEC
    _set(p, AUDIO_NAME, 'op')
    _set(p, True, 'onpulse', 'pulse')
    _set(p, False, 'valuechange', 'value')
    p.nodeX, p.nodeY = comp.nodeX, comp.nodeY - 160


build()