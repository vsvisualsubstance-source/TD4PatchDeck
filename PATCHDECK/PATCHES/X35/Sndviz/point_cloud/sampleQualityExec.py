# me - this DAT
# 
# channel - the Channel object which has changed
# sampleIndex - the index of the changed sample
# val - the numeric value of the changed sample
# prev - the previous sample value
# 
# Make sure the corresponding toggle is enabled in the CHOP Execute DAT.

def onOffToOn(channel, sampleIndex, val, prev):
	return

def whileOn(channel, sampleIndex, val, prev):
	return

def onOnToOff(channel, sampleIndex, val, prev):
	return

def whileOff(channel, sampleIndex, val, prev):
	return

def onValueChange(channel, sampleIndex, val, prev):

	samplingOps = ['audiospect1', 'audiospect2', 'audiospect3']
	
	for operator in samplingOps:
		if val == 0:
			op(operator).par.fftsize = 3 #512
			op(operator).par.outlength = 512
		elif val == 1:
			op(operator).par.fftsize = 4 #1024
			op(operator).par.outlength = 1024
		elif val == 2:
			op(operator).par.fftsize = 5 #2048
			op(operator).par.outlength = 2048
		elif val == 3:
			op(operator).par.fftsize = 6 #4096
			op(operator).par.outlength = 4096
		elif val == 4:
			op(operator).par.fftsize = 7 #8192
			op(operator).par.outlength = 8192
		elif val == 5:
			op(operator).par.fftsize = 8 #16384
			op(operator).par.outlength = 16384

	op('delayExec').run(delayFrames = 15)
			
	return
	