# build_blocks_v2.py — BUILD COMPLETA (sessione del 15/09)
#
# Include tutte le correzioni verificate sul campo:
#   - limiti dei parametri: min/max, non solo normMin/normMax (il clamp
#     bloccava tutto a 1)
#   - percorsi fra fratelli: nomi nudi, non "../"; '.' per il Parameter Execute
#   - nomi dei parametri: una maiuscola iniziale, niente cifra finale
#   - Noise CHOP con rate = 1: altrimenti i campioni cadono in un intervallo
#     minuscolo e tutte le istanze ricevono quasi lo stesso valore
#   - tipo di forma deterministico sull'indice, distribuito fra i tipi attivi
#   - UV dei SOP: "texture" e' un menu, non un interruttore
#   - bande con deriva continua invece di oscillazione
#   - nomi reali: renamefrom/renameto, divs, index1/index2, instancer/g/b
#
# Catena TOP:
#   render_bg -> bg_level -----------\
#                                     comp -> ed_switch -> sl2_switch
#   render_fg -> sl_switch ----------/          (edge)      (taglio finale)
#        -> px_switch (8-bit) -> ps_switch (sorting) -> out1
#
# Gli effetti nascono spenti. USO: Text DAT dentro /project1, Ctrl+R.

import random
import re

# ================================================================ CONFIG
TARGET_PATH = '/project1'
COMP_NAME   = 'BLOCKS'
ORTHO_W, ORTHO_H = 16.0, 9.0
WRAP_X, WRAP_Y = ORTHO_W * 0.75, ORTHO_H * 0.75
TEX_RES = 512

PALETTES = [
    ('Vivace',    ["#FF5733", "#33FF57", "#3357FF", "#F3FF33", "#FF33A1", "#A133FF", "#33FFF3"]),
    ('Caldo',     ["#F94144", "#F3722C", "#F8961E", "#F9C74F", "#FFD5A5", "#E36414", "#9A031E"]),
    ('Freddo',    ["#005F73", "#0A9396", "#94D2BD", "#4CC9F0", "#3A0CA3", "#4361EE", "#CAF0F8"]),
    ('Mono',      ["#111111", "#333333", "#555555", "#777777", "#999999", "#CCCCCC", "#FFFFFF"]),
    ('Neon',      ["#FF00A0", "#00FFD1", "#FFE600", "#7B00FF", "#00B3FF", "#FF3D00", "#C6FF00"]),
    ('Terra',     ["#6B4226", "#A47551", "#C9A227", "#7D8471", "#4A5240", "#D9C5A0", "#3E2C1C"]),
    ('Acido',     ["#D0FF00", "#00FF41", "#39FF14", "#CCFF00", "#B0FF1F", "#7FFF00", "#EFFF3D"]),
    ('Notte',     ["#0B132B", "#1C2541", "#3A506B", "#5BC0BE", "#6FFFE9", "#151F30", "#243B55"]),
    ('Pastello',  ["#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF", "#BDB2FF", "#FFC6FF"]),
    ('Ruggine',   ["#7F2B0A", "#A63A11", "#C1502E", "#D97B4A", "#E8A87C", "#5C1A05", "#2E0D02"]),
    ('Ghiaccio',  ["#E8F6FF", "#C2E7F5", "#94D2E8", "#6BB8D6", "#4A93B8", "#2E6A8C", "#F7FDFF"]),
    ('Tropicale', ["#FF6B35", "#F7C59F", "#EFEFD0", "#004E89", "#1A659E", "#00A896", "#F95738"]),
]
PAL_LEN = 7
SIGLE = ['a', 'b', 'c', 'd', 'e', 'f', 'g']     # niente cifre finali nei nomi

FONT_PREFERITI = ['Menlo', 'Monaco', 'Courier New', 'Courier', 'Andale Mono',
                  'Consolas', 'DejaVu Sans Mono', 'PT Mono', 'SF Mono',
                  'Helvetica', 'Helvetica Neue', 'Arial', 'Verdana',
                  'Futura', 'Impact', 'Georgia', 'Times New Roman', 'Didot']

UV_CANDIDATI = ['Rows and Columns', 'Rows & Columns', 'Rows', 'Sequential',
                'Faces', 'Polygon', 'On', 'Vertex']

# ================================================================ HELPERS
_warn = []

def optype(kind):
    try:
        return eval(kind)
    except NameError:
        return kind

def mk(parent, kind, name, x=0, y=0):
    o = parent.create(optype(kind), name)
    o.nodeX, o.nodeY = x, y
    return o

def _findpar(o, names, find=None):
    if isinstance(names, str):
        names = [names]
    for n in names:
        p = getattr(o.par, n, None)
        if p is not None:
            return p
    if find:
        rx = re.compile(find, re.I)
        hits = [p for p in o.pars('*') if rx.match(p.name)]
        if len(hits) == 1:
            return hits[0]
    stem = names[0][:6].lower()
    near = sorted(p.name for p in o.pars('*') if stem in p.name.lower())
    _warn.append('%s: nessun parametro tra %s%s'
                 % (o.path, names, ('. Simili: %s' % near[:8]) if near else ''))
    return None

def setp(o, names, val, find=None):
    p = _findpar(o, names, find)
    if p is None:
        return None
    try:
        p.val = val
    except Exception as e:
        _warn.append('%s.%s = %r -> %s' % (o.path, p.name, val, e))
    return p

def setx(o, names, expr, find=None):
    p = _findpar(o, names, find)
    if p is None:
        return None
    try:
        p.expr = expr
    except Exception as e:
        _warn.append('%s.%s expr -> %s' % (o.path, p.name, e))
    return p

def setmenu(o, names, labels, find=None):
    p = _findpar(o, names, find)
    if p is None:
        return None
    if isinstance(labels, str):
        labels = [labels]
    mn = [str(x).lower() for x in p.menuNames]
    ml = [str(x).lower() for x in p.menuLabels]
    for want in labels:
        w = want.lower()
        if w in mn:
            p.val = p.menuNames[mn.index(w)]
            return p
        if w in ml:
            p.menuIndex = ml.index(w)
            return p
    _warn.append('%s.%s: nessuna voce tra %s (disponibili: %s)'
                 % (o.path, p.name, labels, p.menuLabels))
    return p

def force_res(o, we, he):
    setmenu(o, 'outputresolution', ['Custom Resolution', 'Custom'])
    setx(o, 'resolutionw', we)
    setx(o, 'resolutionh', he)

def hex2rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)]

def set_uv(s):
    """texture e' un MENU su questi SOP: assegnargli True non lo accende"""
    p = getattr(s.par, 'texture', None)
    if p is None:
        return
    if p.isMenu:
        low = [str(x).lower() for x in p.menuLabels]
        for want in UV_CANDIDATI:
            if want.lower() in low:
                p.menuIndex = low.index(want.lower())
                return
        for i, lab in enumerate(p.menuLabels):
            if str(lab).lower() not in ('off', 'none'):
                p.menuIndex = i
                return
    else:
        p.val = True

