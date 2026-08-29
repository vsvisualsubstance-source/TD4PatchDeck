"""
Execute DAT -- registra i servizi PatchDeck (deck A/B, patch load) su
gaia_client, il client Gaia attivo dopo il ritiro di gaia_agent/
gaia_device_agent (2026-08-28, Cooking flag off). Vedi patchdeck_services.py
per i dettagli e la storia del porting.

Il self-heal vero e proprio (retry quando il registro e' vuoto) ora vive
generico dentro gaia_device_agent.py (_self_check(), GAIA_INTERFACE.md
sezione 2, 2026-08-29) -- questo file si limita ad ARMARE quel meccanismo
con register_project_registrar(), ripetuto ogni pochi secondi perche' un
hot-reload di gaia_device_agent.py da solo (file diverso, non questo)
azzera quel puntatore senza toccare questa DAT.
"""

import time

_last_registrar_check = 0.0
_REGISTRAR_CHECK_INTERVAL_S = 5.0


def _ensure_registrar():
	"""Ri-arma il puntatore registrar su gaia_device_agent se un suo
	hot-reload indipendente lo ha azzerato. Non duplica la logica di
	retry -- quella e' generica in _self_check(), qui c'e' solo il
	ri-aggancio del puntatore."""
	global _last_registrar_check
	now = time.time()
	if (now - _last_registrar_check) < _REGISTRAR_CHECK_INTERVAL_S:
		return
	_last_registrar_check = now
	agent_dat = op.Gaia.op('gaia_device_agent')
	services_dat = op('patchdeck_services')
	if agent_dat is None or services_dat is None:
		return
	if agent_dat.module._registrar is None:
		agent_dat.module.register_project_registrar(services_dat.module.register_all)


def onStart():
	"""
	Called when the project starts.
	"""
	op.Gaia.op('gaia_device_agent').module.register_project_registrar(op('patchdeck_services').module.register_all)
	op('patchdeck_services').module.register_all()
	return

def onCreate():
	"""
	Called when the DAT is created.
	"""
	op.Gaia.op('gaia_device_agent').module.register_project_registrar(op('patchdeck_services').module.register_all)
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
	_ensure_registrar()
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
