"""
DMX Services -- project-specific registrar for gaia_dmx_client (an
independent, minimal Gaia Agent Universale instance dedicated ONLY to
PatchDeck's internal DMX rig). Registers the real controls of
/PATCHDECK/DMX/dmx_audio_chase as Gaia services/params on THIS device's own
identity (Deviceid/Family set on /gaia_dmx_client, distinct from PatchDeck's
own gaia_client device), and publishes the control matrix.

Schema mirrors the standalone DMX V8 project's gaia_client/dmx_services.py
verbatim (same param names, same 'rigs' matrix shape, same kind/type/range
JSON) so a Gaia-side DMX consumer built against that project parses this
device identically. Only two differences: a single rig ('a' ->
dmx_audio_chase, PatchDeck has no _b rig) and _rig() resolves into
/PATCHDECK/DMX/ instead of a sibling of gaia_client (the DMX component here
lives inside the PatchDeck project tree, not beside this agent).

gaia_device_agent (the portable core, identical to gaia_client's) never
calls project code directly by design -- this file is the project-specific
glue and lives ONLY here, wired via dmx_services_lifecycle.py.
"""
import json
import time

RIGS = [
	('a', 'dmx_audio_chase'),
]

FLOAT_PARAMS = [
	('dmx_min_dimmer', 'Mindimmer'),
	('dmx_max_dimmer', 'Maxdimmer'),
	('dmx_dimmer_boost', 'Dimmerboost'),
	('dmx_dimmer_gamma', 'Dimmergamma'),
	('dmx_smooth_factor', 'Smoothfactor'),
	('dmx_color_curve', 'Colorcurve'),
	('dmx_color_fade', 'Colorsmooth'),
	('dmx_color_speed', 'Colorspeed'),
	('dmx_color_phase', 'Colorphase'),
	('dmx_bar_phase', 'Barphase'),
	('dmx_global_smooth', 'Globalsmooth'),
	('dmx_agc_release', 'Agcrelease'),
	('dmx_min_range', 'Minrange'),
	('dmx_kick_threshold', 'Kickthresh'),
	('dmx_kick_boost', 'Kickboost'),
	('dmx_kick_decay', 'Kickdecay'),
	('dmx_kick_cooldown', 'Kickcooldown'),
	('dmx_kick_smooth', 'Kicksmooth'),
]

INT_PARAMS = [
	('dmx_fixture_count', 'Nbars'),
	('dmx_start_address', 'Startaddress'),
]

MENU_PARAMS = [
	('dmx_palette', 'Palette'),
	('dmx_fixture_profile', 'Fixtureprofile'),
]

COLOR_PARAMS = [
	('dmx_custom_color1', 'Custompalette1'),
	('dmx_custom_color2', 'Custompalette2'),
	('dmx_custom_color3', 'Custompalette3'),
	('dmx_custom_color4', 'Custompalette4'),
	('dmx_custom_color5', 'Custompalette5'),
]

SERVICES = [
	('dmx_kick_enable', 'bool'),
	('dmx_use_file_input', 'bool'),
	('dmx_apply_fixture_profile', 'action'),
]


def _rig(rig_name):
	# gaia_dmx_client is /gaia_dmx_client, this DAT's parent -- the DMX rig
	# lives inside PatchDeck's own tree, not beside this agent.
	return me.parent().parent().op('PATCHDECK/DMX/' + rig_name)


def _register_value(agent, name, rig_name, par_name, cast):
	def get():
		return cast(_rig(rig_name).par[par_name].eval())

	def set_(value):
		_rig(rig_name).par[par_name] = cast(value)

	agent.register_param(name, get=get, set=set_)


def _register_menu(agent, name, rig_name, par_name):
	def get():
		return str(_rig(rig_name).par[par_name].eval())

	def set_(value):
		par = _rig(rig_name).par[par_name]
		names = list(par.menuNames)
		if isinstance(value, str) and value in names:
			par.val = value
			return
		# some generic UI enums send the selected INDEX instead of the label
		try:
			idx = int(value)
		except (TypeError, ValueError):
			idx = None
		if idx is not None and 0 <= idx < len(names):
			par.val = names[idx]
			return
		raise ValueError('%s: invalid value %r (options: %s)' % (
			par_name, value, ', '.join(names)))

	agent.register_param(name, get=get, set=set_)