def setflags(o):
    try:
        o.render = True
        o.display = True
    except Exception as e:
        _warn.append('%s: flag -> %s' % (o.path, e))

# ================================================================ COMP
target = op(TARGET_PATH)
if target is None:
    raise RuntimeError('Non trovo %s.' % TARGET_PATH)
old = target.op(COMP_NAME)
if old:
    old.destroy()
c = mk(target, 'baseCOMP', COMP_NAME, 0, 0)

def sub(kind, name, x=0, y=0):
    return mk(c, kind, name, x, y)

def noise(name, chans, end_expr, seed_expr, x, y,
          kind='Random', period_expr=None, tz_expr=None, amp=None):
    n = sub('noiseCHOP', name, x, y)
    setp(n, 'channelname', chans)
    setp(n, 'start', 0)
    setx(n, 'end', end_expr)
    setp(n, 'rate', 1)        # un campione = un secondo: le istanze divergono
    setmenu(n, 'type', [kind] if kind != 'Perlin' else
            ['Perlin 3D', 'Perlin', 'Simplex 3D', 'Sparse'])
    setx(n, 'seed', seed_expr)
    if period_expr:
        setx(n, 'period', period_expr)
    if tz_expr:
        setx(n, 'tz', tz_expr)
    if amp is not None:
        setp(n, 'amp', amp)
    setp(n, 'timeslice', False)
    return n

def rename_to(src, newname, x, y):
    r = sub('renameCHOP', src.name + '_as_' + newname, x, y)
    r.inputConnectors[0].connect(src)
    setp(r, 'renamefrom', '*')
    setp(r, 'renameto', newname)
    return r

# ================================================================ UI
def build_page(pagename, specs):
    pg = c.appendCustomPage(pagename)
    for spec in specs:
        kind, name, label, default = spec[0], spec[1], spec[2], spec[3]
        if kind == 'int':
            p = pg.appendInt(name, label=label)[0]
            p.min, p.max = spec[4], spec[5]
            p.normMin, p.normMax = spec[4], spec[5]
            p.clampMin, p.clampMax = True, True
        elif kind == 'float':
            p = pg.appendFloat(name, label=label)[0]
            p.min, p.max = spec[4], spec[5]
            p.normMin, p.normMax = spec[4], spec[5]
        elif kind == 'toggle':
            p = pg.appendToggle(name, label=label)[0]
        elif kind == 'str':
            p = pg.appendStr(name, label=label)[0]
        elif kind == 'menu':
            p = pg.appendMenu(name, label=label)[0]
            p.menuNames, p.menuLabels = spec[4], spec[5]
        elif kind == 'rgb':
            ps = pg.appendRGB(name, label=label)
            for q, v in zip(ps, default):
                q.default = v
                q.val = v
            continue
        elif kind == 'pulse':
            pg.appendPulse(name, label=label)
            continue
        p.default = default
        p.val = default
    return pg

build_page('Forme', [
    ('int',    'Count',       'Numero blocchi',      8, 1, 64),
    ('toggle', 'Shapecircle', 'Cerchi',              True),
    ('toggle', 'Shaperect',   'Rettangoli',          True),
    ('toggle', 'Shapehex',    'Esagoni',             True),
    ('float',  'Sizemin',     'Dimensione min',      0.2, 0.05, 1.0),
    ('float',  'Sizemax',     'Dimensione max',      0.6, 0.05, 1.5),
    ('float',  'Aspect',      'Rapporto larg/alt',   16/9, 0.25, 4.0),
])

build_page('Rotazione', [
    ('float',  'Rotrand',     'Rotazione casuale Z', 0.0, 0.0, 1.0),
    ('float',  'Spin',        'Rotazione continua Z', 0.0, -2.0, 2.0),
    ('toggle', 'Persp',       'Camera in prospettiva', False),
    ('float',  'Tiltrand',    'Inclinazione casuale 3D', 0.0, 0.0, 1.0),
    ('float',  'Spinx',       'Rotazione continua X', 0.0, -2.0, 2.0),
    ('float',  'Spiny',       'Rotazione continua Y', 0.0, -2.0, 2.0),
])

build_page('Movimento', [
    ('float',  'Speedfg',     'Velocita scorrimento', 1.0, 0.0, 5.0),
    ('float',  'Wander',      'Ampiezza deriva',      1.5, 0.0, 8.0),
    ('float',  'Noisespeed',  'Evoluzione deriva',    0.15, 0.0, 1.0),
    ('float',  'Noiseperiod', 'Scala del noise',      4.0, 0.5, 20.0),
])

build_page('Sfondo', [
    ('int',    'Bgcount',     'Numero fasce',        3, 1, 32),
    ('menu',   'Bgdir',       'Orientamento', 'horizontal',
     ['horizontal', 'vertical'], ['Orizzontale', 'Verticale']),
    ('float',  'Bgsize',      'Dimensione fascia',   1.05, 0.1, 3.0),
    ('float',  'Speedbg',     'Velocita scorrimento', 0.4, 0.0, 5.0),
    ('float',  'Bgwander',    'Deriva',              0.7, 0.0, 6.0),
    ('float',  'Bgopacity',   'Opacita',             1.0, 0.0, 1.0),
])

build_page('Aspetto', [
    ('menu',   'Palette',     'Palette', PALETTES[0][0].lower(),
     [p[0].lower() for p in PALETTES] + ['custom'],
     [p[0] for p in PALETTES] + ['Custom']),
    ('menu',   'Blend',       'Blend sfondo/forme', 'over',
     ['over', 'add', 'difference'], ['Over', 'Add', 'Difference']),
])

build_page('Palette custom', [
    ('rgb', 'Palcola', 'Colore 1', (1.00, 0.34, 0.20)),
    ('rgb', 'Palcolb', 'Colore 2', (0.20, 1.00, 0.34)),
    ('rgb', 'Palcolc', 'Colore 3', (0.20, 0.34, 1.00)),
    ('rgb', 'Palcold', 'Colore 4', (0.95, 1.00, 0.20)),
    ('rgb', 'Palcole', 'Colore 5', (1.00, 0.20, 0.63)),
    ('rgb', 'Palcolf', 'Colore 6', (0.63, 0.20, 1.00)),
    ('rgb', 'Palcolg', 'Colore 7', (0.20, 1.00, 0.95)),
    ('pulse', 'Palcopy', 'Copia palette selezionata', None),
])

