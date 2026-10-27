
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
