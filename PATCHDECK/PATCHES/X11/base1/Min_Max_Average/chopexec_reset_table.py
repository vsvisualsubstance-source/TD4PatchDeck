
def onOffToOn(channel, sampleIndex, val, prev):

	resetMIN = op('null1')[0]
	resetMAX = op('null1')[0] 

	op('table1')[1,'MIN'] = resetMIN
	op('table1')[1,'MAX'] = resetMAX

	return
