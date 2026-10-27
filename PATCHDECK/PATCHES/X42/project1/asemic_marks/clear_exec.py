
def onPulse(par):
    if par.name == 'Clear':
        d = par.owner.op('geo').op('marks_callbacks')
        mod(d).marks.clear()
    return
