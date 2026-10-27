def onFrameStart(frame):



	if parent(2).digits == op('/PATCHDECK/UI/MAIN_INTERFACE/MIDI_status')[1,0]:					
		op('index')[0,0] = 1

	else:
		op('index')[0,0] = 0
		
	if parent(2).digits == op('/PATCHDECK/UI/MAIN_INTERFACE/MIDI_status')[1,1]:					
		op('index')[0,0] = 2
	
	
	return

