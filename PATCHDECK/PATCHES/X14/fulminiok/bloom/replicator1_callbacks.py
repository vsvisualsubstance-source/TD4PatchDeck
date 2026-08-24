# me - this DAT
# 
# comp - the replicator component which is cooking
# allOps - a list of all replicants, created or existing
# newOps - the subset that were just created
# template - table DAT specifying the replicator attributes
# master - the master operator
#


connect = '''
comp = args[0]
allOps = args[1]
numIter = comp.par.numreplicants.eval()


for i, c in enumerate(allOps):



	if i == 0:
		op('level1').outputConnectors[0].connect(c.inputConnectors[0])
		c.outputConnectors[1].connect(op('blurUp').inputConnectors[0])


	else:

		prev = op(c.base + str(i- 1))

		if i == numIter - 1:

			c.outputConnectors[0].connect(op('blurDown').inputConnectors[0])
			op('blurDown').outputConnectors[0].connect(c.inputConnectors[1])
			c.outputConnectors[1].connect(prev.inputConnectors[1])
			prev.outputConnectors[0].connect(c.inputConnectors[0])
			
			op('blurDown').nodeY = c.nodeY - 200

		else:

			#if i != 1:
			c.outputConnectors[1].connect(prev.inputConnectors[1])
			
			prev.outputConnectors[0].connect(c.inputConnectors[0])
			

'''


def onReplicate(comp, allOps, newOps, template, master):

	run(connect, comp, allOps, delayFrames=1)

	for c in newOps:
		
		c.par.clone = master
		

		pass

	return
