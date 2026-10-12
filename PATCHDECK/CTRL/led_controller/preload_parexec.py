"""
Pulsanti della pagina Preload del led_controller.
"""


def onPulse(par):
	if par.name == 'Preload':
		par.owner.ext.PATCHDECKCTRLledcontroller1.preloadSetlist()
	elif par.name == 'Stoppreload':
		par.owner.ext.PATCHDECKCTRLledcontroller1.stopPreload()
	return
