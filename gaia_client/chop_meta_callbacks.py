"""
Script CHOP Callbacks

me - this DAT

scriptOp - the OP which is cooking
"""

from typing import Any

def onSetupParameters(scriptOp: scriptCHOP):
	return

def onPulse(par: Any):
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
	return CookLevel.WHEN_USED
