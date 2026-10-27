
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
