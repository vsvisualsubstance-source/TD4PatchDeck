"""
Script DAT Callbacks

me - this DAT

scriptOp - the OP which is cooking
"""

import json

# press 'Setup Parameters' in the OP to call this function to re-create the
# parameters.
def onSetupParameters(scriptOp: scriptDAT):
	"""
	Called to setup custom parameters for the Script DAT.
	"""
	page = scriptOp.appendCustomPage('Custom')
	p = page.appendFloat('Valuea', label='Value A')
	p = page.appendFloat('Valueb', label='Value B')
	return

def onPulse(par: Par):
	"""
	Called when a custom pulse parameter is pushed.
	
	Args:
		par: The parameter that was pulsed
	"""
	return

def onCook(scriptOp: scriptDAT):
	"""
	Called when the Script DAT needs to cook.
	"""
	scriptOp.clear()
	scriptOp.appendRow(['word', 'count'])

	src = op('topic_canvas')
	try:
		obj = json.loads(src.text) if src is not None else {}
	except (ValueError, AttributeError):
		obj = {}

	lexicon = obj.get('lexicon') or {}
	items = sorted(
		lexicon.items(),
		key=lambda kv: (kv[1] or {}).get('count', 0),
		reverse=True,
	)[:20]
	for word, info in items:
		scriptOp.appendRow([word, str((info or {}).get('count', 0))])
	return

def onGetCookLevel(scriptOp: scriptDAT) -> CookLevel:
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
