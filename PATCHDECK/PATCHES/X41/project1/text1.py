"""
build_balani.py
---------------
Build completa da zero. Non copia niente da /project1: il codice del
tracker e' dentro questo file e viene scritto nel Text DAT dei callback.

CREA

  /project1/blob_tracker
      source -> detect_res -> script1 -> video_out
      script1 scrive blob_table e links_table
      uscite: video_out (TOP), blobs_out (DAT), links_out (DAT)

  /project1/blob_audio
      blobs_in -> blob_voices -> note_exec -> surge -> audioout
      uscita: voices_out (CHOP con gate/note/vel/u/v/area/id per voce)

  collegati:  blob_tracker -> blob_audio

USO
  Text DAT nuovo in /project1, incolla questo file, tasto destro > Run
  Script. Poi controlla il percorso del video nel parametro Source del
  blob_tracker.

NOTE
  - sendNoteOn / sendNoteOff (canale, pitch, velocity) e' il metodo
    confermato dell'Audio VST CHOP in questa build.
  - Le voci si allocano sugli id del tracker, che sono persistenti.
  - detect_res permette di far girare OpenCV a risoluzione ridotta:
    e' li' che se ne vanno gli fps a 1080p con Blocco adattivo 151.
    Se lo accendi, riscala i parametri in pixel come da intestazione
    di blobtrack_bio.
"""

PARENT_PATH  = '/project1'
TRACKER_NAME = 'blob_tracker'
AUDIO_NAME   = 'blob_audio'
SURGE_PATH   = '/Library/Audio/Plug-Ins/VST3/Surge XT.vst3'
VIDEO_PATH   = '/Users/nicolavilla/Downloads/04_09_2026_master_120s_slow80_1080_apo8.mp4'
VOICES       = 8


