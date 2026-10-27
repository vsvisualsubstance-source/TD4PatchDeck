
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
