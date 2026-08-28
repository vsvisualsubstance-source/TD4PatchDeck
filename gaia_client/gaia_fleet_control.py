"""
GAIA Fleet Control -- play/stop/restart of EVERY Gaia device's services,
natively from inside TouchDesigner. Same role as Pi Manager in Gaia's own
web admin, same MQTT protocol, but here TD is the CONTROLLER: it listens to
every device's status (gaia/device/+/status) and can send enable/disable/
restart commands to any of them.

Complementary to gaia_device_agent (which instead makes THIS TD instance
show up as one controllable device) -- the two modules coexist in the same
component without conflict.

Uses TD's native mqttclientDAT (see gaia_device_agent.py's docstring for
why -- no paho, no thread-safety machinery, the mqttclientDAT operator IS
the client).

USING IT FROM YOUR OWN UI
    op('gaia_client/gaia_fleet_control').module.get_devices()
        -> dict device_id -> last status payload (+ "_last_seen")
    op('gaia_client/gaia_fleet_control').module.send_command(
        device_id, service_name, 'enable')   # or 'disable' / 'restart'
send_command() is safe to call directly from a UI callback (already on TD's
main thread). devices_table (a sibling Table DAT) holds one row per
device+service pair (device_id, name, stanza, role, service, state,
offline) -- bind a List COMP to it directly for a live device browser; no
UI is bundled here since that's a per-project visual choice.

STATES: "active" / "inactive" / "failed" -- the exact values published by
Pi/OPS/local agents, no translation. offline=True if a device hasn't sent
status in more than OFFLINE_AFTER_S seconds.

Services > Device Fleet Control (on this component) gates whether incoming
status is stored/tabulated and whether the staleness sweep runs -- the
mqttclientDAT itself always stays connected regardless (never toggle
mqttclientDAT.par.active after it's up).
"""
import json
import time

OFFLINE_AFTER_S = 90
STALENESS_CHECK_S = 10

_devices = {}   # device_id -> {status..., "_last_seen": float}
_last_staleness_check = 0.0
_dirty = False  # set True by _rebuild_table(), cleared+reported by tick()


def _enabled():
	try:
		return bool(me.parent().par.Devicecontrol.eval())
	except Exception:
		return True


def _mqtt():
	return me.parent().op('mqtt_control')


def get_devices():
	"""Snapshot of device_id -> last received status payload."""
	return {k: dict(v) for k, v in _devices.items()}


def send_command(device_id, service, action):
	"""Call from a Button/List COMP: play='enable', stop='disable',
	restart='restart'. Safe from a UI callback (main thread)."""
	dat = _mqtt()
	if dat is None or not dat.isConnected:
		print("[GAIA Fleet Control] not connected, command ignored")
		return
	dat.publish(
		f"gaia/device/{device_id}/command",
		json.dumps({"action": action, "service": service}).encode('utf-8'),
	)


def _svc_keys(d):
	keys = list((d.get("services") or {}).keys())
	for k in (d.get("config") or {}):
		if k not in keys:
			keys.append(k)
	return keys


def _rebuild_table():
	global _dirty
	table = me.parent().op("devices_table")
	if table is None:
		return
	_dirty = True
	table.clear()
	table.appendRow(["device_id", "name", "stanza", "role", "service", "state", "offline"])
	now = time.time()
	for device_id, d in sorted(_devices.items()):
		offline = (now - d.get("_last_seen", 0)) > OFFLINE_AFTER_S
		keys = _svc_keys(d) or [""]
		for svc in keys:
			state = (d.get("services") or {}).get(svc, "unknown")
			table.appendRow([
				device_id, d.get("name") or d.get("stanza") or device_id,
				d.get("stanza", ""), d.get("role", ""), svc, state, str(offline),
			])


def tick():
	"""Call from Execute DAT onFrameStart, EVERY FRAME -- recomputes the
	'offline' flag every STALENESS_CHECK_S seconds (devices don't publish
	every frame, but a vanished device must still show offline within
	OFFLINE_AFTER_S). Returns True if devices_table changed this frame."""
	global _last_staleness_check, _dirty
	if not _enabled():
		return False
	now = time.time()
	if (now - _last_staleness_check) >= STALENESS_CHECK_S:
		_last_staleness_check = now
		_rebuild_table()
	changed, _dirty = _dirty, False
	return changed


# ---- Called from mqtt_control_callbacks -- already on the main thread
# (native Callbacks DAT dispatch). -----------------------------------------

def on_connect(dat):
	dat.subscribe("gaia/device/+/status")
	print("[GAIA Fleet Control] Connected, listening on gaia/device/+/status")


def on_connect_failure(msg):
	print(f"[GAIA Fleet Control] MQTT connection failed: {msg}")


def on_connection_lost(msg):
	print(f"[GAIA Fleet Control] Disconnected: {msg}")


def on_message(topic, payload):
	if not _enabled():
		return
	if isinstance(payload, bytes):
		payload = payload.decode('utf-8', errors='replace')
	try:
		d = json.loads(payload)
	except Exception as e:
		print(f"[GAIA Fleet Control] Invalid status: {e}")
		return
	device_id = d.get("device_id")
	if not device_id:
		return
	d["_last_seen"] = time.time()
	_devices[device_id] = d
	_rebuild_table()
