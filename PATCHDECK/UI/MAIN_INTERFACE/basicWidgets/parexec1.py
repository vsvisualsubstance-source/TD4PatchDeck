# me - this DAT
# par - the Par object that has changed
# val - the current value
# prev - the previous value
# 
# Make sure the corresponding toggle is enabled in the Parameter Execute DAT.

def onValueChange(par, prev):
	return

def onPulse(par):
	if par.name == 'Updatedeployed':
		updateDeployed()

def onExpressionChange(par, val, prev):
	return

def onExportChange(par, val, prev):
	return

def onEnableChange(par, val, prev):
	return

def onModeChange(par, val, prev):
	return

def updateDeployed():
	widgets = op('/').findChildren(tags=('TDBasicWidget',))
	deployed = [w for w in widgets if w.par.clone.eval()
				and w.par.clone.eval().parent() == me.parent()
				and w.par.clone.eval() != w]
	op.TDUpdater.Update(deployed, updater=op('TDUpdateSystem'))