build_page('Texture', [
    ('menu',   'Texmode',  'Struttura interna', 'none',
     ['none', 'ramp', 'grid', 'border', 'text'],
     ['Nessuna', 'Gradiente', 'Griglia', 'Bordo', 'Testo']),
    ('menu',   'Texramp',  'Orientamento gradiente', 'radial',
     ['vertical', 'horizontal', 'radial', 'circular'],
     ['Verticale', 'Orizzontale', 'Radiale', 'Circolare']),
    ('int',    'Texdiv',   'Divisioni griglia',   4, 1, 32),
    ('float',  'Texwidth', 'Spessore linea',      0.12, 0.01, 0.5),
])

build_page('Testo', [
    ('menu',   'Textmode',    'Contenuto', 'grid',
     ['grid', 'fixed'], ['Griglia di caratteri', 'Testo fisso']),
    ('str',    'Textchars',   'Caratteri', 'ABCDEFGH0123456789/\\|-_=+*#'),
    ('str',    'Textstring',  'Testo fisso', 'BLOCKS'),
    ('int',    'Textcols',    'Colonne', 10, 1, 40),
    ('int',    'Textrows',    'Righe',   8, 1, 40),
    ('float',  'Textsize',    'Corpo (riempimento)', 0.9, 0.1, 2.0),
    ('float',  'Textdensity', 'Densita caratteri', 0.7, 0.0, 1.0),
    ('rgb',    'Textcolor',   'Colore glifi', (0.0, 0.0, 0.0)),
    ('rgb',    'Textbg',      'Colore fondo', (1.0, 1.0, 1.0)),
])

build_page('Contorni', [
    ('toggle', 'Wireframe',    'Wireframe forme',    False),
    ('toggle', 'Wireframebg',  'Wireframe sfondo',   False),
    ('float',  'Wirewidth',    'Spessore wireframe', 1.0, 0.1, 10.0),
    ('toggle', 'Edgeenable',   'Edge sull immagine', False),
    ('float',  'Edgestrength', 'Intensita edge',     1.0, 0.0, 5.0),
])

build_page('Taglio', [
    ('toggle', 'Sliceenable', 'Taglio a bande', False),
    ('menu',   'Slicedir',    'Direzione bande', 'horizontal',
     ['horizontal', 'vertical', 'both'],
     ['Bande orizzontali', 'Bande verticali', 'Entrambe']),
    ('int',    'Slicebands',  'Numero bande',   24, 2, 400),
    ('float',  'Sliceamount', 'Spostamento',    0.15, 0.0, 1.0),
    ('float',  'Slicespeed',  'Velocita bande', 0.6, 0.0, 5.0),
    ('float',  'Slicechaos',  'Irregolarita',   0.5, 0.0, 1.0),
])

build_page('Taglio finale', [
    ('toggle', 'Slicetwoenable', 'Taglio finale', False),
    ('menu',   'Slicetwodir',    'Direzione bande', 'vertical',
     ['horizontal', 'vertical', 'both'],
     ['Bande orizzontali', 'Bande verticali', 'Entrambe']),
    ('int',    'Slicetwobands',  'Numero bande',   9, 2, 400),
    ('float',  'Slicetwoamount', 'Spostamento',    0.08, 0.0, 1.0),
    ('float',  'Slicetwospeed',  'Velocita bande', 0.3, 0.0, 5.0),
    ('float',  'Slicetwochaos',  'Irregolarita',   0.5, 0.0, 1.0),
])

build_page('Pixel', [
    ('toggle', 'Pixelenable', 'Effetto 8-bit',      False),
    ('int',    'Pixelsize',   'Dimensione pixel',   6, 1, 64),
    ('int',    'Levels',      'Livelli per canale', 4, 2, 32),
    ('float',  'Dither',      'Dithering',          0.5, 0.0, 1.0),
])

build_page('Sorting', [
    ('toggle', 'Sortenable',  'Pixel sorting',    False),
    ('int',    'Sortscale',   'Scala pixel',      6, 1, 64),
    ('float',  'Sortthresh',  'Soglia luminanza', 0.181, 0.0, 1.0),
    ('float',  'Sortrefresh', 'Rigenerazione',    0.05, 0.0, 1.0),
])

build_page('Output', [
    ('int', 'Resw', 'Risoluzione X', 1280, 256, 3840),
    ('int', 'Resh', 'Risoluzione Y', 720, 256, 2160),
])

build_page('Seed', [
    ('int',   'Seed',        'Seed composizione', random.randint(0, 99999), 0, 99999),
    ('pulse', 'Reseed',      'Rigenera composizione', None),
    ('int',   'Colorseed',   'Seed colori', random.randint(0, 99999), 0, 99999),
    ('pulse', 'Reseedcolor', 'Rigenera colori', None),
])

END_FG = 'parent().par.Count - 1'
END_BG = 'parent().par.Bgcount - 1'
RESW, RESH = 'parent().par.Resw', 'parent().par.Resh'

# ================================================================ PALETTE
pal_chops = []
for i, (pname, cols) in enumerate(PALETTES):
    t = sub('tableDAT', 'pal_%d_tbl' % i, -1500, 700 + i * 50)
    t.clear()
    t.appendRow(['r', 'g', 'b'])
    for h in cols:
        t.appendRow(['%.4f' % v for v in hex2rgb(h)])
    d = sub('dattoCHOP', 'pal_%d' % i, -1350, 700 + i * 50)
    setp(d, 'dat', t.name)
    setmenu(d, 'firstrow',    ['Use As Names', 'Names'])
    setmenu(d, 'firstcolumn', ['Use As Values', 'Values'])
    setmenu(d, 'output',      ['Channel per Column'])
    pal_chops.append(d)

# palette custom: sette Constant CHOP uniti in sette campioni
consts = []
for i, s in enumerate(SIGLE):
    cc = sub('constantCHOP', 'palc_' + s, -1500, 1350 + i * 45)
    for j, ch in enumerate('rgb'):
        setp(cc, 'name%d' % j, ch, find=r'^name%d$' % j)
        setx(cc, 'value%d' % j, 'parent().par.Palcol%s%s' % (s, ch),
             find=r'^value%d$' % j)
    consts.append(cc)

pal_custom = sub('joinCHOP', 'pal_custom', -1350, 1350)
for i, cc in enumerate(consts):
    pal_custom.inputConnectors[i].connect(cc)
pal_chops.append(pal_custom)

pal_switch = sub('switchCHOP', 'palette_chop', -1150, 900)
for i, d in enumerate(pal_chops):
    pal_switch.inputConnectors[i].connect(d)
setx(pal_switch, 'index', 'parent().par.Palette.menuIndex')

def color_chain(prefix, seed_expr, y, end_expr):
    rnd = noise(prefix + '_rand_col', 'index', end_expr, seed_expr, -1350, y)
    q = sub('mathCHOP', prefix + '_col_idx', -1200, y)
    q.inputConnectors[0].connect(rnd)
    setp(q, 'fromrange1', -1); setp(q, 'fromrange2', 1)
    setp(q, 'torange1', 0);    setp(q, 'torange2', PAL_LEN - 0.001)
    setmenu(q, 'integer', ['Floor', 'Floor (Round Down)'])
    nrm = sub('mathCHOP', prefix + '_col_nrm', -1050, y)
    nrm.inputConnectors[0].connect(q)
    setp(nrm, 'gain', 1.0 / (PAL_LEN - 1))
    lk = sub('lookupCHOP', prefix + '_color', -900, y)
    lk.inputConnectors[0].connect(nrm)
    lk.inputConnectors[1].connect(pal_switch)
    setp(lk, 'index1', 0)
    setp(lk, 'index2', 1)
    return lk

