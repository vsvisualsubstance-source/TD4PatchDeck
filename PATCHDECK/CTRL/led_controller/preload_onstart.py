"""
Preload On Start: all'apertura del progetto, se il toggle Preloadonstart del
led_controller e' attivo, lancia il preload della Setlist dopo ~10 s, cosi'
il restore di Embody e l'init dell'APC40 sono gia' conclusi.
"""

START_DELAY_SEC = 10


def onStart():
	if parent().par.Preloadonstart.eval():
		run("me.parent().ext.PATCHDECKCTRLledcontroller1.preloadSetlist()",
			fromOP=me, delayMilliSeconds=START_DELAY_SEC * 1000)
	return
