"""
PatchDeck Services -- registra i controlli PatchDeck (stop/start deck A/B,
caricamento patch) come servizi Gaia via gaia_device_agent.register_service().

Eseguito UNA VOLTA da agent_lifecycle.onCreate(). Non tocca
gaia_device_agent.py (file condiviso su tutta la flotta Gaia) ne'
indexexec.py (percorso dei pad fisici APC40, invariato) -- chiama solo i
3 metodi aggiunti a led_controller (loadPatchToDeck/clearDeck/deckStatus),
stessa fonte di verita' (MIDI_status, extra_active) usata dai pad fisici.
"""

import json
import time

_last_patch = {'A': 0, 'B': 0}  # memoria locale per il resume di start_deck_a/b


def _led():
	return op('/PATCHDECK/CTRL/led_controller').ext.PATCHDECKCTRLledcontroller1


def _register_deck_services(agent, deck):
	def stop():
		cleared = _led().clearDeck(deck)
		if cleared:
			_last_patch[deck] = cleared

	def start():
		p = _last_patch.get(deck, 0)
		if p:
			_led().loadPatchToDeck(p, deck)

	def status():
		return _led().deckStatus(deck) != 0

	agent.register_service('deck_%s' % deck.lower(), start=start, stop=stop, status=status)


def _register_patch_service(agent, patch_num, deck):
	def start():
		_led().loadPatchToDeck(patch_num, deck)

	def status():
		return _led().deckStatus(deck) == patch_num

	agent.register_service('load_x%d_%s' % (patch_num, deck.lower()), start=start, stop=None, status=status)


def _build_matrix():
	"""Struttura meccanica dei 78 servizi (quali sono deck toggle, quali
	load_x{N}_{deck}) -- NON descrizioni creative delle patch, solo la
	matrice pulsanti cosi' chi costruisce l'interfaccia lato Gaia non
	deve fare parsing dei nomi servizio."""
	services = {
		'deck_a': {'kind': 'deck_toggle', 'deck': 'A'},
		'deck_b': {'kind': 'deck_toggle', 'deck': 'B'},
	}
	for patch_num in range(1, 39):
		for deck in ('A', 'B'):
			name = 'load_x%d_%s' % (patch_num, deck.lower())
			services[name] = {'kind': 'load_patch', 'patch': patch_num, 'deck': deck}
	return {
		'decks': ['A', 'B'],
		'patches': list(range(1, 39)),
		'services': services,
	}


def publish_matrix():
	"""Pubblica la matrice servizi su MQTT, retained -- sopravvive a
	riconnessioni del device, resta sul broker finche' non viene
	sovrascritta da una futura repubblica."""
	dat = op('/PATCHDECK/gaia_device_agent/mqtt_agent')
	if not dat or not dat.isConnected:
		print('[PatchDeck Services] mqtt_agent non connesso, matrice non pubblicata')
		return False
	cfg_op = op('/PATCHDECK/gaia_device_agent')
	device_id = cfg_op.par.Deviceid.eval() if cfg_op else 'unknown'
	payload = _build_matrix()
	payload['device_id'] = device_id
	payload['ts'] = int(time.time() * 1000)
	dat.publish('gaia/devices/%s/patchdeck_matrix' % device_id, json.dumps(payload).encode('utf-8'), retain=True)
	print('[PatchDeck Services] Matrice pubblicata su gaia/devices/%s/patchdeck_matrix' % device_id)
	return True


def register_all():
	agent = op('/PATCHDECK/gaia_device_agent/gaia_device_agent').module
	for deck in ('A', 'B'):
		_register_deck_services(agent, deck)
	for patch_num in range(1, 39):
		for deck in ('A', 'B'):
			_register_patch_service(agent, patch_num, deck)
	print('[PatchDeck Services] %d servizi registrati' % len(agent._services))
	publish_matrix()
