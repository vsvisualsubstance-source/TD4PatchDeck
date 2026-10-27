def onProjectPreSave():
	op('MIDI_status')[1,0] = 0
	op('MIDI_status')[1,1] = 0
	return
