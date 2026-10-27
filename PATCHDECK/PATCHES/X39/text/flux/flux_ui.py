# flux_ui — pulsanti e testo live del pannello flux


def _send(comp):
    msg = comp.par.Inject.eval().strip()
    if not msg:
        return
    q = comp.op('inject_flux')
    if q is not None:
        q.text = (q.text + '\n' if q.text else '') + comp.par.Injectto.eval() + '\t' + msg
    if comp.par.Injectclear.eval():
        comp.par.Inject.val = ''


def _open(d):
    if d is None:
        return
    try:
        d.par.edit.pulse()
    except Exception:
        d.openViewer()


def onPulse(par):
    comp = par.owner
    if par.name == 'Send':
        _send(comp)
    elif par.name == 'Editflux':
        _open(comp.op('src_flux'))
    elif par.name == 'Edittexttt':
        path = comp.par.Sourcecomp.eval()
        src = comp.op(path) if path else None
        _open(src.op('src_all') if src is not None else None)
    return


def onValueChange(par, prev):
    if par.name == 'Inject' and par.eval().strip():
        _send(par.owner)
    return


def onExpressionChange(*args):
    return

def onExportChange(*args):
    return

def onEnableChange(*args):
    return

def onModeChange(*args):
    return
