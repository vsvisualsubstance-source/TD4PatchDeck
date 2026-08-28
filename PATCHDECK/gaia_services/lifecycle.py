"""
Execute DAT -- registra i servizi PatchDeck (deck A/B, patch load) su
gaia_client, il client Gaia attivo dopo il ritiro di gaia_agent/
gaia_device_agent (2026-08-28, Cooking flag off). Vedi patchdeck_services.py
per i dettagli e la storia del porting.
"""

import time

_last_registry_check = 0.0
_REGISTRY_CHECK_INTERVAL_S = 5.0


def _ensure_services_registered():
	"""Self-heal: ri-registra se gaia_client/gaia_device_agent._services e'
	stato svuotato da un hot-reload del suo DAT (syncfile reload
	ri-esegue il modulo, azzerando lo stato) senza un onStart/onCreate
	che lo ripopoli dopo."""
	global _last_registry_check
	now = time.time()
	if (now - _last_registry_check) < _REGISTRY_CHECK_INTERVAL_S:
		return
	_last_registry_check = now
	agent_dat = op('/gaia_client/gaia_device_agent')
	services_dat = op('patchdeck_services')
	if agent_dat is None or services_dat is None:
		return
	if 'deck_a' not in agent_dat.module._services:
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
	"""
	_ensure_services_registered()
	return

def onFrameEnd(frame: int):
	"""
	Called at the end of each frame.
	"""
	return

def onPlayStateChange(state: bool):
	"""
	Called when the play state changes.
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