# ================================================================ FORME: moto
fg_start = noise('fg_start', 'tx ty', END_FG, 'parent().par.Seed + 4', -1350, 60)
fg_start_m = sub('mathCHOP', 'fg_start_pos', -1200, 60)
fg_start_m.inputConnectors[0].connect(fg_start)
setp(fg_start_m, 'gain', WRAP_X)

fg_dir = noise('fg_dir', 'tx ty', END_FG, 'parent().par.Seed + 5', -1350, -20)
fg_scroll = sub('mathCHOP', 'fg_scroll', -1200, -20)
fg_scroll.inputConnectors[0].connect(fg_dir)
setx(fg_scroll, 'gain', 'absTime.seconds * parent().par.Speedfg * 3')

fg_org = noise('fg_org', 'tx ty', END_FG, 'parent().par.Seed', -1350, -100,
               kind='Perlin', period_expr='parent().par.Noiseperiod',
               tz_expr='absTime.seconds * parent().par.Noisespeed')
fg_org_m = sub('mathCHOP', 'fg_wander', -1200, -100)
fg_org_m.inputConnectors[0].connect(fg_org)
setx(fg_org_m, 'gain', 'parent().par.Wander')

fg_sum = sub('mathCHOP', 'fg_sum', -1050, 0)
for i, o in enumerate([fg_start_m, fg_scroll, fg_org_m]):
    fg_sum.inputConnectors[i].connect(o)
setmenu(fg_sum, 'chopop', ['Add'])

fg_selx = sub('selectCHOP', 'fg_sel_tx', -900, 60)
fg_selx.inputConnectors[0].connect(fg_sum)
setp(fg_selx, 'channames', 'tx')
fg_wrapx = sub('limitCHOP', 'fg_wrap_tx', -750, 60)
fg_wrapx.inputConnectors[0].connect(fg_selx)
setmenu(fg_wrapx, 'type', ['Loop'])
setp(fg_wrapx, 'min', -WRAP_X); setp(fg_wrapx, 'max', WRAP_X)

fg_sely = sub('selectCHOP', 'fg_sel_ty', -900, -60)
fg_sely.inputConnectors[0].connect(fg_sum)
setp(fg_sely, 'channames', 'ty')
fg_wrapy = sub('limitCHOP', 'fg_wrap_ty', -750, -60)
fg_wrapy.inputConnectors[0].connect(fg_sely)
setmenu(fg_wrapy, 'type', ['Loop'])
setp(fg_wrapy, 'min', -WRAP_Y); setp(fg_wrapy, 'max', WRAP_Y)

fg_pos = sub('mergeCHOP', 'fg_pos', -600, 0)
fg_pos.inputConnectors[0].connect(fg_wrapx)
fg_pos.inputConnectors[1].connect(fg_wrapy)

# ================================================================ ROTAZIONE
# Z: angolo casuale fisso + rotazione continua
rot_rnd = noise('fg_rand_rot', 'rz', END_FG, 'parent().par.Seed + 6', -1350, -160)
fg_rotz = sub('mathCHOP', 'fg_rotz', -1200, -160)
fg_rotz.inputConnectors[0].connect(rot_rnd)
setx(fg_rotz, 'gain',
     'parent().par.Rotrand * 180 + absTime.seconds * parent().par.Spin * 60')

# X e Y: inclinazione casuale + rotazione continua. In ortografica una forma
# piatta che ruota su X o Y si limita a schiacciarsi: serve la prospettiva.
rot3_rnd = noise('fg_rand_rot3', 'rx ry', END_FG, 'parent().par.Seed + 8', -1350, -220)
fg_rotx = sub('mathCHOP', 'fg_rot3', -1200, -220)
fg_rotx.inputConnectors[0].connect(rot3_rnd)
setx(fg_rotx, 'gain', 'parent().par.Tiltrand * 90')

fg_spin3 = sub('expressionCHOP', 'fg_spin3', -1050, -220)
fg_spin3.inputConnectors[0].connect(fg_rotx)
setx(fg_spin3, 'expr0',
     "me.inputVal + absTime.seconds * 60 *"
     " (parent().par.Spinx if me.chanIndex == 0 else parent().par.Spiny)")

fg_rot = sub('mergeCHOP', 'fg_rot', -900, -190)
fg_rot.inputConnectors[0].connect(fg_rotz)
fg_rot.inputConnectors[1].connect(fg_spin3)

# ================================================================ MISURE
fg_rsize = noise('fg_rand_size', 'sy', END_FG, 'parent().par.Seed + 1', -1200, -300)
fg_sy = sub('mathCHOP', 'fg_size_y', -1050, -300)
fg_sy.inputConnectors[0].connect(fg_rsize)
setp(fg_sy, 'fromrange1', -1); setp(fg_sy, 'fromrange2', 1)
setx(fg_sy, 'torange1', 'parent().par.Sizemin * %f' % ORTHO_H)
setx(fg_sy, 'torange2', 'parent().par.Sizemax * %f' % ORTHO_H)

fg_sx = sub('mathCHOP', 'fg_size_x', -900, -340)
fg_sx.inputConnectors[0].connect(fg_sy)
setx(fg_sx, 'gain', 'parent().par.Aspect')
fg_sxr = rename_to(fg_sx, 'sx', -750, -340)

fg_size = sub('mergeCHOP', 'fg_size', -600, -300)
fg_size.inputConnectors[0].connect(fg_sy)
fg_size.inputConnectors[1].connect(fg_sxr)

# ================================================================ TIPO
# deterministico sull'indice: il rumore con pochi campioni dava lo stesso
# valore a tutte le istanze. Distribuito solo fra i tipi ATTIVI.
fg_rshape = noise('fg_rand_shape', 'shape', END_FG, 'parent().par.Seed + 2', -1350, -420)
fg_pick = sub('expressionCHOP', 'fg_shape_pick', -1200, -420)
fg_pick.inputConnectors[0].connect(fg_rshape)
setx(fg_pick, 'expr0',
     "(lambda att: att[(me.sampleIndex * 7 + int(parent().par.Seed) * 13) % len(att)]"
     " if att else -1)"
     "([i for i, t in enumerate(["
     "parent().par.Shapecircle, parent().par.Shaperect, parent().par.Shapehex"
     "]) if t])")

