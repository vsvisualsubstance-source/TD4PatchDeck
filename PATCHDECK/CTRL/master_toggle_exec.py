# Akai "Master" button (MIDI ch1 note 81) -> toggles Direct NDI Mode on
# /PATCHDECK/PATCHES/POST_FX. Edge-triggered on Off->On so it works whether
# the pad sends a momentary press or a latching on/off.

def onOffToOn(channel, sampleIndex, val, prev):
	post_fx = op('/PATCHDECK/PATCHES/POST_FX')
	if post_fx is None:
		return

	post_fx.par.Directndimode = not post_fx.par.Directndimode.eval()
	return
