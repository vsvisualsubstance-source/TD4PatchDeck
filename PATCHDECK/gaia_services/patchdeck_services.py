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

Aggiunti 2026-08-31: i primi 5 knob POST_FX di control_ui (EDGE, FEEDBACK,
FB SCALE, FB BLUR, MIRROR -- le prime 5 colonne di
PATCHDECK/PATCHES/POST_FX/fx_lables.tsv, custom par Fx1..Fx5 su
control_ui) esposti come Gaia continuous param via
gaia_device_agent.register_param() (stesso 'action:set' via MQTT gia'
usato per gli altri controlli di questo device -- vedi i servizi deck_a/
deck_b sopra), cosi' TD4Gaia puo' pilotarli allo stesso modo dei deck.
FX6/FX7/FX8 (BRIGHTNESS/BLACK LVL/Strobo) restano fuori, non richiesti.
"""

import json
import time

_last_patch = {'A': 0, 'B': 0}  # memoria locale per il resume di start_deck_a/b


def _led():
	return op('/PATCHDECK/CTRL/led_controller').ext.PATCHDECKCTRLledcontroller1


def _ctrl():
	return op('/PATCHDECK/UI/MAIN_INTERFACE/control_ui')


# name esposto via MQTT -> custom par su control_ui (Fx1..Fx5, vedi
# PATCHDECK/PATCHES/POST_FX/fx_lables.tsv per la mappa completa FX1..FX8)
_FX_PARAMS = [
	('edge', 'Fx1'),
	('feedback', 'Fx2'),
	('fb_scale', 'Fx3'),
	('fb_blur', 'Fx4'),
	('mirror', 'Fx5'),
]


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


def _register_fx_params(agent):
	"""Espone i primi 5 knob POST_FX di control_ui come Gaia continuous
	param (get/set su Fx1..Fx5, 0..1 float -- vedi _FX_PARAMS)."""
	for name, par_name in _FX_PARAMS:
		def get(par_name=par_name):
			return float(_ctrl().par[par_name].eval())

		def set_(value, par_name=par_name):
			_ctrl().par[par_name] = float(value)

		agent.register_param(name, get=get, set=set_)


def _build_matrix():
	"""Struttura meccanica dei 78 servizi (quali sono deck toggle, quali
	load_x{N}_{deck}) -- NON descrizioni creative delle patch, solo la
	matrice pulsanti cosi' chi costruisce l'interfaccia lato Gaia non
	deve fare parsing dei nomi servizio. Stesso principio per fx_params
	(nome MQTT -> label originale + range), cosi' TD4Gaia puo' disegnare
	gli slider senza indovinare la mappa Fx1..Fx5 -> EDGE..MIRROR."""
	services = {
		'deck_a': {'kind': 'deck_toggle', 'deck': 'A'},
		'deck_b': {'kind': 'deck_toggle', 'deck': 'B'},
	}
	for patch_num in range(1, 39):
		for deck in ('A', 'B'):
			name = 'load_x%d_%s' % (patch_num, deck.lower())
			services[name] = {'kind': 'load_patch', 'patch': patch_num, 'deck': deck}
	fx_labels = {'edge': 'EDGE', 'feedback': 'FEEDBACK', 'fb_scale': 'FB SCALE',
		'fb_blur': 'FB BLUR', 'mirror': 'MIRROR'}
	fx_params = {name: {'label': fx_labels[name], 'min': 0.0, 'max': 1.0}
		for name, _ in _FX_PARAMS}
	return {
		'decks': ['A', 'B'],
		'patches': list(range(1, 39)),
		'services': services,
		'fx_params': fx_params,
	}


def publish_matrix():
	"""Pubblica la matrice servizi su MQTT, retained -- sopravvive a
	riconnessioni del device, resta sul broker finche' non viene
	sovrascritta da una futura repubblica.

	Nome del topic costruito dal parametro custom Family su /gaia_client
	(gaia/devices/{id}/{family}_matrix -- GAIA_INTERFACE.md sezione 1b
	"Gaia Agent Universale", 2026-08-29): oggi Family='patchdeck' quindi
	il nome coincide con il vecchio hardcoded 'patchdeck_matrix', ma il
	nome ora e' dichiarato dal parametro invece che scelto a mano qui."""
	dat = op('/gaia_client/mqtt_device')
	if not dat or not dat.isConnected:
		print('[PatchDeck Services] mqtt_device non connesso, matrice non pubblicata')
		return False
	agent = op('/gaia_client/gaia_device_agent').module
	cfg = agent._read_config()
	device_id = cfg['device_id']
	family = cfg['family']
	if not family:
		print('[PatchDeck Services] Family non impostato su /gaia_client, matrice non pubblicata')
		return False
	payload = _build_matrix()
	payload['device_id'] = device_id
	payload['ts'] = int(time.time() * 1000)
	topic = 'gaia/devices/%s/%s_matrix' % (device_id, family)
	dat.publish(topic, json.dumps(payload).encode('utf-8'), retain=True)
	print('[PatchDeck Services] Matrice pubblicata su %s' % topic)
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
	if 'edge' not in agent._params:
		_register_fx_params(agent)
		print('[PatchDeck Services] %d param FX registrati' % len(agent._params))
	publish_matrix()
