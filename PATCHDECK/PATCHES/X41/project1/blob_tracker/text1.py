# =============================================================
# blobtrack_bio.py
# Callbacks DAT per uno Script TOP di TouchDesigner.
#
# Traccia formazioni biologiche (balani, incrostazioni, alghe)
# su un video e disegna punti, linee di collegamento e testi.
#
# USO
#   1. Script TOP -> par "Callbacks DAT" = questo Text DAT
#   2. Video (Movie File In TOP) nell'ingresso 0
#   3. Common -> Output Resolution = Input
#
# I default sono tarati su un frame 1920x1080 di questo materiale
# (37 blob agganciati). Sfocatura, Blocco adattivo e Pulizia
# morfologica sono in pixel: se lavori a 1280x720 scalali di ~0.67
# (blocco 101, sfocatura 11, morph 5). Area minima e massima sono
# normalizzate sull'area del frame, quelle non si toccano.
#
# Se i parametri restano a zero: pulsante "Ripristina default"
# nella pagina Detection.
#
# ROTAZIONE (pagina Output)
#   La rotazione avviene PRIMA del rilevamento, non dopo. Cosi'
#   contorni, riquadri, testi, griglia e tabella dati lavorano tutti
#   nel nuovo orientamento senza nessuna conversione: quello che vedi
#   e' quello che esce nella tabella.
#   Con 90 gradi un 1920x1080 diventa 1080x1920, cioe' 9:16.
#   Il Common -> Output Resolution puo' restare su Input: la
#   risoluzione la detta l'array che lo script restituisce. Se il TOP
#   ti esce schiacciato, mettilo su Custom con i valori scambiati.
#
#   Attenzione a valle: dopo la rotazione la colonna u della tabella
#   corre lungo il lato corto. Se blob_audio mappa u sull'altezza
#   della nota, la melodia cambia di conseguenza: e' corretto, ma
#   suona diverso da prima.
# =============================================================

import time as _time

import numpy as np
import cv2

TRACKS = {}
NEXT_ID = [1]
STATS = {'new': 0, 'lost': 0, 'peak': 0}
HISTORY = []

