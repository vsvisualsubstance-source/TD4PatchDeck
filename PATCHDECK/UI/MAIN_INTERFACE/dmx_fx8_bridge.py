
# ------------------------------------------------
# Parameter Execute DAT - ponte tra il knob fisico
# APC40 "Master FX 8" (ex-Strobo) e dmx_audio_chase.
# Ora a TRE stati, tutti sullo stesso knob fisico:
#   nessuno shift  -> knob originale, pilota black_level
#                      via MASTERFX -> hold_fx8_strobo -> fx8
#   shift1 (ch1n83, Scene Launch 1) -> Dimmerboost (DMX Intensity)
#   shift2 (ch1n84, Scene Launch 2) -> Videomix (DMX Video Mix)
# Entrambe le note verificate davvero libere con diff empirico
# dei canali midiin1 (nessun riferimento nel progetto ne' nel
# device profile) -- vedi memoria patchdeck-known-issues, a
# differenza del primo tentativo con nota 51/Track Select 1,
# che in realta' inviava la nota 33 gia' usata da B2.
#
# hold_fx8_strobo (in POST_FX) congela black_level ogni volta
# che ch1n83 O ch1n84 e' premuto (combine_shift, Combine CHOPs
# = Maximum), cosi' i tre controlli non si toccano mai a vicenda.
#
# control_ui.par.Fx8 e' il landing pad esistente per
# il valore hardware del knob (0-1, aggiornato dal
# resto della pipeline MIDI gia' presente in CTRL,
# non toccata da questo script).
# - Con shift1: rimappato su 0.1-3.0 (range di Dimmerboost).
#   Lo slider UI "dmx_intensity" resta BIND-ato allo stesso
#   Dimmerboost, quindi restano sincronizzati in entrambe le
#   direzioni.
# - Con shift2: scritto diretto su Videomix (gia' 0-1, nessun
#   remap). Lo slider UI "dmx_video_mix" resta BIND-ato.
# ------------------------------------------------

def onValueChange(par, prev):
	if par.name != 'Fx8':
		return

	midi = me.op('../../../CTRL/midiin1')
	if midi is None:
		return

	dmx = me.op('../../../DMX/dmx_audio_chase')
	if dmx is None:
		return

	raw = max(0.0, min(1.0, float(par.eval())))

	shift1_held = midi['ch1n83'][0] > 0.5
	shift2_held = midi['ch1n84'][0] > 0.5

	if shift1_held:
		mapped = 0.1 + raw * (3.0 - 0.1)
		dmx.par.Dimmerboost = mapped
	elif shift2_held:
		dmx.par.Videomix = raw
	return

def onPulse(par):
	return

def onExpressionChange(par, val, prev):
	return

def onExportChange(par, val, prev):
	return

def onEnableChange(par, val, prev):
	return

def onModeChange(par, val, prev):
	return
