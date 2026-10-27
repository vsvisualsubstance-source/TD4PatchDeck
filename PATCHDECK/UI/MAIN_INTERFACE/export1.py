ctrl = op("previews")

# null1's channel names don't all match previews' custom-parameter names
# (case mismatch: MIDI-derived channels are 'KillA'/'KillB', but this
# project's custom-parameter naming convention forces 'Killa'/'Killb' --
# see parameters.md). Assigning a channel to a Par that doesn't exist under
# that exact name raises tdError("Can only assign parameter objects...").
# Tried fixing it at the source via null1's Rename From/To, but that CHOP
# parameter was verified NOT to take effect in this TD build (isolated
# test on a throwaway nullCHOP confirmed no rename happens regardless of
# settings) -- so the mapping is done here instead, right before lookup.
_NAME_FIX = {'KillA': 'Killa', 'KillB': 'Killb'}

def onValueChange(channel, sampleIndex, val, prev):
	name = _NAME_FIX.get(channel.name, channel.name)
	par = ctrl.par[name]
	if par is None:
		return
	ctrl.par[name] = channel
	return
	