fg_shape = sub('mathCHOP', 'fg_shape', -1050, -420)
fg_shape.inputConnectors[0].connect(fg_pick)
setp(fg_shape, 'fromrange1', 0); setp(fg_shape, 'fromrange2', 2)
setp(fg_shape, 'torange1', 0);   setp(fg_shape, 'torange2', 2)

MASKS = [('active0', 'Shapecircle'), ('active1', 'Shaperect'), ('active2', 'Shapehex')]
mask_ops = []
for i, (chan, par) in enumerate(MASKS):
    e = sub('expressionCHOP', 'mask_%d' % i, -900, -420 - i * 70)
    e.inputConnectors[0].connect(fg_shape)
    setx(e, 'expr0',
         '(1 if int(me.inputVal) == %d else 0) * int(parent().par.%s)' % (i, par))
    mask_ops.append(rename_to(e, chan, -750, -420 - i * 70))

fg_masks = sub('mergeCHOP', 'fg_masks', -600, -490)
for i, m in enumerate(mask_ops):
    fg_masks.inputConnectors[i].connect(m)

fg_color = color_chain('fg', 'parent().par.Colorseed', -700, END_FG)

fg_merge = sub('mergeCHOP', 'fg_merge', -400, -300)
for i, o in enumerate([fg_pos, fg_rot, fg_size, fg_masks, fg_color]):
    fg_merge.inputConnectors[i].connect(o)
inst_fg = sub('nullCHOP', 'inst_fg', -250, -300)
inst_fg.inputConnectors[0].connect(fg_merge)

# ================================================================ SFONDO
EXT = "(%f if parent().par.Bgdir.menuIndex == 0 else %f)" % (ORTHO_W, ORTHO_H)

bg_n = noise('bg_n', 'pos', END_BG, 'parent().par.Seed + 9', -1500, 300, amp=0)
bg_base = sub('expressionCHOP', 'bg_base', -1350, 300)
bg_base.inputConnectors[0].connect(bg_n)
setx(bg_base, 'expr0',
     "(me.sampleIndex / max(1, parent().par.Bgcount) - 0.5) * " + EXT)

bg_org = noise('bg_org', 'pos', END_BG, 'parent().par.Seed + 7', -1500, 220,
               kind='Perlin', period_expr='parent().par.Noiseperiod',
               tz_expr='absTime.seconds * parent().par.Noisespeed * 0.5')
bg_wan = sub('mathCHOP', 'bg_wander', -1350, 220)
bg_wan.inputConnectors[0].connect(bg_org)
setx(bg_wan, 'gain', 'parent().par.Bgwander')

bg_sum = sub('mathCHOP', 'bg_pos', -1200, 260)
bg_sum.inputConnectors[0].connect(bg_base)
bg_sum.inputConnectors[1].connect(bg_wan)
setmenu(bg_sum, 'chopop', ['Add'])
setx(bg_sum, 'postoff', 'absTime.seconds * parent().par.Speedbg * 3')

bg_wrap = sub('limitCHOP', 'bg_wrap', -1050, 260)
bg_wrap.inputConnectors[0].connect(bg_sum)
setmenu(bg_wrap, 'type', ['Loop'])
setx(bg_wrap, 'min', '-' + EXT + ' * 0.75')
setx(bg_wrap, 'max',  EXT + ' * 0.75')

bg_ex = sub('expressionCHOP', 'bg_x', -900, 300)
bg_ex.inputConnectors[0].connect(bg_wrap)
setx(bg_ex, 'expr0', 'me.inputVal * (1 if parent().par.Bgdir.menuIndex == 0 else 0)')
bg_tx = rename_to(bg_ex, 'tx', -750, 300)

bg_ey = sub('expressionCHOP', 'bg_y', -900, 220)
bg_ey.inputConnectors[0].connect(bg_wrap)
setx(bg_ey, 'expr0', 'me.inputVal * (1 if parent().par.Bgdir.menuIndex == 1 else 0)')
bg_ty = rename_to(bg_ey, 'ty', -750, 220)

bg_xy = sub('mergeCHOP', 'bg_xy', -600, 260)
bg_xy.inputConnectors[0].connect(bg_tx)
bg_xy.inputConnectors[1].connect(bg_ty)

bg_color = color_chain('bg', 'parent().par.Colorseed + 11', 140, END_BG)

bg_merge = sub('mergeCHOP', 'bg_merge', -400, 260)
bg_merge.inputConnectors[0].connect(bg_xy)
bg_merge.inputConnectors[1].connect(bg_color)
inst_bg = sub('nullCHOP', 'inst_bg', -250, 260)
inst_bg.inputConnectors[0].connect(bg_merge)

# ================================================================ TEXTURE
tex_white = sub('constantTOP', 'tex_white', 250, -700)
for ch in 'rgb':
    setp(tex_white, 'color' + ch, 1)
setp(tex_white, 'alpha', 1)
force_res(tex_white, str(TEX_RES), str(TEX_RES))

tex_ramp = sub('rampTOP', 'tex_ramp', 250, -770)
setx(tex_ramp, 'type', 'parent().par.Texramp.eval()')
force_res(tex_ramp, str(TEX_RES), str(TEX_RES))

def cell_top(name, y):
    t = sub('rectangleTOP', name, 250, y)
    setp(t, 'sizex', 1); setp(t, 'sizey', 1)
    for ch in 'rgb':
        setp(t, 'fillcolor' + ch, 1)     # interno bianco: lascia il colore
        setp(t, 'border' + ch, 0)        # bordo nero: e' la linea
    setp(t, 'fillalpha', 1)
    setp(t, 'borderalpha', 1)
    setx(t, 'borderwidth', 'parent().par.Texwidth * 100')
    force_res(t, str(TEX_RES), str(TEX_RES))
    return t

tex_cell = cell_top('tex_cell', -840)
tex_grid = sub('tileTOP', 'tex_grid', 400, -840)
tex_grid.inputConnectors[0].connect(tex_cell)
setx(tex_grid, 'repeatx', 'parent().par.Texdiv')
setx(tex_grid, 'repeaty', 'parent().par.Texdiv')
tex_border = cell_top('tex_border', -910)

# testo: la griglia e' costruita nell'espressione, cosi' TD vede le
# dipendenze dai parametri e ricuoce quando li muovi
txt_top = sub('textTOP', 'txt_top', 250, -980)
setx(txt_top, 'text',
     "'\\n'.join("
     "''.join("
     "(str(parent().par.Textchars)["
     "(r*7 + c*13 + int(parent().par.Seed)) % max(1, len(str(parent().par.Textchars)))"
     "]"
     " if ((r*31 + c*17 + int(parent().par.Seed)*7) % 100) / 100.0"
     " < parent().par.Textdensity else ' ')"
     " for c in range(int(parent().par.Textcols)))"
     " for r in range(int(parent().par.Textrows)))"
     " if parent().par.Textmode.menuIndex == 0 else str(parent().par.Textstring)")
