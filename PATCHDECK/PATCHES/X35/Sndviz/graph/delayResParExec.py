res = op.Sndviz.par.Pointcloudoutputresw
resOps = ['fit1', 'feedback1']

for operator in resOps:
	op(operator).par.resolutionw = res
	op(operator).par.resolutionh = res
	
	if operator == 'fit1':
		offset = round(res * 0.5)
		if offset % 2 != 0:
			offset -= 1
		else:
			pass

		#op(operator).par.tx = offset