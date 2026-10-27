# seq_ui — pulsanti delle pagine Presets e Timeline


def _cmd(comp, line):
    q = comp.op('seq_cmd')
    if q is not None:
        q.text = (q.text + '\n' if q.text else '') + line


def _open(d):
    if d is None:
        return
    try:
        d.par.edit.pulse()
    except Exception:
        d.openViewer()


def onPulse(par):
    c = par.owner
    n = par.name
    if n == 'Presetsave':
        name = c.par.Presetname.eval().strip() or 'preset'
        _cmd(c, 'save\t' + name)
    elif n == 'Presetload':
        _cmd(c, 'load\t' + c.par.Presetlist.eval())
    elif n == 'Presetdelete':
        _cmd(c, 'delete\t' + c.par.Presetlist.eval())
    elif n == 'Presetstarters':
        _cmd(c, 'starters')
    elif n == 'Seqnext':
        _cmd(c, 'next')
    elif n == 'Seqprev':
        _cmd(c, 'prev')
    elif n == 'Seqrestart':
        _cmd(c, 'restart')
    elif n == 'Editpresets':
        _open(c.op('presets_json'))
    elif n == 'Editsequence':
        _open(c.op('sequence'))
    return


def onValueChange(par, prev):
    return


def onExpressionChange(*args):
    return

def onExportChange(*args):
    return

def onEnableChange(*args):
    return

def onModeChange(*args):
    return
