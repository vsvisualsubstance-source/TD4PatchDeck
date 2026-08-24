# me - this DAT
# par - the Par object that has changed
# val - the current value
# prev - the previous value
# 
# Make sure the corresponding toggle is enabled in the Parameter Execute DAT.

def onValueChange(par, prev):
	# use par.eval() to get current value
	
	# display/hide menu sources in custom pars
	if op.Sndviz.par.Source == 'stream':
		op.Sndviz.par.Device.enable = True
		op.Sndviz.par.File.enable = False
		op.Sndviz.par.Cuefile.enable = False
		op.Sndviz.par.Playfile.enable = False
		op.Sndviz.par.Loopfile.enable = False
		
	elif op.Sndviz.par.Source == 'chop':
		op.Sndviz.par.Device.enable = False
		op.Sndviz.par.File.enable = False
		op.Sndviz.par.Cuefile.enable = False
		op.Sndviz.par.Playfile.enable = False
		op.Sndviz.par.Loopfile.enable = False
		
	else:
		op.Sndviz.par.Device.enable = False
		op.Sndviz.par.File.enable = True
		op.Sndviz.par.Cuefile.enable = True
		op.Sndviz.par.Playfile.enable = True
		op.Sndviz.par.Loopfile.enable = True
		
	# switch audio source (if present)
	switch = op('switch1')
	error = op('fileWarningError')
	
	if par.eval() == 'stream':
		switch.par.index = 0
	elif par.eval() == 'chop':
		switch.par.index = 1
	elif par.eval() == 'file':
		if error[0,0] > 0 or error[0,1] > 0:
			pass
		else:
			switch.par.index = 2
	
	return

def onPulse(par):
	return

def onExpressionChange(par, val, prev):
	return

def onExportChange(par, val, prev):
	return

def onEnableChange(par, val, prev):
	return

def onModeChange(par, val, prev):
	return
	