"""
Audio VST CHOP Callbacks

me - this DAT
"""

def onReceiveMidi(chop: audiovstCHOP, channel: int, byteData: bytes, 
				  timestamp: float):
	"""
	Called when MIDI data is received by the Audio VST CHOP.
	
	Args:
		chop: The Audio VST CHOP
		channel: The MIDI channel
		byteData: The MIDI bytes
		timestamp: The timestamp of the MIDI event (plugin-specific units,
			typically sample number)
	"""
	return
