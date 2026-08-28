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

CATEGORY = '/hand/'
BUDGET = 200

def onCook(scriptOp: scriptCHOP):
	"""
	Called when the Script CHOP needs to cook.

	Bounded pool over oscin_mocap's raw hand (left+right) channels -- same
	deterministic size-capped-slice approach as chop_pose (see its comment).
	"""
	scriptOp.clear()
	src = op('oscin_mocap')
	if src is None:
		return

	names = sorted(c.name for c in src.chans() if CATEGORY in c.name)[:BUDGET]
	scriptOp.numSamples = 1
	for i, name in enumerate(names):
		chan = scriptOp.appendChan('h%d' % i)
		chan[0] = src[name].eval()
	return

def onGetCookLevel(scriptOp: scriptCHOP) -> CookLevel:
	return CookLevel.WHEN_USED
