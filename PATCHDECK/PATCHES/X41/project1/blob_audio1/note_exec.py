
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
