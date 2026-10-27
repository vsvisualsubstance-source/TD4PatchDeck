# me - this DAT.
# 
# dat - the changed DAT
# rows - a list of row indices
# cols - a list of column indices
# cells - the list of cells that have changed content
# prev - the list of previous string contents of the changed cells
# 
# Make sure the corresponding toggle is enabled in the DAT Execute DAT.
# 
# If rows or columns are deleted, sizeChange will be called instead of row/col/cellChange.


def onTableChange(dat):
	
	return

def onRowChange(dat, rows):
	return

def onColChange(dat, cols):
	return

def onCellChange(dat, cells, prev):

	switch = op('switch1')
	info = op('fileWarningError')
	warnings = info[0,0]
	errors = info[0,1]
	
	
	if (warnings > 0):
		switch.par.index = 1
	else:
		switch.par.index = 2
	
	
	return

def onSizeChange(dat):
	return
	