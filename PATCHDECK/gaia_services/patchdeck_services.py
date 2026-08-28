"""
PatchDeck Services -- registra i controlli PatchDeck (stop/start deck A/B,
caricamento patch) come servizi Gaia via gaia_device_agent.register_service().

Ported 2026-08-28 dal vecchio /PATCHDECK/gaia_device_agent/patchdeck_services.py
quando gaia_client ha sostituito gaia_agent/gaia_device_agent (ora ritirati,
Cooking flag off) come unico client Gaia attivo -- senza questa porta i 78
servizi (deck_a/deck_b + 38 patch x 2 deck) restavano vuoti in gaia_client,
lasciando PatchDeck incontrollabile via MQTT lato Gaia.

Eseguito da lifecycle.onCreate()/onStart(). Non tocca gaia_client/gaia_device_agent.py
(file condiviso/portabile, vedi il suo stesso docstring) ne' indexexec.py
(percorso dei pad fisici APC40, invariato) -- chiama solo i 3 metodi aggiunti
a led_controller (loadPatchToDeck/clearDeck/deckStatus), stessa fonte di
verita' (MIDI_status, extra_active) usata dai pad fisici.
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
	dat = op('/gaia_client/mqtt_device')
	if not dat or not dat.isConnected:
		print('[PatchDeck Services] mqtt_device non connesso, matrice non pubblicata')
		return False
	agent = op('/gaia_client/gaia_device_agent').module
	device_id = agent._read_config()['device_id']
	payload = _build_matrix()
	payload['device_id'] = device_id
	payload['ts'] = int(time.time() * 1000)
	dat.publish('gaia/devices/%s/patchdeck_matrix' % device_id, json.dumps(payload).encode('utf-8'), retain=True)
	print('[PatchDeck Services] Matrice pubblicata su gaia/devices/%s/patchdeck_matrix' % device_id)
	return True


def register_all():
	"""Idempotent for the REGISTRATION step only -- publish_matrix() always
	runs regardless, because the first call (from onCreate, early in the
	load sequence) usually lands before mqtt_device has connected and
	fails silently; onCreate/onStart/the 5s self-heal all call this, so
	gating the publish behind the same 'already registered' check meant
	it could permanently skip publishing after that one failed attempt."""
	agent = op('/gaia_client/gaia_device_agent').module
	if 'deck_a' not in agent._services:
		for deck in ('A', 'B'):
			_register_deck_services(agent, deck)
		for patch_num in range(1, 39):
			for deck in ('A', 'B'):
				_register_patch_service(agent, patch_num, deck)
		print('[PatchDeck Services] %d servizi registrati' % len(agent._services))
	publish_matrix()
