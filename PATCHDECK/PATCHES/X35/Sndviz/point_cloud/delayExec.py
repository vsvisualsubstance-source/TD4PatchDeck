resx = op('hi').width
resy = op('hi').height

resOps = ['fit1', 'res1', 'feedback1', 'reorder1']
	
for operator in resOps:
	op(operator).par.resolutionw = resx
	op(operator).par.resolutionh = resy
	
	if operator == 'fit1':		
		offset = -(resy * 0.5 - 1)
		
		if op('par2')['Samplingquality'].eval() == 5:
			offset -= 1
		op(operator).par.ty = offset
		
	if operator == 'res1':
		op(operator).par.resolutionh = 1
		
	if operator == 'reorder1':
		op(operator).par.resolutionh = resx