# il corpo si ricava dalla griglia: cosi' i glifi restano sempre dentro
setx(txt_top, 'fontsizex',
     "%d / max(1, max(int(parent().par.Textcols), int(parent().par.Textrows)))"
     " * parent().par.Textsize" % TEX_RES, find=r'^fontsize(x)?$')
setmenu(txt_top, 'alignx', ['Center'], find=r'^alignx$')
setmenu(txt_top, 'aligny', ['Center'], find=r'^aligny$')
for ch in 'rgb':
    setx(txt_top, 'fontcolor' + ch, 'parent().par.Textcolor%s' % ch,
         find=r'^fontcolor' + ch + r'$')
    setx(txt_top, 'bgcolor' + ch, 'parent().par.Textbg%s' % ch,
         find=r'^bgcolor' + ch + r'$')
setp(txt_top, 'fontalpha', 1, find=r'^fontalpha$')
setp(txt_top, 'bgalpha', 1, find=r'^bgalpha$')
force_res(txt_top, str(TEX_RES), str(TEX_RES))

# menu del carattere costruito sui font realmente installati
fp = getattr(txt_top.par, 'font', None)
if fp is not None and fp.isMenu:
    inst = [str(x) for x in fp.menuNames]
    bassi = [x.lower() for x in inst]
    disp = [inst[bassi.index(f.lower())] for f in FONT_PREFERITI if f.lower() in bassi]
    if disp:
        pgt = None
        for p in c.customPages:
            if p.name == 'Testo':
                pgt = p
        fpar = pgt.appendMenu('Textfont', label='Carattere')[0]
        fpar.menuNames = disp
        fpar.menuLabels = disp
        fpar.default = disp[0]
        fpar.val = disp[0]
        fp.expr = 'parent().par.Textfont.eval()'

tex_switch = sub('switchTOP', 'tex_switch', 550, -820)
for i, o in enumerate([tex_white, tex_ramp, tex_grid, tex_border, txt_top]):
    tex_switch.inputConnectors[i].connect(o)
setx(tex_switch, 'index', 'parent().par.Texmode.menuIndex')

tex_null = sub('nullTOP', 'tex_null', 700, -820)
tex_null.inputConnectors[0].connect(tex_switch)

# ================================================================ MATERIALI
mat_fg = sub('constantMAT', 'mat_fg', 50, -600)
setp(mat_fg, 'colormap', 'tex_null')
setx(mat_fg, 'wireframe', 'parent().par.Wireframe')
setx(mat_fg, 'wirewidth', 'parent().par.Wirewidth')

mat_bg = sub('constantMAT', 'mat_bg', 50, -660)
setx(mat_bg, 'wireframe', 'parent().par.Wireframebg')
setx(mat_bg, 'wirewidth', 'parent().par.Wirewidth')

# ================================================================ GEOMETRIE
def make_geo(name, x, y, chop, active_chan, use_scale, use_rot, mat, sop_builder):
    g = sub('geometryCOMP', name, x, y)
    for child in list(g.children):
        child.destroy()
    sop_builder(g)
    setp(g, 'instancing', True)
    setp(g, 'instanceop', chop)          # fratello: nome nudo
    setp(g, 'instancetx', 'tx')
    setp(g, 'instancety', 'ty')
    if active_chan:
        setp(g, 'instanceactive', active_chan)
    if use_scale:
        setp(g, 'instancesx', 'sx')
        setp(g, 'instancesy', 'sy')
    if use_rot:
        setp(g, 'instancerx', 'rx')
        setp(g, 'instancery', 'ry')
        setp(g, 'instancerz', 'rz')
    setp(g, 'instancecolorop', chop)
    setmenu(g, 'instancecolormode', ['Multiply'])   # moltiplica la texture
    setp(g, 'instancer', 'r')
    setp(g, 'instanceg', 'g')
    setp(g, 'instanceb', 'b')
    setp(g, 'material', mat.name)
    return g

def sop_circle(g):
    s = mk(g, 'circleSOP', 'shape', 0, 0)
    setp(s, 'radx', 0.5); setp(s, 'rady', 0.5)
    setmenu(s, 'type', ['Polygon']); setp(s, 'divs', 64)
    set_uv(s); setflags(s)

def sop_rect(g):
    s = mk(g, 'rectangleSOP', 'shape', 0, 0)
    setp(s, 'sizex', 1); setp(s, 'sizey', 1)
    set_uv(s); setflags(s)

def sop_hex(g):
    s = mk(g, 'circleSOP', 'shape', 0, 0)
    setp(s, 'radx', 0.5); setp(s, 'rady', 0.5)
    setmenu(s, 'type', ['Polygon']); setp(s, 'divs', 6)
    set_uv(s); setflags(s)

def sop_bgquad(g):
    s = mk(g, 'rectangleSOP', 'shape', 0, 0)
    setx(s, 'sizex',
         "(%f / max(1, parent(2).par.Bgcount) * parent(2).par.Bgsize)"
         " if parent(2).par.Bgdir.menuIndex == 0 else %f" % (ORTHO_W, ORTHO_W + 1))
    setx(s, 'sizey',
         "%f if parent(2).par.Bgdir.menuIndex == 0 else"
         " (%f / max(1, parent(2).par.Bgcount) * parent(2).par.Bgsize)"
         % (ORTHO_H + 1, ORTHO_H))
    set_uv(s); setflags(s)

make_geo('geo_circle', 50, -300, 'inst_fg', 'active0', True, True, mat_fg, sop_circle)
make_geo('geo_rect',   50, -370, 'inst_fg', 'active1', True, True, mat_fg, sop_rect)
make_geo('geo_hex',    50, -440, 'inst_fg', 'active2', True, True, mat_fg, sop_hex)
make_geo('geo_bg',     50,  260, 'inst_bg', None,      False, False, mat_bg, sop_bgquad)

# ================================================================ CAMERA
cam = sub('cameraCOMP', 'cam', 50, 0)
setp(cam, 'orthowidth', ORTHO_W)
setp(cam, 'tz', 10)
setp(cam, 'fov', 48, find=r'^fov$')     # inquadratura simile all'ortografica
pr = getattr(cam.par, 'projection', None)
if pr is not None and pr.isMenu:
    nomi = [str(x) for x in pr.menuNames]
    bassi = [x.lower() for x in nomi]
    n_persp = next((nomi[i] for i, b in enumerate(bassi) if 'pers' in b), None)
    n_ortho = next((nomi[i] for i, b in enumerate(bassi) if 'ortho' in b), None)
    if n_persp and n_ortho:
        pr.expr = "'%s' if parent().par.Persp else '%s'" % (n_persp, n_ortho)
    else:
        setmenu(cam, 'projection', ['Orthographic', 'Ortho'])

