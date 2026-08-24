"""
Script CHOP Callbacks

me - this DAT

scriptOp - the OP which is cooking
"""

from typing import Any

# press 'Setup Parameters' in the OP to call this function to re-create the
# parameters.
def onSetupParameters(scriptOp: scriptCHOP):
	"""
	Called to setup custom parameters for the Script CHOP.
	"""
	page = scriptOp.appendCustomPage('Custom')
	p = page.appendFloat('Valuea', label='Value A')
	p = page.appendFloat('Valueb', label='Value B')
	return

def onPulse(par: Any):
	"""
	Called when a custom pulse parameter is pushed.
	
	Args:
		par: The parameter that was pulsed
	"""
	return

CATEGORY = '/meta/'

def onCook(scriptOp: scriptCHOP):
	"""
	Called when the Script CHOP needs to cook.

	Passthrough of oscin_mocap's meta/faces|hands|poses counters -- always
	exactly 3 channels, no bounding needed.
	"""
	scriptOp.clear()
	src = op('oscin_mocap')
	if src is None:
		return

	scriptOp.numSamples = 1
	for c in src.chans():
		if CATEGORY not in c.name:
			continue
		name = c.name.split(CATEGORY, 1)[1]
		chan = scriptOp.appendChan(name)
		chan[0] = c.eval()
	return

def onGetCookLevel(scriptOp: scriptCHOP) -> CookLevel:
	"""
	Sets the scriptOp's cook level, the conditions necessary to cause a cook.

	Return one of the following:
		CookLevel.AUTOMATIC - inputs changed and output being used. TD default
							  behavior.
		CookLevel.ON_CHANGE - inputs changed, output used or not.
		CookLevel.WHEN_USED - every frame when output is being used
		CookLevel.ALWAYS - every frame
	"""

	return CookLevel.WHEN_USED