# ===========================================================================
# blobtrack_bio - callbacks dello Script TOP
# ===========================================================================
TRACKER_CODE = r'''
# =============================================================
# blobtrack_bio.py
# Callbacks DAT per uno Script TOP di TouchDesigner.
#
# Traccia formazioni biologiche (balani, incrostazioni, alghe)
# su un video e disegna punti, linee di collegamento e testi.
#
# I default sono tarati su un frame 1920x1080 di questo materiale
# (37 blob agganciati). Sfocatura, Blocco adattivo e Pulizia
# morfologica sono in pixel: se lavori a 1280x720 scalali di ~0.67
# (blocco 101, sfocatura 11, morph 5). Area minima e massima sono
# normalizzate sull'area del frame, quelle non si toccano.
#
# Se i parametri restano a zero: pulsante "Ripristina default"
# nella pagina Detection.
# =============================================================

import numpy as np
import cv2

TRACKS = {}
NEXT_ID = [1]
STATS = {'new': 0, 'lost': 0, 'peak': 0}
HISTORY = []

SPECS = [
 ('Detection', [
  ('Toggle', 'Active',    'Attivo',              1,      {}),
  ('Int',    'Blurw',     'Sfocatura',           15,     {'min': 1, 'max': 51, 'clampMin': True}),
  ('Menu',   'Method',    'Soglia',       'adaptive',    {'menuNames':  ['fixed', 'otsu', 'adaptive'],
                                                          'menuLabels': ['Fissa', 'Otsu (auto)', 'Adattiva']}),
  ('Float',  'Threshold', 'Livello soglia',      0.5,    {'normMin': 0.0, 'normMax': 1.0}),
  ('Int',    'Blocksize', 'Blocco adattivo',     151,    {'min': 3, 'max': 201, 'clampMin': True}),
  ('Float',  'Adaptc',    'Offset adattivo',     6.0,    {'normMin': -20.0, 'normMax': 20.0}),
  ('Toggle', 'Invert',    'Inverti maschera',    0,      {}),
  ('Int',    'Morph',     'Pulizia morfologica', 7,      {'min': 0, 'max': 25, 'clampMin': True}),
  ('Float',  'Minarea',   'Area minima',         0.0006, {'normMin': 0.0, 'normMax': 0.01}),
  ('Float',  'Maxarea',   'Area massima',        0.03,   {'normMin': 0.0, 'normMax': 0.5}),
  ('Int',    'Maxblobs',  'Numero max blob',     40,     {'min': 1, 'max': 400, 'clampMin': True}),
  ('Pulse',  'Resetids',  'Azzera ID',           None,   {}),
  ('Pulse',  'Restoredefaults', 'Ripristina default', None, {}),
 ]),
 ('Tracking', [
  ('Float',  'Matchdist',  'Raggio di aggancio',       0.06, {'normMin': 0.0, 'normMax': 0.3}),
  ('Int',    'Maxmissing', 'Frame di tolleranza',      8,    {'min': 0, 'max': 120, 'clampMin': True}),
  ('Int',    'Minage',     'Eta minima per disegnare', 2,    {'min': 0, 'max': 120, 'clampMin': True}),
  ('Float',  'Smooth',     'Smorzamento',              0.5,  {'normMin': 0.0, 'normMax': 0.99}),
 ]),
 ('Grafica', [
  ('Toggle', 'Overlay',       'Sopra il video',          1,    {}),
  ('Float',  'Dim',           'Scurisci sfondo',         0.35, {'normMin': 0.0, 'normMax': 1.0}),
  ('Toggle', 'Showpoint',     'Punto',                   1,    {}),
  ('Toggle', 'Showrect',      'Rettangolo',              1,    {}),
  ('Toggle', 'Cornersonly',   'Rettangolo: solo angoli', 0,    {}),
  ('Float',  'Pointradius',   'Raggio punto',            6.0,  {'normMin': 1.0, 'normMax': 60.0}),
  ('Int',    'Pointthick',    'Spessore punto (-1 pieno)', 2,  {'min': -1, 'max': 20}),
  ('RGB',    'Pointcolor',    'Colore punto',   [0.98, 0.96, 0.90], {}),
  ('Toggle', 'Scalebyarea',   'Raggio da area',          1,    {}),
  ('Int',    'Boxthick',      'Spessore rettangolo',     1,    {'min': 1, 'max': 10}),
  ('Float',  'Boxpad',        'Margine rettangolo',      4.0,  {'normMin': 0.0, 'normMax': 40.0}),
  ('Float',  'Cornerlen',     'Lunghezza angoli',        0.30, {'normMin': 0.05, 'normMax': 0.5}),
  ('RGB',    'Boxcolor',      'Colore rettangolo', [0.20, 0.95, 0.75], {}),
  ('Toggle', 'Showlines',     'Linee',                   1,    {}),
  ('Float',  'Linkdist',      'Distanza collegamento',   0.18, {'normMin': 0.0, 'normMax': 1.0}),
  ('Int',    'Maxlinks',      'Link per blob',           3,    {'min': 0, 'max': 20, 'clampMin': True}),
  ('Int',    'Linethick',     'Spessore linea',          1,    {'min': 1, 'max': 10}),
  ('RGB',    'Linecolor',     'Colore linea',   [0.55, 0.80, 0.85], {}),
  ('Float',  'Linealpha',     'Opacita linea',           0.45, {'normMin': 0.0, 'normMax': 1.0}),
  ('Toggle', 'Fadebylength',  'Sfuma per lunghezza',     1,    {}),
  ('Toggle', 'Showlabels',    'Testi',                   1,    {}),
  ('Str',    'Labeltemplate', 'Template testo', 'ID{id}  A{area:.4f}', {}),
  ('Float',  'Fontscale',     'Corpo testo',             0.4,  {'normMin': 0.1, 'normMax': 3.0}),
  ('Int',    'Fontthick',     'Spessore testo',          1,    {'min': 1, 'max': 6}),
  ('RGB',    'Textcolor',     'Colore testo',   [1.0, 1.0, 1.0], {}),
  ('XY',     'Labeloffset',   'Offset testo',   [10.0, -10.0], {}),
  ('Toggle', 'Labelleader',   'Trattino di richiamo',    1,    {}),
 ]),
 ('Counter', [
  ('Toggle', 'Showcounter',  'Contatore',               1,    {}),
  ('Menu',   'Counterpos',   'Posizione',        'topleft',
      {'menuNames':  ['topleft', 'topright', 'bottomleft', 'bottomright'],
       'menuLabels': ['Alto sx', 'Alto dx', 'Basso sx', 'Basso dx']}),
  ('Str',    'Countertemplate', 'Template contatore',
      'BLOB {count}   NUOVI {new}   PICCO {peak}   TOT {total}', {}),
  ('Float',  'Counterscale', 'Corpo contatore',         0.55, {'normMin': 0.2, 'normMax': 2.0}),
  ('Int',    'Counterthick', 'Spessore contatore',      1,    {'min': 1, 'max': 6}),
  ('RGB',    'Countercolor', 'Colore contatore', [1.0, 1.0, 1.0], {}),
  ('Int',    'Countermargin', 'Margine dal bordo',      24,   {'min': 0, 'max': 300}),
  ('Toggle', 'Panel',        'Pannello di fondo',       0,    {}),
  ('Toggle', 'Countershadow', 'Contorno scuro',         1,    {}),
  ('Float',  'Panelalpha',   'Opacita pannello',        0.55, {'normMin': 0.0, 'normMax': 1.0}),
  ('Toggle', 'Showgraph',    'Grafico andamento',       1,    {}),
  ('Int',    'Graphlen',     'Frame di storico',        120,  {'min': 8, 'max': 900, 'clampMin': True}),
  ('Int',    'Graphheight',  'Altezza grafico',         38,   {'min': 8, 'max': 300}),
  ('Int',    'Graphwidth',   'Larghezza grafico',       260,  {'min': 40, 'max': 1200}),
  ('RGB',    'Graphcolor',   'Colore grafico',   [0.20, 0.95, 0.75], {}),
 ]),
 ('Griglia', [
  ('Toggle', 'Showgrid',    'Griglia numerica',       1,    {}),
  ('Menu',   'Gridpos',     'Posizione',      'bottomleft',
      {'menuNames':  ['topleft', 'topright', 'bottomleft', 'bottomright'],
       'menuLabels': ['Alto sx', 'Alto dx', 'Basso sx', 'Basso dx']}),
  ('Menu',   'Gridsort',    'Ordinamento',        'id',
      {'menuNames':  ['id', 'area', 'x', 'y', 'age'],
       'menuLabels': ['ID', 'Area', 'X', 'Y', 'Eta']}),
  ('Str',    'Gridheader',  'Intestazione',  'ID   X     Y', {}),
  ('Str',    'Gridrow',     'Riga',   '{id:03d} {x:.3f} {y:.3f}', {}),
  ('Str',    'Gridfooter',  'Piede',              'N={count}', {}),
  ('Int',    'Gridmax',     'Righe massime',      24,   {'min': 1, 'max': 200, 'clampMin': True}),
  ('Int',    'Gridcols',    'Colonne',            1,    {'min': 1, 'max': 6, 'clampMin': True}),
  ('Float',  'Gridscale',   'Corpo griglia',      0.40, {'normMin': 0.2, 'normMax': 1.5}),
  ('Int',    'Gridthick',   'Spessore griglia',   1,    {'min': 1, 'max': 4}),
  ('Int',    'Gridleading', 'Interlinea',         14,   {'min': 6, 'max': 80}),
  ('Toggle', 'Gridmono',    'Passo fisso',        1,    {}),
  ('RGB',    'Gridcolor',   'Colore griglia', [0.75, 0.95, 1.0], {}),
  ('Toggle', 'Gridpanel',   'Pannello di fondo',  0,    {}),
  ('Toggle', 'Gridshadow',  'Contorno scuro',     1,    {}),
  ('Float',  'Gridpanelalpha', 'Opacita pannello', 0.55, {'normMin': 0.0, 'normMax': 1.0}),
  ('Int',    'Gridmargin',  'Margine dal bordo',  24,   {'min': 0, 'max': 300}),
 ]),
 ('Dati', [
  ('DAT', 'Outputdat', 'Tabella blob', None, {}),
  ('DAT', 'Linksdat',  'Tabella link', None, {}),
 ]),
]

_SUFFIX = {'RGB': 'r', 'XY': 'x'}

OBSOLETE = ['Marker', 'Showpoints']


def _build(scriptOp, force=False):
    """Crea le pagine. force=True riscrive anche i valori esistenti."""

    for name in OBSOLETE:
        par = getattr(scriptOp.par, name, None)
        if par is not None:
            try:
                par.destroy()
            except Exception:
                pass

    for pagename, specs in SPECS:
        page = scriptOp.appendCustomPage(pagename)
        for kind, name, label, default, extra in specs:

            probe = name + _SUFFIX.get(kind, '')
            fresh = getattr(scriptOp.par, probe, None) is None

            pg = getattr(page, 'append' + kind)(name, label=label)

            # gli attributi vanno prima del valore:
            # un Menu deve conoscere i suoi nomi per accettare una stringa
            for par in pg:
                for k, v in extra.items():
                    try:
                        setattr(par, k, v)
                    except Exception:
                        pass

            if default is None:
                continue

            vals = default if isinstance(default, (list, tuple)) else [default]
            for i, par in enumerate(pg):
                v = vals[i] if i < len(vals) else vals[-1]
                par.default = v
                if fresh or force:
                    par.val = v


def onSetupParameters(scriptOp):
    _build(scriptOp, force=False)


def _reset():
    TRACKS.clear()
    NEXT_ID[0] = 1
    HISTORY.clear()
    STATS.update({'new': 0, 'lost': 0, 'peak': 0})


def onPulse(par):
    if par.name == 'Resetids':
        _reset()
    elif par.name == 'Restoredefaults':
        _reset()
        _build(par.owner, force=True)
    return


# =============================================================
# UTILITY
# =============================================================
def _odd(v, lo=1):
    v = int(v)
    if v < lo:
        v = lo
    return v if v % 2 == 1 else v + 1


def _fmt(template, data):
    try:
        return template.format(**data)
    except Exception:
        return template


def _detect(gray, s, w, h):
    k = _odd(s['blurw'])
    if k > 1:
        gray = cv2.GaussianBlur(gray, (k, k), 0)

    m = s['method']
    if m == 'fixed':
        _, mask = cv2.threshold(gray, s['threshold'] * 255.0, 255, cv2.THRESH_BINARY)
    elif m == 'otsu':
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        mask = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
            _odd(s['blocksize'], 3), float(s['adaptc']))

    if s['invert']:
        mask = 255 - mask

    mk = int(s['morph'])
    if mk > 0:
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (_odd(mk), _odd(mk)))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, ker)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, ker)

    cnts = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

    frame_area = float(w * h)
    out = []
    for c in cnts:
        a = cv2.contourArea(c)
        if a <= 0:
            continue
        an = a / frame_area
        if an < s['minarea'] or an > s['maxarea']:
            continue
        M = cv2.moments(c)
        if M['m00'] == 0:
            continue
        bx, by, bw, bh = cv2.boundingRect(c)
        out.append((M['m10'] / M['m00'], M['m01'] / M['m00'], an, bx, by, bw, bh))

    out.sort(key=lambda d: d[2], reverse=True)
    return out[:int(s['maxblobs'])]


def _track(dets, s, w):
    maxd = s['matchdist'] * w
    used = set()

    # le track piu' vecchie scelgono per prime: sono le piu' affidabili
    for tid in sorted(TRACKS, key=lambda i: -TRACKS[i]['age']):
        t = TRACKS[tid]
        best, bestd = -1, maxd
        for i, d in enumerate(dets):
            if i in used:
                continue
            dist = ((d[0] - t['p'][0]) ** 2 + (d[1] - t['p'][1]) ** 2) ** 0.5
            if dist < bestd:
                best, bestd = i, dist
        if best >= 0:
            d = dets[best]
            used.add(best)
            a = s['smooth']
            t['p'] = (t['p'][0] * a + d[0] * (1 - a), t['p'][1] * a + d[1] * (1 - a))
            t['area'] = t['area'] * a + d[2] * (1 - a)
            nb = (d[3], d[4], d[5], d[6])
            t['bb'] = tuple(t['bb'][i] * a + nb[i] * (1 - a) for i in range(4))
            t['wh'] = (d[5], d[6])
            t['age'] += 1
            t['miss'] = 0
        else:
            t['miss'] += 1

    created = 0
    for i, d in enumerate(dets):
        if i in used:
            continue
        TRACKS[NEXT_ID[0]] = {'p': (d[0], d[1]), 'area': d[2],
                              'bb': (d[3], d[4], d[5], d[6]),
                              'wh': (d[5], d[6]), 'age': 1, 'miss': 0}
        NEXT_ID[0] += 1
        created += 1

    dropped = [i for i, t in TRACKS.items() if t['miss'] > s['maxmissing']]
    for tid in dropped:
        del TRACKS[tid]

    STATS['new'] = created
    STATS['lost'] = len(dropped)


def _links(items, s, w):
    maxd = s['linkdist'] * w
    nmax = int(s['maxlinks'])
    pairs = {}
    for tid, t in items:
        cand = []
        for oid, o in items:
            if oid == tid:
                continue
            d = ((t['p'][0] - o['p'][0]) ** 2 + (t['p'][1] - o['p'][1]) ** 2) ** 0.5
            if d <= maxd:
                cand.append((d, oid))
        cand.sort()
        for d, oid in cand[:nmax]:
            key = (min(tid, oid), max(tid, oid))
            if key not in pairs:
                pairs[key] = d
    return pairs, maxd


def _counter(canvas, P, n, nlinks, live, w, h):
    """Pannello contatore + sparkline dell'andamento."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = P.Counterscale.eval()
    thick = int(P.Counterthick.eval())
    cc = tuple(int(getattr(P, k).eval() * 255)
               for k in ('Countercolorr', 'Countercolorg', 'Countercolorb'))
    gc = tuple(int(getattr(P, k).eval() * 255)
               for k in ('Graphcolorr', 'Graphcolorg', 'Graphcolorb'))

    tot_area = sum(t['area'] for _, t in live)
    data = {'count': n, 'new': STATS['new'], 'lost': STATS['lost'],
            'peak': STATS['peak'], 'total': NEXT_ID[0] - 1,
            'links': nlinks, 'area': tot_area,
            'avgarea': (tot_area / n) if n else 0.0,
            'frame': int(absTime.frame)}
    txt = _fmt(P.Countertemplate.eval(), data)

    (tw, tht), bl = cv2.getTextSize(txt, font, scale, thick)

    graph = P.Showgraph.eval()
    gw = int(P.Graphwidth.eval()) if graph else 0
    gh = int(P.Graphheight.eval()) if graph else 0
    gap = 10 if graph else 0

    panel = P.Panel.eval()
    shadow = P.Countershadow.eval()
    pad = 12 if panel else 3
    boxw = max(tw, gw) + pad * 2
    boxh = tht + bl + gap + gh + pad * 2

    mg = int(P.Countermargin.eval())
    pos = P.Counterpos.eval()
    x = mg if pos in ('topleft', 'bottomleft') else max(0, w - boxw - mg)
    y = mg if pos in ('topleft', 'topright') else max(0, h - boxh - mg)

    x2, y2 = min(w, x + boxw), min(h, y + boxh)
    if x2 <= x or y2 <= y:
        return canvas

    if panel:
        a = P.Panelalpha.eval()
        roi = canvas[y:y2, x:x2]
        canvas[y:y2, x:x2] = (roi.astype(np.float32) * (1.0 - a)).astype(np.uint8)

    _txt(canvas, txt, (x + pad, y + pad + tht), font, scale, cc, thick, 0, False, shadow)

    if graph and len(HISTORY) > 1:
        gx, gy = x + pad, y + pad + tht + bl + gap
        vmax = max(max(HISTORY), 1)
        pts = []
        # lo storico si legge da destra: il frame corrente e' l'ultimo punto
        for i, v in enumerate(HISTORY):
            px = gx + int(i * (gw - 1) / max(len(HISTORY) - 1, 1))
            py = gy + gh - int(v * gh / vmax)
            pts.append((px, py))
        cv2.polylines(canvas, [np.array(pts, np.int32)], False, gc, 1, cv2.LINE_AA)
        cv2.line(canvas, (gx, gy + gh), (gx + gw, gy + gh),
                 tuple(int(c * 0.4) for c in gc), 1, cv2.LINE_AA)
        cv2.circle(canvas, pts[-1], 2, gc, -1, cv2.LINE_AA)
        cv2.putText(canvas, str(vmax), (gx + gw + 4, gy + 8),
                    font, scale * 0.6, gc, 1, cv2.LINE_AA)

    return canvas


def _draw(img, txt, org, font, scale, color, thick, adv, mono):
    """mono=True scrive a passo fisso: i font Hershey sono
    proporzionali e senza questo le cifre non si incolonnano."""
    if not mono:
        cv2.putText(img, txt, org, font, scale, color, thick, cv2.LINE_AA)
        return
    x, y = org
    for i, ch in enumerate(txt):
        if ch != ' ':
            cv2.putText(img, ch, (x + i * adv, y), font, scale, color, thick, cv2.LINE_AA)


def _txt(img, txt, org, font, scale, color, thick, adv, mono, shadow):
    """Senza pannello di fondo il contorno scuro e' l'unica cosa
    che tiene leggibili i numeri sulle zone chiare del video."""
    if shadow:
        _draw(img, txt, org, font, scale, (0, 0, 0), thick + 2, adv, mono)
    _draw(img, txt, org, font, scale, color, thick, adv, mono)


def _grid(canvas, P, live, w, h):
    """Tabella numerica: ID, posizione, area."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = P.Gridscale.eval()
    thick = int(P.Gridthick.eval())
    lead = int(P.Gridleading.eval())
    mono = P.Gridmono.eval()
    col = tuple(int(getattr(P, k).eval() * 255)
                for k in ('Gridcolorr', 'Gridcolorg', 'Gridcolorb'))

    key = P.Gridsort.eval()
    def sortkey(it):
        tid, t = it
        if key == 'area':
            return -t['area']
        if key == 'x':
            return t['p'][0]
        if key == 'y':
            return t['p'][1]
        if key == 'age':
            return -t['age']
        return tid
    items = sorted(live, key=sortkey)[:int(P.Gridmax.eval())]

    tmpl = P.Gridrow.eval()
    lines = []
    for tid, t in items:
        lines.append(_fmt(tmpl, {
            'id': tid, 'x': t['p'][0] / w, 'y': 1.0 - t['p'][1] / h,
            'px': int(t['p'][0]), 'py': int(t['p'][1]),
            'area': t['area'], 'areapx': t['area'] * w * h,
            'w': t['wh'][0], 'h': t['wh'][1], 'age': t['age']}))

    header = P.Gridheader.eval()
    footer = _fmt(P.Gridfooter.eval(), {'count': len(live), 'shown': len(lines),
                                        'total': NEXT_ID[0] - 1, 'peak': STATS['peak']})

    ncols = int(P.Gridcols.eval())
    percol = max(1, -(-len(lines) // ncols)) if lines else 1

    adv = cv2.getTextSize('0', font, scale, thick)[0][0] + 1
    def tw(txt):
        return len(txt) * adv if mono else cv2.getTextSize(txt, font, scale, thick)[0][0]

    colw = max([tw(t) for t in lines] + [tw(header)]) + 18
    (_, tht), bl = cv2.getTextSize('0', font, scale, thick)

    panel = P.Gridpanel.eval()
    shadow = P.Gridshadow.eval()
    pad = 12 if panel else 3
    nrows = percol + (1 if header else 0) + (1 if footer else 0)
    boxw = colw * ncols - 18 + pad * 2
    boxh = nrows * lead + pad * 2

    mg = int(P.Gridmargin.eval())
    pos = P.Gridpos.eval()
    x = mg if pos in ('topleft', 'bottomleft') else max(0, w - boxw - mg)
    y = mg if pos in ('topleft', 'topright') else max(0, h - boxh - mg)
    x2, y2 = min(w, x + boxw), min(h, y + boxh)
    if x2 <= x or y2 <= y:
        return canvas

    if panel:
        a = P.Gridpanelalpha.eval()
        roi = canvas[y:y2, x:x2]
        canvas[y:y2, x:x2] = (roi.astype(np.float32) * (1.0 - a)).astype(np.uint8)

    ty = y + pad + tht
    if header:
        for c in range(ncols):
            _txt(canvas, header, (x + pad + c * colw, ty),
                 font, scale, col, thick, adv, mono, shadow)
        ty += lead

    for i, txt in enumerate(lines):
        c, r = i // percol, i % percol
        _txt(canvas, txt, (x + pad + c * colw, ty + r * lead),
             font, scale, col, thick, adv, mono, shadow)

    if footer:
        fy = y + pad + tht + (percol + (1 if header else 0)) * lead
        _txt(canvas, footer, (x + pad, fy), font, scale, col, thick, adv, mono, shadow)

    return canvas


# =============================================================
# COOK
# =============================================================
def onCook(scriptOp):

    if not len(scriptOp.inputs):
        return
    src = scriptOp.inputs[0].numpyArray(delayed=False)
    if src is None:
        return

    P = scriptOp.par
    if getattr(P, 'Active', None) is None:
        return
    if not P.Active.eval():
        scriptOp.copyNumpyArray(src)
        return

    # TD ha origine in basso a sinistra, OpenCV in alto a sinistra
    img = np.ascontiguousarray(np.flipud(src))
    h, w = img.shape[0], img.shape[1]

    s = {
        'blurw': P.Blurw.eval(), 'method': P.Method.eval(),
        'threshold': P.Threshold.eval(), 'blocksize': P.Blocksize.eval(),
        'adaptc': P.Adaptc.eval(), 'invert': P.Invert.eval(),
        'morph': P.Morph.eval(), 'minarea': P.Minarea.eval(),
        'maxarea': P.Maxarea.eval(), 'maxblobs': P.Maxblobs.eval(),
        'matchdist': P.Matchdist.eval(), 'maxmissing': P.Maxmissing.eval(),
        'minage': P.Minage.eval(), 'smooth': P.Smooth.eval(),
        'linkdist': P.Linkdist.eval(), 'maxlinks': P.Maxlinks.eval(),
    }

    rgb8 = np.clip(img[:, :, :3] * 255.0, 0, 255).astype(np.uint8)
    gray = cv2.cvtColor(rgb8, cv2.COLOR_RGB2GRAY)

    _track(_detect(gray, s, w, h), s, w)

    if P.Overlay.eval():
        canvas = rgb8.copy()
        d = P.Dim.eval()
        if d > 0:
            canvas = (canvas.astype(np.float32) * (1.0 - d)).astype(np.uint8)
    else:
        canvas = np.zeros((h, w, 3), np.uint8)

    pc = tuple(int(getattr(P, n).eval() * 255) for n in ('Pointcolorr', 'Pointcolorg', 'Pointcolorb'))
    lc = tuple(int(getattr(P, n).eval() * 255) for n in ('Linecolorr', 'Linecolorg', 'Linecolorb'))
    tc = tuple(int(getattr(P, n).eval() * 255) for n in ('Textcolorr', 'Textcolorg', 'Textcolorb'))
    bc = tuple(int(getattr(P, n).eval() * 255) for n in ('Boxcolorr', 'Boxcolorg', 'Boxcolorb'))

    live = [(i, t) for i, t in TRACKS.items()
            if t['miss'] == 0 and t['age'] >= s['minage']]

    # ---------- linee ----------
    pairs, maxd = {}, 1.0
    if P.Showlines.eval() and s['maxlinks'] > 0:
        pairs, maxd = _links(live, s, w)
        pos = {i: t['p'] for i, t in live}
        fade = P.Fadebylength.eval()
        base = P.Linealpha.eval()
        lt = int(P.Linethick.eval())
        # layer separato sommato alla fine: ogni linea porta la sua
        # opacita' nel colore, senza ricomporre l'immagine a ogni tratto
        layer = np.zeros_like(canvas)
        for (a, b), dd in pairs.items():
            al = base * (1.0 - dd / maxd) if (fade and maxd > 0) else base
            if al <= 0.003:
                continue
            col = tuple(int(c * al) for c in lc)
            cv2.line(layer, (int(pos[a][0]), int(pos[a][1])),
                     (int(pos[b][0]), int(pos[b][1])), col, lt, cv2.LINE_AA)
        canvas = cv2.add(canvas, layer)

    # ---------- rettangoli e punti ----------
    # tre interruttori indipendenti: rettangolo, punto, testo.
    # spegnerne uno non tocca gli altri.
    showrect = P.Showrect.eval()
    showpoint = P.Showpoint.eval()

    if showrect or showpoint:
        r0 = P.Pointradius.eval()
        th = int(P.Pointthick.eval())
        byarea = P.Scalebyarea.eval()
        bt = int(P.Boxthick.eval())
        pad = P.Boxpad.eval()
        clen = P.Cornerlen.eval()
        corners = P.Cornersonly.eval()

        for tid, t in live:

            if showrect:
                bx, by, bw, bh = t['bb']
                x0, y0 = int(bx - pad), int(by - pad)
                x1, y1 = int(bx + bw + pad), int(by + bh + pad)

                if corners:
                    # solo gli spigoli: si legge meglio quando i blob sono fitti
                    L = max(3, int(min(x1 - x0, y1 - y0) * clen))
                    for (cx0, cy0, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                                               (x0, y1, 1, -1), (x1, y1, -1, -1)):
                        cv2.line(canvas, (cx0, cy0), (cx0 + dx * L, cy0), bc, bt, cv2.LINE_AA)
                        cv2.line(canvas, (cx0, cy0), (cx0, cy0 + dy * L), bc, bt, cv2.LINE_AA)
                else:
                    cv2.rectangle(canvas, (x0, y0), (x1, y1), bc, bt, cv2.LINE_AA)

            if showpoint:
                r = max(2.0, (t['area'] * w * h / 3.14159) ** 0.5) if byarea else r0
                cv2.circle(canvas, (int(t['p'][0]), int(t['p'][1])),
                           int(r), pc, th, cv2.LINE_AA)

    # ---------- testi ----------
    if P.Showlabels.eval():
        tmpl = P.Labeltemplate.eval()
        fs = P.Fontscale.eval()
        ft = int(P.Fontthick.eval())
        ox, oy = P.Labeloffsetx.eval(), P.Labeloffsety.eval()
        leader = P.Labelleader.eval()
        nblob = len(live)
        for n, (tid, t) in enumerate(live):
            x, y = t['p']
            data = {'id': tid, 'n': n, 'total': nblob,
                    'x': x / w, 'y': 1.0 - y / h,
                    'px': int(x), 'py': int(y),
                    'area': t['area'], 'areapx': t['area'] * w * h,
                    'w': t['wh'][0], 'h': t['wh'][1],
                    'age': t['age'], 'frame': int(absTime.frame)}
            tx, ty = int(x + ox), int(y + oy)
            if leader:
                cv2.line(canvas, (int(x), int(y)), (tx - 3, ty + 3), tc, 1, cv2.LINE_AA)
            cv2.putText(canvas, _fmt(tmpl, data), (tx, ty),
                        cv2.FONT_HERSHEY_SIMPLEX, fs, tc, ft, cv2.LINE_AA)

    # ---------- contatore ----------
    nlive = len(live)
    HISTORY.append(nlive)
    glen = int(P.Graphlen.eval())
    while len(HISTORY) > glen:
        HISTORY.pop(0)
    if nlive > STATS['peak']:
        STATS['peak'] = nlive

    if P.Showcounter.eval():
        canvas = _counter(canvas, P, nlive, len(pairs), live, w, h)

    if P.Showgrid.eval():
        canvas = _grid(canvas, P, live, w, h)

    # ---------- tabelle ----------
    dat = P.Outputdat.eval()
    if dat is not None:
        dat.clear()
        dat.appendRow(['id', 'u', 'v', 'area', 'w', 'h', 'age'])
        for tid, t in live:
            dat.appendRow([tid, round(t['p'][0] / w, 5), round(1.0 - t['p'][1] / h, 5),
                           round(t['area'], 6), t['wh'][0], t['wh'][1], t['age']])

    ldat = P.Linksdat.eval()
    if ldat is not None:
        ldat.clear()
        ldat.appendRow(['ida', 'idb', 'dist'])
        for (a, b), dd in pairs.items():
            ldat.appendRow([a, b, round(dd / w, 5)])

    # ---------- output ----------
    out = np.zeros((h, w, 4), np.float32)
    out[:, :, :3] = canvas.astype(np.float32) / 255.0
    out[:, :, 3] = img[:, :, 3] if img.shape[2] > 3 else 1.0
    scriptOp.copyNumpyArray(np.ascontiguousarray(np.flipud(out)))
    return
'''