# ================================================================ RENDER
def make_render(name, geos, x, y):
    r = sub('renderTOP', name, x, y)
    setp(r, 'camera', 'cam')
    setp(r, 'geometry', geos)
    force_res(r, RESW, RESH)
    return r

render_bg = make_render('render_bg', 'geo_bg', 250, 260)
render_fg = make_render('render_fg', 'geo_circle geo_rect geo_hex', 250, -300)

bg_level = sub('levelTOP', 'bg_level', 400, 260)
bg_level.inputConnectors[0].connect(render_bg)
setx(bg_level, 'opacity', 'parent().par.Bgopacity')

# ================================================================ TAGLIO
SHADER_SLICE = """// taglio a bande, deriva continua (nessuna oscillazione)
// uP: x = numero bande  y = spostamento  z = tempo  w = irregolarita'
// uQ: x = modalita' (0 = orizzontali, 1 = verticali, 2 = entrambe)
out vec4 fragColor;
uniform vec4 uP;
uniform vec4 uQ;

float hash(float n) { return fract(sin(n * 127.1) * 43758.5453); }

// la deriva cresce nel tempo, il fract la fa rientrare dall'altro lato
float bandShift(float b)
{
    float calmo = 0.3 + 0.7 * hash(b + 5.0);            // stesso verso
    float rotto = (hash(b + 9.0) * 2.0 - 1.0) * 2.0;    // versi misti
    return uP.z * mix(calmo, rotto, uP.w) * uP.y;
}

void main()
{
    vec2 uv = vUV.st;
    vec2 st = uv;
    int  mode = int(uQ.x + 0.5);
    float bands = max(2.0, uP.x);

    if (mode == 0 || mode == 2) {
        float b = floor(uv.y * bands);
        st.x = fract(st.x + bandShift(b));
    }
    if (mode == 1 || mode == 2) {
        float b = floor(uv.x * bands) + 137.0;   // indice dalla X ORIGINALE
        st.y = fract(st.y + bandShift(b));
    }

    fragColor = TDOutputSwizzle(texture(sTD2DInputs[0], st));
}
"""
sl_text = sub('textDAT', 'sl_glsl_text', 400, -140)
sl_text.text = SHADER_SLICE

def slice_stage(name, src, prefix, x, y, enable_par):
    g = sub('glslTOP', name + '_glsl', x, y)
    g.inputConnectors[0].connect(src)
    setp(g, 'pixeldat', 'sl_glsl_text', find=r'.*pixeldat.*')
    setp(g, 'uniname0', 'uP', find=r'^uniname0$')
    setx(g, 'value0x', 'parent().par.%sbands' % prefix,  find=r'^(value|uni)0x$')
    setx(g, 'value0y', 'parent().par.%samount' % prefix, find=r'^(value|uni)0y$')
    setx(g, 'value0z', 'absTime.seconds * parent().par.%sspeed' % prefix,
         find=r'^(value|uni)0z$')
    setx(g, 'value0w', 'parent().par.%schaos' % prefix,  find=r'^(value|uni)0w$')
    setp(g, 'uniname1', 'uQ', find=r'^uniname1$')
    setx(g, 'value1x', 'parent().par.%sdir.menuIndex' % prefix, find=r'^(value|uni)1x$')
    force_res(g, RESW, RESH)
    sw = sub('switchTOP', name + '_switch', x + 150, y + 60)
    sw.inputConnectors[0].connect(src)
    sw.inputConnectors[1].connect(g)
    setx(sw, 'index', 'parent().par.%s' % enable_par)
    return sw

sl_switch = slice_stage('sl', render_fg, 'Slice', 400, -300, 'Sliceenable')

# ================================================================ COMPOSITE
comp = sub('compositeTOP', 'comp', 700, 0)
comp.inputConnectors[0].connect(bg_level)
comp.inputConnectors[1].connect(sl_switch)
setx(comp, 'operand', 'parent().par.Blend.eval()')
force_res(comp, RESW, RESH)

# ================================================================ EDGE
edge = sub('edgeTOP', 'ed_edge', 850, 120)
edge.inputConnectors[0].connect(comp)
setx(edge, 'strength', 'parent().par.Edgestrength', find=r'^strength$')
ed_switch = sub('switchTOP', 'ed_switch', 850, 0)
ed_switch.inputConnectors[0].connect(comp)
ed_switch.inputConnectors[1].connect(edge)
setx(ed_switch, 'index', 'parent().par.Edgeenable')

# ================================================================ TAGLIO FINALE
sl2_switch = slice_stage('sl2', ed_switch, 'Slicetwo', 1000, -120, 'Slicetwoenable')

# ================================================================ 8-BIT
SHADER_PIX = """// quantizzazione colore + dithering ordinato 4x4 (Bayer)
// uP: x = livelli per canale  y = intensita' dithering
out vec4 fragColor;
uniform vec4 uP;

const float bayer[16] = float[16](
     0.0,  8.0,  2.0, 10.0,
    12.0,  4.0, 14.0,  6.0,
     3.0, 11.0,  1.0,  9.0,
    15.0,  7.0, 13.0,  5.0
);

void main()
{
    vec4 src = texture(sTD2DInputs[0], vUV.st);
    float levels = max(2.0, uP.x);

    int bx = int(mod(gl_FragCoord.x, 4.0));
    int by = int(mod(gl_FragCoord.y, 4.0));
    float threshold = (bayer[by * 4 + bx] + 0.5) / 16.0 - 0.5;

    vec3 col = src.rgb + threshold * uP.y / levels;     // dither PRIMA
    col = clamp(floor(col * levels + 0.5) / levels, 0.0, 1.0);

    fragColor = TDOutputSwizzle(vec4(col, src.a));
}
"""
px_text = sub('textDAT', 'px_glsl_text', 1200, 160)
px_text.text = SHADER_PIX

PXDIV = "max(1, parent().par.Pixelsize.eval())"
px_down = sub('resolutionTOP', 'px_down', 1200, 0)
px_down.inputConnectors[0].connect(sl2_switch)
force_res(px_down,
          "max(8, int(%s.eval() / %s))" % (RESW, PXDIV),
          "max(8, int(%s.eval() / %s))" % (RESH, PXDIV))
setmenu(px_down, 'filter', ['Nearest Pixel', 'Nearest'], find=r'.*filter.*')

px_glsl = sub('glslTOP', 'px_glsl', 1350, 0)
px_glsl.inputConnectors[0].connect(px_down)
setp(px_glsl, 'pixeldat', 'px_glsl_text', find=r'.*pixeldat.*')
setp(px_glsl, 'uniname0', 'uP', find=r'^uniname0$')
setx(px_glsl, 'value0x', 'parent().par.Levels', find=r'^(value|uni)0x$')
setx(px_glsl, 'value0y', 'parent().par.Dither', find=r'^(value|uni)0y$')