# -------------------------------------------------------------
# definizione parametri:  (tipo, nome, etichetta, default, extra)
# -------------------------------------------------------------
SPECS = [
 ('Output', [
  ('Menu',   'Rotate', 'Rotazione', 'none',
      {'menuNames':  ['none', 'cw', 'ccw', 'half'],
       'menuLabels': ['Nessuna', '90 orario', '90 antiorario', '180']}),
  ('Toggle', 'Flipx',  'Specchia orizzontale', 0, {}),
  ('Toggle', 'Flipy',  'Specchia verticale',   0, {}),
 ]),
 ('Prestazioni', [
  ('Float',  'Detectscale', 'Scala rilevamento', 0.5, {'normMin': 0.2, 'normMax': 1.0}),
  ('Toggle', 'Profile',     'Profilo nel Textport', 0, {}),
  ('Int',    'Profileevery', 'Ogni quanti frame',  60, {'min': 5, 'max': 600, 'clampMin': True}),
 ]),
 ('Detection', [
  ('Toggle', 'Active',    'Attivo',              1,      {}),
  ('Int',    'Blurw',     'Sfocatura',           15,      {'min': 1, 'max': 51, 'clampMin': True}),
  ('Menu',   'Method',    'Soglia',       'adaptive',    {'menuNames':  ['fixed', 'otsu', 'adaptive'],
                                                          'menuLabels': ['Fissa', 'Otsu (auto)', 'Adattiva']}),
  ('Float',  'Threshold', 'Livello soglia',      0.5,    {'normMin': 0.0, 'normMax': 1.0}),
  ('Int',    'Blocksize', 'Blocco adattivo',     151,     {'min': 3, 'max': 201, 'clampMin': True}),
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

# parametri di versioni precedenti, rimossi all'aggiornamento
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


def _now():
    return _time.perf_counter()


_PROF = {'n': 0, 'det': 0.0, 'trk': 0.0, 'draw': 0.0, 'blobs': 0}


def _profile(P, det, trk, draw, nblobs, w, h, ds):
    """Medie sugli ultimi N frame: i singoli frame ballano troppo
    per dire qualcosa."""
    _PROF['n'] += 1
    _PROF['det'] += det
    _PROF['trk'] += trk
    _PROF['draw'] += draw
    _PROF['blobs'] += nblobs

    every = int(P.Profileevery.eval()) if getattr(P, 'Profileevery', None) else 60
    if _PROF['n'] < every:
        return

    n = float(_PROF['n'])
    print('blobtrack %dx%d  scala %.2f (%dx%d)  media su %d frame'
          % (w, h, ds, int(w * ds), int(h * ds), int(n)))
    print('   rilevamento %6.2f ms   tracking %5.2f ms   disegno %6.2f ms'
          % (_PROF['det'] / n, _PROF['trk'] / n, _PROF['draw'] / n))
    print('   totale script %6.2f ms   blob medi %.1f'
          % ((_PROF['det'] + _PROF['trk'] + _PROF['draw']) / n,
             _PROF['blobs'] / n))
    for k in _PROF:
        _PROF[k] = 0


def _fmt(template, data):
    try:
        return template.format(**data)
    except Exception:
        return template


_ROT = {
    'cw':   cv2.ROTATE_90_CLOCKWISE,
    'ccw':  cv2.ROTATE_90_COUNTERCLOCKWISE,
    'half': cv2.ROTATE_180,
}


def _orient(img, P):
    """Rotazione e specchiature, applicate PRIMA di tutto il resto.

    Farlo qui invece che in uscita significa che rilevamento, disegno e
    tabella lavorano gia' nel nuovo orientamento: nessuna conversione di
    coordinate sparsa nel codice, e quindi nessun posto dove sbagliarla.

    Con 90 gradi le dimensioni si scambiano: un 1920x1080 esce 1080x1920.
    """
    mode = str(P.Rotate.eval()) if getattr(P, 'Rotate', None) else 'none'
    code = _ROT.get(mode)
    if code is not None:
        img = cv2.rotate(img, code)

    if getattr(P, 'Flipx', None) and P.Flipx.eval():
        img = img[:, ::-1]
    if getattr(P, 'Flipy', None) and P.Flipy.eval():
        img = img[::-1, :]

    return np.ascontiguousarray(img)


def _detect(gray, s, w, h, k=1.0):
    """k e' il fattore di scala a cui gira il rilevamento.

    Sfocatura, Blocco adattivo e Pulizia morfologica sono in pixel: se
    l'immagine e' rimpicciolita vanno rimpiccioliti anche loro, altrimenti
    cambiando Scala rilevamento cambierebbe anche COSA viene rilevato.
    Cosi' invece la taratura resta valida a qualunque scala.
    """
    kb = _odd(max(1, int(round(s['blurw'] * k))))
    if kb > 1:
        gray = cv2.GaussianBlur(gray, (kb, kb), 0)

    m = s['method']
    if m == 'fixed':
        _, mask = cv2.threshold(gray, s['threshold'] * 255.0, 255, cv2.THRESH_BINARY)
    elif m == 'otsu':
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        mask = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
            _odd(max(3, int(round(s['blocksize'] * k))), 3), float(s['adaptc']))

    if s['invert']:
        mask = 255 - mask

    mk = int(round(s['morph'] * k))
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
        # anche da spento la rotazione si applica, altrimenti l'interruttore
        # Attivo cambierebbe anche l'inquadratura
        scriptOp.copyNumpyArray(
            np.ascontiguousarray(np.flipud(_orient(np.flipud(src), P))))
        return

    # TD ha origine in basso a sinistra, OpenCV in alto a sinistra
    img = np.ascontiguousarray(np.flipud(src))

    # Rotazione prima di tutto: da qui in poi w e h sono quelli nuovi e
    # nessun'altra parte del codice deve saperne niente.
    img = _orient(img, P)
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

    # Il rilevamento e' la voce di costo dominante e scala con i pixel.
    # Girarlo su una copia ridotta e riportare le coordinate alla scala
    # piena costa una frazione, e il disegno resta a risoluzione intera.
    ds = float(getattr(P, 'Detectscale', None).eval()) \
        if getattr(P, 'Detectscale', None) else 1.0
    ds = max(0.1, min(1.0, ds))

    t0 = _now()
    if ds < 0.999:
        sw, sh = max(16, int(w * ds)), max(16, int(h * ds))
        small = cv2.resize(gray, (sw, sh), interpolation=cv2.INTER_AREA)
        dets = _detect(small, s, sw, sh, ds)
        inv = 1.0 / ds
        dets = [(d[0] * inv, d[1] * inv, d[2],
                 d[3] * inv, d[4] * inv, d[5] * inv, d[6] * inv) for d in dets]
    else:
        dets = _detect(gray, s, w, h, 1.0)
    t1 = _now()

    _track(dets, s, w)
    t2 = _now()

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

    # ---------- tabelle opzionali ----------
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

    t3 = _now()

    # ---------- output ----------
    out = np.zeros((h, w, 4), np.float32)
    out[:, :, :3] = canvas.astype(np.float32) / 255.0
    out[:, :, 3] = img[:, :, 3] if img.shape[2] > 3 else 1.0
    scriptOp.copyNumpyArray(np.ascontiguousarray(np.flipud(out)))

    if getattr(P, 'Profile', None) and P.Profile.eval():
        _profile(P, (t1 - t0) * 1000.0, (t2 - t1) * 1000.0,
                 (t3 - t2) * 1000.0, len(dets), w, h, ds)
    return


# =============================================================
# ROTAZIONE E FORMATO VERTICALE
#   Pagina Output: Rotazione (nessuna / 90 orario / 90 antiorario /
#   180) piu' due specchiature.
#
#   La rotazione e' applicata all'ingresso, prima del rilevamento.
#   Conseguenze volute:
#     - riquadri, punti, testi e griglia si dispongono nel nuovo
#       formato senza nessuna correzione
#     - le colonne u e v della tabella blob sono relative al frame
#       ruotato, quindi coerenti con quello che vedi
#     - Area minima e massima restano normalizzate sull'area del
#       frame, che non cambia ruotando: non vanno ritoccate
#     - Sfocatura, Blocco adattivo e Pulizia morfologica sono in
#       pixel e neanche loro cambiano, perche' i pixel sono gli
#       stessi, solo disposti diversamente
#
#   Da 1920x1080 a 90 gradi escono 1080x1920, cioe' 9:16.
#
#   ATTENZIONE A VALLE: dopo la rotazione u corre lungo il lato
#   corto. Se u pilota l'altezza delle note, la melodia cambia.
#   Non e' un errore, ma conviene risalvare il preset audio.
#
# =============================================================
# GRIGLIA NUMERICA
#   Riga:  {id} {x} {y} {px} {py} {area} {areapx} {w} {h} {age}
#   Piede: {count} {shown} {total} {peak}
#
#   'Passo fisso' allinea le cifre in colonna: senza, i font
#   Hershey sono proporzionali e i numeri ballano.
#   L'intestazione e' testo libero, allineala tu al template riga.
#
# ESEMPI
#   riga   {id:03d}  {x:.3f} {y:.3f} {area:.4f}
#   riga   {id:03d} {px:>4d},{py:>4d}
#   piede  N={count}   VISTI {shown}/{total}
#
# =============================================================
# PLACEHOLDER DEL TEMPLATE CONTATORE
#   {count}   blob attivi in questo frame
#   {new}     agganciati in questo frame
#   {lost}    persi in questo frame
#   {peak}    massimo raggiunto dall'ultimo azzeramento
#   {total}   ID assegnati in totale
#   {links}   collegamenti disegnati
#   {area}    somma delle aree     {avgarea}  area media
#   {frame}   frame assoluto
#
# ESEMPI
#   BLOB {count}   NUOVI {new}   PICCO {peak}   TOT {total}
#   {count:03d} ORGANISMI   COPERTURA {area:.1%}
#   n={count}  link={links}  f={frame}
#
# =============================================================
# PLACEHOLDER DEL TEMPLATE TESTO
#   {id} {n} {total} {x} {y} {px} {py}
#   {area} {areapx} {w} {h} {age} {frame}
#
# Sintassi format() di Python:  'B{id:03d}  {area:.4f}' -> 'B007  0.0031'
#
# ESEMPI
#   ID{id}  A{area:.4f}
#   BALANUS {id:02d}   eta {age}f
#   {id:03d} / {total}
#   x{x:.3f} y{y:.3f}
#
# LIMITE: cv2.putText usa i font Hershey, solo ASCII.
# =============================================================