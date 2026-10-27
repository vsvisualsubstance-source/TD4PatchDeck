# ui_exec — pulsanti e campo "Testo live" del pannello texttt
EDIT = {'Editall': 'src_all', 'Edit1': 'src_text1', 'Editphrase': 'src_phrase',
        'Edit2': 'src_text2', 'Edit3': 'src_text3', 'Editcode': 'code_phrases'}
KEEP = {'all': 'src_all', 'text1': 'src_text1', 'phrase': 'src_phrase',
        'text2': 'src_text2', 'text3': 'src_text3'}


def _send(comp):
    msg = comp.par.Inject.eval().strip()
    if not msg:
        return
    target = comp.par.Injectto.eval()
    q = comp.op('inject_queue')
    if q is not None:
        q.text = (q.text + '\n' if q.text else '') + target + '\t' + msg
    if comp.par.Injectkeep.eval():
        d = comp.op(KEEP.get(target, 'src_all'))
        if d is not None:
            d.text = d.text.rstrip('\n') + '\n' + msg
    if comp.par.Injectclear.eval():
        comp.par.Inject.val = ''


def onPulse(par):
    comp = par.owner
    if par.name == 'Send':
        _send(comp)
    elif par.name in EDIT:
        d = comp.op(EDIT[par.name])
        if d is not None:
            try:
                d.par.edit.pulse()
            except Exception:
                d.openViewer()
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