px_up = sub('resolutionTOP', 'px_up', 1500, 0)
px_up.inputConnectors[0].connect(px_glsl)
force_res(px_up, RESW, RESH)
setmenu(px_up, 'filter', ['Nearest Pixel', 'Nearest'], find=r'.*filter.*')

px_switch = sub('switchTOP', 'px_switch', 1650, 0)
px_switch.inputConnectors[0].connect(sl2_switch)
px_switch.inputConnectors[1].connect(px_up)
setx(px_switch, 'index', 'parent().par.Pixelenable')

# ================================================================ SORTING
SHADER_SORT = """// ordinamento a trasposizione pari-dispari, per colonne
// sTD2DInputs[0] = immagine viva   sTD2DInputs[1] = stato del frame prima
// uP: x = fase (0/1)  y = soglia luminanza  z = rigenerazione
out vec4 fragColor;
uniform vec4 uP;

float lum(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

vec4 state(ivec2 p)
{
    vec4 prev = texelFetch(sTD2DInputs[1], p, 0);
    vec4 live = texelFetch(sTD2DInputs[0], p, 0);
    return mix(prev, live, uP.z);
}

void main()
{
    ivec2 res = textureSize(sTD2DInputs[1], 0);
    ivec2 uv  = ivec2(gl_FragCoord.xy);
    vec4 cur  = state(uv);

    // alternando la fase le coppie sono (0,1)(2,3)... poi (1,2)(3,4)...
    bool lower = ((uv.y + int(uP.x)) % 2 == 0);
    int  oy    = lower ? uv.y + 1 : uv.y - 1;

    if (oy < 0 || oy >= res.y) {
        fragColor = TDOutputSwizzle(cur);
        return;
    }

    vec4 other = state(ivec2(uv.x, oy));
    float a = lum(cur.rgb);
    float b = lum(other.rgb);

    // sotto soglia i pixel non partecipano: decide DOVE si spezza
    if (a > uP.y && b > uP.y) {
        if (lower  && a > b) cur = other;
        if (!lower && b > a) cur = other;
    }

    fragColor = TDOutputSwizzle(cur);
}
"""
ps_text = sub('textDAT', 'ps_glsl_text', 1800, 160)
ps_text.text = SHADER_SORT

SDIV = "max(1, parent().par.Sortscale.eval())"
SW_ = "max(8, int(%s.eval() / %s))" % (RESW, SDIV)
SH_ = "max(8, int(%s.eval() / %s))" % (RESH, SDIV)

ps_down = sub('resolutionTOP', 'ps_down', 1800, 0)
ps_down.inputConnectors[0].connect(px_switch)
force_res(ps_down, SW_, SH_)
setmenu(ps_down, 'filter', ['Nearest Pixel', 'Nearest'], find=r'.*filter.*')

ps_glsl = sub('glslTOP', 'ps_glsl', 1950, 0)
ps_glsl.inputConnectors[0].connect(ps_down)
setp(ps_glsl, 'pixeldat', 'ps_glsl_text', find=r'.*pixeldat.*')
setp(ps_glsl, 'uniname0', 'uP', find=r'^uniname0$')
setx(ps_glsl, 'value0x', 'absTime.frame % 2',        find=r'^(value|uni)0x$')
setx(ps_glsl, 'value0y', 'parent().par.Sortthresh',  find=r'^(value|uni)0y$')
setx(ps_glsl, 'value0z', 'parent().par.Sortrefresh', find=r'^(value|uni)0z$')
force_res(ps_glsl, SW_, SH_)

ps_null = sub('nullTOP', 'ps_null', 2100, 0)
ps_null.inputConnectors[0].connect(ps_glsl)

# l'ordinamento E' uno stato che si accumula fra i frame
ps_fb = sub('feedbackTOP', 'ps_fb', 1950, 90)
setp(ps_fb, 'top', 'ps_null')
force_res(ps_fb, SW_, SH_)
ps_glsl.inputConnectors[1].connect(ps_fb)

ps_up = sub('resolutionTOP', 'ps_up', 2250, 0)
ps_up.inputConnectors[0].connect(ps_null)
force_res(ps_up, RESW, RESH)
setmenu(ps_up, 'filter', ['Nearest Pixel', 'Nearest'], find=r'.*filter.*')

ps_switch = sub('switchTOP', 'ps_switch', 2400, 0)
ps_switch.inputConnectors[0].connect(px_switch)
ps_switch.inputConnectors[1].connect(ps_up)
setx(ps_switch, 'index', 'parent().par.Sortenable')

# ================================================================ USCITA
out = sub('nullTOP', 'out1', 2550, 0)
out.inputConnectors[0].connect(ps_switch)
setp(c, 'opviewer', out.path)

# ================================================================ PULSANTI
pex = sub('parameterexecuteDAT', 'reseed_exec', 2550, 150)
setp(pex, 'op', '.')
setp(pex, 'pars', 'Reseed Reseedcolor Palcopy')
setp(pex, 'onpulse', True)
setp(pex, 'valuechange', False)
setp(pex, 'active', True)
pex.text = (
    "import random\n\n"
    "SIGLE = ['a','b','c','d','e','f','g']\n\n"
    "def onPulse(par):\n"
    "    c = par.owner\n"
    "    if par.name == 'Reseed':\n"
    "        c.par.Seed = random.randint(0, 99999)\n"
    "    elif par.name == 'Reseedcolor':\n"
    "        c.par.Colorseed = random.randint(0, 99999)\n"
    "    elif par.name == 'Palcopy':\n"
    "        src = c.op('pal_%d' % c.par.Palette.menuIndex)\n"
    "        if src is None:\n"
    "            return   # gia' su Custom: niente da copiare\n"
    "        for n, s in enumerate(SIGLE):\n"
    "            for ch in 'rgb':\n"
    "                try:\n"
    "                    setattr(c.par, 'Palcol%s%s' % (s, ch), src[ch][n])\n"
    "                except Exception:\n"
    "                    pass\n"
    "    return\n"
)

# ================================================================ REPORT
print('=' * 74)
print('BLOCKS costruito in %s   uscita %d x %d' % (c.path, out.width, out.height))
if _warn:
    print('Parametri non settati (%d):' % len(_warn))
    for w in _warn:
        print('  - %s' % w)
else:
    print('Nessun warning.')
print('-' * 74)
try:
    ch = fg_shape.chans()[0]
    vals = [int(ch[i]) for i in range(fg_shape.numSamples)]
    nomi = {0: 'cerchio', 1: 'rettangolo', 2: 'esagono', -1: '-'}
    print('  tipi per istanza: %s' % [nomi.get(v, '?') for v in vals])
except Exception as e:
    print('  lettura tipi fallita: %s' % e)
for n in ['render_fg', 'comp', 'sl2_switch', 'px_switch', 'ps_switch', 'out1']:
    o = c.op(n)
    if o:
        print('  %-12s %4d x %-4d  errori: %s' % (o.name, o.width, o.height, o.errors() or '-'))
print('=' * 74)