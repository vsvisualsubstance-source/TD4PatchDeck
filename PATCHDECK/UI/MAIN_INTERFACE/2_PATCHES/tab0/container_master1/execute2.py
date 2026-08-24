def onFrameEnd(frame):

	if op('../../../MIDI_status')[1,0] == parent(1).digits:
		op('ab')[0,0] = ' A'
		op('a_active').par.opacity = 1
		


	if op('../../../MIDI_status')[1,1] == parent(1).digits:
		op('ab')[0,0] = ' B'
		op('b_active').par.opacity = 1
	
	if op('../../../MIDI_status')[1,0] != parent(1).digits and op('../../../MIDI_status')[1,1] != parent(1).digits:
		op('ab')[0,0] = ''
		op('a_active').par.opacity = 0
		op('b_active').par.opacity = 0