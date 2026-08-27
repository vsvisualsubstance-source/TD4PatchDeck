"""
Execute DAT

me - this DAT

Make sure the corresponding toggle is enabled in the Execute DAT.
"""

import time

_last_registry_check = 0.0
_REGISTRY_CHECK_INTERVAL_S = 5.0


def _ensure_services_registered():
	"""Self-heal: re-register PatchDeck services if gaia_device_agent's
	module-level _services dict was wiped by a hot-reload of its DAT
	content (syncfile reload re-executes the module, resetting state)
	with no onStart/onCreate to repopulate it afterward."""
	global _last_registry_check
	now = time.time()
	if (now - _last_registry_check) < _REGISTRY_CHECK_INTERVAL_S:
		return
	_last_registry_check = now
	agent_dat = op('gaia_device_agent')
	services_dat = op('patchdeck_services')
	if agent_dat is None or services_dat is None:
		return
	if not agent_dat.module._services:
		services_dat.module.register_all()


def onStart():
	"""
	Called when the project starts.
	"""
	op('patchdeck_services').module.register_all()
	return

def onCreate():
	"""
	Called when the DAT is created.
	"""
	op('patchdeck_services').module.register_all()
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
	op('gaia_device_agent').module.tick()
	op('gaia_device_agent').module.perf_tick()
	_ensure_services_registered()
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