# ===========================================================================
# vst_send
# ===========================================================================
VST_SEND = r'''
def _comp():
    return me.parent()


def _candidates(kind, ch, a, b):
    # Confermato: l'Audio VST CHOP espone sendNoteOn / sendNoteOff con
    # firma (canale, pitch, velocity). Gli altri restano come riserva.
    if kind == 'on':
        return [('sendNoteOn',  (ch, a, b)),
                ('noteOn',      (ch, a, b)),
                ('sendNote',    (ch, a, b))]
    if kind == 'off':
        return [('sendNoteOff', (ch, a, 0)),
                ('noteOff',     (ch, a)),
                ('sendNote',    (ch, a, 0))]
    return [('sendControlChange', (ch, a, b)),
            ('sendControl',       (ch, a, b)),
            ('sendCC',            (ch, a, b))]


def _dispatch(kind, ch, a, b):
    c = _comp()
    # Una volta accertato che non passa si smette di provare: i tentativi
    # con eccezione ripetuti a ogni frame costano piu' di quanto sembri.
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
            debug('blob_audio: invio', kind, 'via', n)
            return True
        except Exception:
            continue

    c.store('vst_dead', True)
    debug('blob_audio: nessun metodo di invio funziona su', vst.path)
    debug('metodi:', [m for m in dir(vst) if not m.startswith('_')])
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
    for fname in ('sendAllNotesOff', 'allNotesOff'):
        fn = getattr(vst, fname, None)
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
# blob_voices
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
'''


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
    # Solo quando il valore a 7 bit cambia davvero.
    key = 'cc_last_' + channel.name
    if comp.fetch(key, -1) == q:
        return
    comp.store(key, q)
    mod('vst_send').control(int(comp.par.Midichannel.eval()), num, q)
