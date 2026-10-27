"""
Execute DAT

me - this DAT

Make sure the corresponding toggle is enabled in the Execute DAT.
"""

def onStart():
    init_dat = op('/PATCHDECK/CTRL/init_apc40')  # il tuo Text DAT
    if init_dat:
        init_dat.run()
        print("[INIT] APC40 inizializzato all'avvio progetto")
    else:
        print("[INIT] ❌ init_apc40 DAT non trovato")


def onCreate():
	"""
	Called when the DAT is created.
	"""
	return

def onExit():
	"""
	Called when the project exits.
	"""
	return

def onFrameStart(frame: int):
	"""
	Called at the start of each frame.
	
	Args:
		frame: The current frame number
	"""
	return

def onFrameEnd(frame: int):
	"""
	Called at the end of each frame.
	
	Args:
		frame: The current frame number
	"""
	return

def onPlayStateChange(state: bool):
	"""
	Called when the play state changes.
	
	Args:
		state: False if the timeline was just paused
	"""
	return

def onDeviceChange():
	"""
	Called when a device change occurs.
	"""
	return

def onProjectPreSave():
	"""
	Called before the project is saved.
	"""
	return

def onProjectPostSave():
	"""
	Called after the project is saved.
	"""
	return
