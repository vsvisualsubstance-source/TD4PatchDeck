def onValueChange(channel, sampleIndex, val, prev):

	max = op('table1')[1,1]
	min = op('table1')[1,0]

	if val < min:
		min = val
		op('table1')[1,'MIN'] = round(min,3)
	
	if val > max:
		max = val
		op('table1')[1,'MAX'] = round(max,3)


	op('table1')[1,'AVERAGE'] = round((max + min) /2, 3)


	return
	