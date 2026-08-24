# me - this DAT
# scriptOp - the OP which is cooking
#
# press 'Setup Parameters' in the OP to call this function to re-create the parameters.
def onSetupParameters(scriptOp):
	return

# called whenever custom pulse parameter is pushed
def onPulse(par):
	return

def onCook(scriptOp):
	try:
		scriptOp.text = setupMenuOptions(scriptOp)
	except:
		scriptOp.text = "name\tlabel"
	#scriptOp.copy(scriptOp.inputs[0])	# no need to call .clear() above when copying
	#scriptOp.insertRow(['color', 'size', 'shape'], 0)
	#scriptOp.appendRow(['red', '3', 'square'])
	#scriptOp[1,0] += '**'

	return

def setupMenuOptions(scriptOp):
	if hasattr(parent.Widget.par, 'Synctoboundmenu'):
		parent.Widget.par.Menulabels.readOnly = \
			parent.Widget.par.Menunames.readOnly = \
									parent.Widget.par.Synctoboundmenu.eval()
	externalMenuTable = scriptOp.inputs[0]
	if externalMenuTable.numCols:
		labels = []
		#['AllRows_FirstCols', 'LabelRow_FirstCols', 'LabelRow_LabeledCols']
		if parent.Widget.par.Tableformat.eval() ==\
												'ExcludeFirstRow_LabeledCols':
			names = [c.val for c in externalMenuTable.col('name')[1:]]
			labelCol = externalMenuTable.col('label')
			if labelCol:
				labels = [c.val for c in labelCol[1:]]
		else:
			names = [c.val for c in externalMenuTable.col(0)]
			labelCol = externalMenuTable.col(1)
			if labelCol:
				labels = [c.val for c in labelCol]
			if parent.Widget.par.Tableformat.eval() == \
												'ExcludeFirstRow_NumberedCols':
				names.pop(0)
				if labels:
					labels.pop(0)
	else:
		names = tdu.split(parent.Widget.par.Menunames)
		labels = tdu.split(parent.Widget.par.Menulabels)
	finalNames = names
	finalLabels = []
	for i, name in enumerate(names):
		if i < len(labels):
			finalLabels.append(labels[i])
		else:
			finalLabels.append(name)
	return 'name\tlabel\n' + \
			'\n'.join([finalNames[i] + '\t' + finalLabels[i]
					   		for i in range(len(finalNames))])