'''


AUDIO_PAREXEC = r'''
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
        print('blob_audio: nota di prova inviata (Do centrale)')
    elif par.name == 'Diagnose':
        diagnose(comp)
    elif par.name == 'Openvst':
        vst = comp.op('surge')
        for m in ('openPluginUI', 'openViewer', 'showPluginUI'):
            fn = getattr(vst, m, None)
            if fn is not None:
                try:
                    fn()
                    print('blob_audio: UI aperta con', m)
                    return
                except Exception as e:
                    print('blob_audio:', m, 'fallito:', e)
        print('metodi:', [m for m in dir(vst) if not m.startswith('_')])
    return


def diagnose(comp):
    print('=' * 66)
    print('blob_audio - diagnostica')
    print('-' * 66)
    src = comp.op('blobs_in')
    if src is None:
        print('ingresso: ASSENTE')
    elif src.numRows < 1:
        print('ingresso: VUOTO -> guarda il blob_tracker')
    else:
        print('ingresso: %d righe' % src.numRows)
        print('          colonne:', [str(c.val) for c in src.row(0)])
        if src.numRows > 1:
            print('          prima riga:', [str(c.val) for c in src.row(1)])

    v = comp.op('blob_voices')
    if v is not None:
        nv = int(comp.par.Voices.eval())
        try:
            print('voci    : gate', [int(v['gate%d' % (i + 1)][0]) for i in range(nv)])
            print('          note', [int(v['note%d' % (i + 1)][0]) for i in range(nv)])
            print('          id  ', [int(v['id%d' % (i + 1)][0]) for i in range(nv)])
            print('          count %d, grezzi %d'
                  % (int(v['count'][0]), int(v['blobs_raw'][0])))
        except Exception as e:
            print('voci    : errore lettura (%s)' % e)

    vst = comp.op('surge')
    if vst is None:
        print('vst     : ASSENTE')
    else:
        print('vst     :', vst.type, '|', vst.par.file.eval())
        print('          invio disattivato:', comp.fetch('vst_dead', False))
        print('          metodi in cache:', comp.fetch('vst_m_on', None),
              comp.fetch('vst_m_off', None), comp.fetch('vst_m_cc', None))
    out = comp.op('audioout')
    if out is not None:
        print('uscita  : active =', out.par.active.eval())
    print('=' * 66)
