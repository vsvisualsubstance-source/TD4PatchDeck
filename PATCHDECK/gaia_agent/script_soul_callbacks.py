"""
Script CHOP Callbacks

me - this DAT

scriptOp - the OP which is cooking
"""

from typing import Any
import json

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

def onCook(scriptOp: scriptCHOP):
	"""
	Called when the Script CHOP needs to cook.
	"""
	scriptOp.clear()

	dat = op('topic_canvas')
	try:
		soul = json.loads(dat.text).get('soul', {}) if dat is not None else {}
	except (ValueError, AttributeError):
		soul = {}

	mood_rgb = soul.get('mood_rgb') or {}
	values = {
		'mood_r': (mood_rgb.get('r') or 0) / 255.0,
		'mood_g': (mood_rgb.get('g') or 0) / 255.0,
		'mood_b': (mood_rgb.get('b') or 0) / 255.0,
		'stress': soul.get('stress') or 0,
		'calm': soul.get('calm') or 0,
		'social': soul.get('social') or 0,
		'curiosity': soul.get('curiosity') or 0,
		'energy': (soul.get('energy') or 0) / 100.0,
		'lifeindex': (soul.get('lifeIndex') or 0) / 100.0,
	}

	scriptOp.numSamples = 1
	for name, value in values.items():
		chan = scriptOp.appendChan(name)
		chan[0] = value
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
