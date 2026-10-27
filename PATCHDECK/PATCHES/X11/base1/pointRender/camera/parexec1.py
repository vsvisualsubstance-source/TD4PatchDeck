# me - this DAT
# par - the Par object that has changed
# val - the current value
# prev - the previous value
# 
# Make sure the corresponding toggle is enabled in the Parameter Execute DAT.

def onValueChange(par, prev):
	# use par.eval() to get current value
	return

def onPulse(par):

	if par.name == "Reset":
		parent.Camera.Reset();
		
	elif par.name == "Home":
		parent.Camera.Home(False);
		
	elif par.name == "Homeselected":
		parent.Camera.Home(True);
		
	elif par.name == "Frame":
		parent.Camera.Frame(False);
		
	elif par.name == "Frameselected":
		parent.Camera.Frame(True);
		
	return

def onExpressionChange(par, val, prev):
	return

def onExportChange(par, val, prev):
	return

def onEnableChange(par, val, prev):
	return

def onModeChange(par, val, prev):
	return
	