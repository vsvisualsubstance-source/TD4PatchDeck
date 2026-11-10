"""
All'apertura del progetto, dopo ~10 s (restore di Embody e init dell'APC40 gia'
conclusi): riallinea il warm pool alla memoria reale e, se il toggle
Preloadonstart del led_controller e' attivo, lancia il preload della Setlist.
"""

START_DELAY_SEC = 10


def onStart():
	run("me.parent().ext.PATCHDECKCTRLledcontroller1.prepareAfterStart()",
		fromOP=me, delayMilliSeconds=START_DELAY_SEC * 1000)
	return
