
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