'''


TRACKER_PAREXEC = r'''
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
'''


# ===========================================================================
# helper
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
        REPORT.append('MANCA      %-22s (%s)' % (name, ', '.join(cn)))
        return None
    o = comp.create(c, name)
    REPORT.append('ok         %-22s %s' % (name, o.type))
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
    REPORT.append('   par non impostato su %s: %s' % (o.name, '/'.join(parnames)))
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
    return False


def _link(a, b, i=0):
    if a is None or b is None:
        return
    try:
        b.inputConnectors[i].connect(a)
    except Exception as e:
        REPORT.append('   collegamento fallito %s -> %s (%s)' % (a.name, b.name, e))


# ===========================================================================
# blocco 1: tracker
# ===========================================================================
def build_tracker(parent_comp):
    tmp = TRACKER_NAME + '_building'
    if parent_comp.op(tmp):
        parent_comp.op(tmp).destroy()
    comp = parent_comp.create(_cls('baseCOMP'), tmp)

    p = comp.appendCustomPage('Blob Tracker')
    p.appendPulse('Diagnose', label='Diagnostica')
    p.appendFile('Source', label='Video')[0].default = VIDEO_PATH
    p.appendToggle('Downscale', label='Rileva a risoluzione ridotta')
    dh = p.appendInt('Detectheight', label='Altezza di rilevamento')[0]
    dh.default, dh.normMin, dh.normMax = 540, 180, 1080

    mov = _make(comp, 'source', 'moviefileinTOP')
    _expr(mov, 'parent().par.Source', 'file')
    _set(mov, True, 'play')

    det = _make(comp, 'detect_res', 'resolutionTOP')
    _link(mov, det)
    _set(det, 'fixed', 'outputresolution', 'resolutionmenu')
    _expr(det, 'int(parent().par.Detectheight * 16 / 9)', 'resolutionw', 'w')
    _expr(det, 'parent().par.Detectheight', 'resolutionh', 'h')
    _expr(det, 'not parent().par.Downscale', 'bypass')

    # --- callbacks e Script TOP ---
    cb = _make(comp, 'blobtrack_callbacks', 'textDAT')
    if cb is not None:
        cb.text = TRACKER_CODE

    script = _make(comp, 'script1', 'scriptTOP')
    _link(det, script)
    _set(script, 'blobtrack_callbacks', 'callbacks', 'callbacksdat')
    _set(script, 'useinput', 'outputresolution', 'resolutionmenu')

    # Le pagine custom nascono in onSetupParameters, che TD chiama quando
    # vuole lui. Qui la forziamo subito, altrimenti Outputdat non esiste
    # ancora e l'assegnazione qui sotto fallirebbe.
    if cb is not None and script is not None:
        try:
            cb.module.onSetupParameters(script)
            REPORT.append('ok         %-22s parametri creati' % 'script1')
        except Exception as e:
            REPORT.append('   onSetupParameters fallito (%s)' % e)

    tbl = _make(comp, 'blob_table', 'tableDAT')
    lnk = _make(comp, 'links_table', 'tableDAT')
    _set(script, 'blob_table', 'Outputdat')
    _set(script, 'links_table', 'Linksdat')

    vout = _make(comp, 'video_out', 'outTOP')
    _link(script, vout)
    bout = _make(comp, 'blobs_out', 'outDAT')
    _link(tbl, bout)
    lout = _make(comp, 'links_out', 'outDAT')
    _link(lnk, lout)

    coords = {'source': (0, 450), 'detect_res': (200, 450),
              'script1': (400, 450), 'video_out': (620, 450),
              'blobtrack_callbacks': (400, 600),
              'blob_table': (400, 250), 'blobs_out': (620, 250),
              'links_table': (400, 120), 'links_out': (620, 120)}
    for n, (x, y) in coords.items():
        o = comp.op(n)
        if o is not None:
            o.nodeX, o.nodeY = x, y

    old = parent_comp.op(TRACKER_NAME)
    if old is not None:
        old.destroy()
    comp.name = TRACKER_NAME
    comp.nodeX, comp.nodeY = 0, 300
    return comp


# ===========================================================================
# blocco 2: audio
# ===========================================================================
def build_audio(parent_comp):
    tmp = AUDIO_NAME + '_building'
    if parent_comp.op(tmp):
        parent_comp.op(tmp).destroy()
    comp = parent_comp.create(_cls('baseCOMP'), tmp)

    p = comp.appendCustomPage('Blob Audio')
    p.appendToggle('Audioon', label='Audio attivo')[0].default = True
    p.appendToggle('Sendcc', label='Invia CC')[0].default = True
    p.appendPulse('Testnote', label='Nota di prova')
    p.appendPulse('Panic', label='Panic / riabilita invio')
    p.appendPulse('Diagnose', label='Diagnostica')
    p.appendPulse('Openvst', label='Apri UI VST')
    p.appendFile('Plugin', label='Plugin VST3')[0].default = SURGE_PATH

    r = p.appendInt('Rate', label='Elabora 1 frame ogni')[0]
    r.default, r.normMin, r.normMax = 1, 1, 10
    m = p.appendFloat('Minarea', label='Area minima blob')[0]
    m.default, m.normMin, m.normMax = 0.0, 0.0, 0.02
    vo = p.appendInt('Voices', label='Voci')[0]
    vo.default, vo.normMin, vo.normMax = VOICES, 1, 24
    ma = p.appendInt('Minage', label='Eta minima per suonare')[0]
    ma.default, ma.normMin, ma.normMax = 4, 1, 60

    s = p.appendMenu('Scale', label='Scala')[0]
    s.menuNames  = ['chromatic', 'major', 'minor', 'dorian', 'penta', 'whole']
    s.menuLabels = ['Cromatica', 'Maggiore', 'Minore', 'Dorico',
                    'Pentatonica', 'Toni interi']
    s.default = 'minor'
    rn = p.appendInt('Rootnote', label='Nota fondamentale')[0]
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

    mc = p.appendInt('Midichannel', label='Canale MIDI')[0]
    mc.default, mc.normMin, mc.normMax = 1, 1, 16
    for name, label, default in [('Cccount', 'CC numero blob', 1),
                                 ('Ccdensity', 'CC densita', 11),
                                 ('Ccheight', 'CC altezza', 74)]:
        c = p.appendInt(name, label=label)[0]
        c.default, c.normMin, c.normMax = default, -1, 127

    vol = p.appendFloat('Volume', label='Volume uscita')[0]
    vol.default, vol.normMin, vol.normMax = 0.7, 0.0, 1.0

    _make(comp, 'blobs_in', 'inDAT')

    send = _make(comp, 'vst_send', 'textDAT')
    if send is not None:
        send.text = VST_SEND

    vsd = _make(comp, 'blob_voices_callbacks', 'textDAT')
    if vsd is not None:
        vsd.text = VOICES_SCRIPT
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

    vst = _make(comp, 'surge', 'audiovstCHOP')
    _expr(vst, 'parent().par.Plugin', 'file')
    _set(vst, True, 'timeslice')

    dev = _make(comp, 'audioout', 'audiodevoutCHOP')
    _link(vst, dev)
    _expr(dev, 'parent().par.Volume', 'volume')
    _set(dev, True, 'active')

    coords = {'blobs_in': (0, 400), 'blob_voices_callbacks': (0, 250),
              'blob_voices': (250, 400), 'voices_out': (500, 400),
              'vst_send': (0, 100), 'note_exec': (250, 100),
              'cc_exec': (500, 100), 'surge': (250, -60),
              'audioout': (500, -60)}
    for n, (x, y) in coords.items():
        o = comp.op(n)
        if o is not None:
            o.nodeX, o.nodeY = x, y

    old = parent_comp.op(AUDIO_NAME)
    if old is not None:
        old.destroy()
    comp.name = AUDIO_NAME
    comp.nodeX, comp.nodeY = 450, 300
    return comp, vst


def _pulse_handler(parent_comp, comp, text):
    # Il Parameter Execute DAT va FUORI dal COMP che osserva: se sta dentro,
    # TD segnala "Cook dependency loop detected".
    name = comp.name + '_pulse'
    if parent_comp.op(name):
        parent_comp.op(name).destroy()
    cls = _cls('parameterexecuteDAT')
    if cls is None:
        return
    p = parent_comp.create(cls, name)
    p.text = text
    _set(p, comp.name, 'op')
    _set(p, True, 'pulse')
    _set(p, False, 'value')
    p.nodeX, p.nodeY = comp.nodeX, comp.nodeY - 160
    REPORT.append('ok         %-22s fuori dal COMP' % name)


def build():
    REPORT.clear()
    parent_comp = op(PARENT_PATH)
    if parent_comp is None:
        raise RuntimeError('non trovo %s' % PARENT_PATH)

    tracker = build_tracker(parent_comp)
    audio, vst = build_audio(parent_comp)
    _link(tracker, audio)

    _pulse_handler(parent_comp, tracker, TRACKER_PAREXEC)
    _pulse_handler(parent_comp, audio, AUDIO_PAREXEC)

    print('=' * 66)
    print('build completa')
    print('-' * 66)
    for r in REPORT:
        print(' ', r)
    print('-' * 66)
    print(' %s -> %s' % (tracker.path, audio.path))
    print('')
    print(' 1. controlla il parametro Video sul blob_tracker')
    print(' 2. Diagnose sul blob_tracker: la tabella deve avere righe')
    print(' 3. Nota di prova sul blob_audio: se la senti, Surge e\' vivo')
    print(' 4. Diagnose sul blob_audio: i gate devono accendersi')
    print('=' * 66)


build()