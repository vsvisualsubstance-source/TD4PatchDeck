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

	floatOps = ['hi', 'mid', 'low', 'all']
	
	for operator in floatOps:
		if val == 0:
			op(operator).par.format = 11 # 8-bit float mono
		elif val == 1:
			op(operator).par.format = 13 # 16-bit float mono
		elif val == 2:
			op(operator).par.format = 14 # 32-bit float mono
			
	vec4Ops = ['reorder1']
	
	for operator in vec4Ops:
		if val == 0:
			op(operator).par.format = 2 # 8-bit fixed rgba
		elif val == 1:
			op(operator).par.format = 3 # 16-bit float rgba
		elif val == 2:
			op(operator).par.format = 4 # 32-bit float rgba
	
	return
	