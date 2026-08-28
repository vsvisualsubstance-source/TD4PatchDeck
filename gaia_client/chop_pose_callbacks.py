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

CATEGORY = '/pose/'
BUDGET = 200

def onCook(scriptOp: scriptCHOP):
	"""
	Called when the Script CHOP needs to cook.

	Pose OSC addresses use an unstable, non-contiguous, mixed-zero-padding
	flat index -- NOT a clean per-landmark/per-person scheme -- so this does
	not attempt semantic decoding. It just takes a deterministic, size-capped
	slice (sorted by name) so downstream cost never grows with oscin_mocap's
	own unbounded channel count.
	"""
	scriptOp.clear()
	src = op('oscin_mocap')
	if src is None:
		return

	names = sorted(c.name for c in src.chans() if CATEGORY in c.name)[:BUDGET]
	scriptOp.numSamples = 1
	for i, name in enumerate(names):
		chan = scriptOp.appendChan('p%d' % i)
		chan[0] = src[name].eval()
	return

def onGetCookLevel(scriptOp: scriptCHOP) -> CookLevel:
	return CookLevel.WHEN_USED
