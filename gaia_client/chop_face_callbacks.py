"""
Script CHOP Callbacks

me - this DAT

scriptOp - the OP which is cooking
"""

from typing import Any
import re

def onSetupParameters(scriptOp: scriptCHOP):
	return

def onPulse(par: Any):
	return

CATEGORY = '/face/'
PERSON_BUDGET = 2   # '/face/{person}/{region}{idx}' -- person IS a clean
                    # segment here (unlike pose/hand), so we bound by person
                    # count instead of an arbitrary channel slice.

def onCook(scriptOp: scriptCHOP):
	"""
	Called when the Script CHOP needs to cook.

	Bounded pool over oscin_mocap's raw face-mesh-contour channels
	('/face/{person}/{region}{idx}', region in eye_left/eye_right/
	eyebrow_left/eyebrow_right/lips/nose/oval). Keeps the first
	PERSON_BUDGET person ids (sorted) in full; drops the rest. This bounds
	output size regardless of how many stale person ids accumulate in
	oscin_mocap over a session (no automatic expiry there).
	"""
	scriptOp.clear()
	src = op('oscin_mocap')
	if src is None:
		return

	# region -> {numeric_idx -> full_channel_name}. Sorting the remainder as
	# a STRING scrambles contour order (e.g. 'eye_left11' < 'eye_left2') --
	# split the trailing digits out and sort numerically so consecutive
	# output values trace the actual contour in order.
	by_person = {}
	name_re = re.compile(r'([a-zA-Z_]+)(\d+)$')
	for c in src.chans():
		if CATEGORY not in c.name:
			continue
		seg = c.name.split(CATEGORY, 1)[1]
		parts = seg.split('/', 1)
		if len(parts) != 2:
			continue
		person, rest = parts
		m = name_re.match(rest)
		if not m:
			continue
		region, idx = m.group(1), int(m.group(2))
		by_person.setdefault(person, {}).setdefault(region, {})[idx] = c.name

	scriptOp.numSamples = 1
	i = 0
	for person in sorted(by_person)[:PERSON_BUDGET]:
		regions = by_person[person]
		for region in sorted(regions):
			for idx in sorted(regions[region]):
				chan = scriptOp.appendChan('f%d' % i)
				chan[0] = src[regions[region][idx]].eval()
				i += 1
	return

def onGetCookLevel(scriptOp: scriptCHOP) -> CookLevel:
	return CookLevel.WHEN_USED