def _register_color(agent, name, rig_name, base_par):
	def get():
		rig = _rig(rig_name)
		return [
			float(rig.par[base_par + 'r'].eval()),
			float(rig.par[base_par + 'g'].eval()),
			float(rig.par[base_par + 'b'].eval()),
		]

	def set_(value):
		rig = _rig(rig_name)
		r, g, b = value
		rig.par[base_par + 'r'] = float(r)
		rig.par[base_par + 'g'] = float(g)
		rig.par[base_par + 'b'] = float(b)

	agent.register_param(name, get=get, set=set_)


def _numeric_range(par):
	"""Real control range -- clamp if set, otherwise the slider range
	(normMin/normMax), never a made-up value."""
	lo = par.min if par.clampMin else par.normMin
	hi = par.max if par.clampMax else par.normMax
	return [round(float(lo), 6), round(float(hi), 6)]


def _build_matrix_for_rig(rig_name):
	rig = _rig(rig_name)
	params = {}

	for name, par_name in FLOAT_PARAMS:
		par = rig.par[par_name]
		params[name] = {
			'kind': 'param',
			'type': 'float',
			'range': _numeric_range(par),
			'default': float(par.default),
		}

	for name, par_name in INT_PARAMS:
		par = rig.par[par_name]
		params[name] = {
			'kind': 'param',
			'type': 'int',
			'range': _numeric_range(par),
			'default': int(par.default),
		}

	for name, par_name in MENU_PARAMS:
		par = rig.par[par_name]
		params[name] = {
			'kind': 'param',
			'type': 'enum',
			'options': list(par.menuNames),
			'default': str(par.default),
		}

	for name, base_par in COLOR_PARAMS:
		params[name] = {
			'kind': 'param',
			'type': 'color_rgb',
			'range': [0.0, 1.0],
		}

	services = {name: {'kind': 'service', 'type': kind} for name, kind in SERVICES}

	return {'params': params, 'services': services}


def publish_matrix():
	"""Publishes the combined per-rig matrix on MQTT, retained -- survives
	device reconnects, stays on the broker until overwritten by a future
	republish."""
	dat = op('mqtt_device')
	if not dat or not dat.isConnected:
		print('[DMX Services] mqtt_device not connected, matrix not published')
		return False
	cfg_op = me.parent()
	device_id = cfg_op.par.Deviceid.eval() if cfg_op else 'unknown'
	family = (cfg_op.par.Family.eval() if cfg_op else '') or 'dmx'
	payload = {
		'device_id': device_id,
		'rigs': {letter: _build_matrix_for_rig(rig_name) for letter, rig_name in RIGS},
		'ts': int(time.time() * 1000),
	}
	topic = 'gaia/devices/%s/%s_matrix' % (device_id, family.lower())
	dat.publish(topic, json.dumps(payload).encode('utf-8'), retain=True)
	print('[DMX Services] Matrix published to %s' % topic)
	return True


def register_all():
	agent = op('gaia_device_agent').module

	for letter, rig_name in RIGS:
		prefix = 'dmx_%s_' % letter

		for name, par_name in FLOAT_PARAMS:
			_register_value(agent, prefix + name[4:], rig_name, par_name, float)
		for name, par_name in INT_PARAMS:
			_register_value(agent, prefix + name[4:], rig_name, par_name, int)
		for name, par_name in MENU_PARAMS:
			_register_menu(agent, prefix + name[4:], rig_name, par_name)
		for name, base_par in COLOR_PARAMS:
			_register_color(agent, prefix + name[4:], rig_name, base_par)

		agent.register_service(
			prefix + 'kick_enable',
			start=lambda rn=rig_name: setattr(_rig(rn).par, 'Kickenable', 1),
			stop=lambda rn=rig_name: setattr(_rig(rn).par, 'Kickenable', 0),
			status=lambda rn=rig_name: bool(_rig(rn).par.Kickenable.eval()))

		agent.register_service(
			prefix + 'use_file_input',
			start=lambda rn=rig_name: setattr(_rig(rn).par, 'Usefileinput', 1),
			stop=lambda rn=rig_name: setattr(_rig(rn).par, 'Usefileinput', 0),
			status=lambda rn=rig_name: bool(_rig(rn).par.Usefileinput.eval()))

		agent.register_service(
			prefix + 'apply_fixture_profile',
			start=lambda rn=rig_name: _rig(rn).par.Applyfixture.pulse())

	print('[DMX Services] %d services/params registered' % (
		len(agent._services) + len(agent._params)))

	publish_matrix()
