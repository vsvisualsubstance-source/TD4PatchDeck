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

def onCook(scriptOp: scriptCHOP):
	"""
	Called when the Script CHOP needs to cook.

	Emette ch1..ch48 (0/1): quali canali audio di Controller sono
	autorizzati in questo momento -- stessa fonte di verita' usata da
	PATCHDECKCTRLledcontroller1.py per pilotare i LED APC40 (Deck A/B +
	extra_active_patches), letta qui in sola lettura senza toccare
	quell'extension. Va sul touchoutCHOP verso Controller (porta 8010).
	"""
	scriptOp.clear()

	patchdeck = scriptOp.parent(2)
	status_table = patchdeck.op('UI/MAIN_INTERFACE/MIDI_status')
	led_controller = patchdeck.op('CTRL/led_controller')

	authorized = set()
	if status_table:
		authorized.add(str(status_table[1, 0].val or '0'))
		authorized.add(str(status_table[1, 1].val or '0'))
	if led_controller:
		extra_active = led_controller.fetch('extra_active_patches', [])
		authorized.update(str(n) for n in extra_active)
	authorized.discard('0')

	for patch_num in range(1, 49):
		chan = scriptOp.appendChan('ch%d' % patch_num)
		chan[0] = 1.0 if str(patch_num) in authorized else 0.0
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

	return CookLevel.AUTOMATIC
