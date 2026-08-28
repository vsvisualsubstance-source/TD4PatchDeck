"""
Auto-discovery/self-correction of the Gaia broker host via gaia_beacon (UDP
8899, GAIA_DISCOVER protocol, documented in the gaia repo's
docs/discovery-protocol.md). Ported from TD-Gaia's proven
Bridge/gaia_config/beacon_discovery.py, trimmed to Brokerhost only (this
component has no OSC-out consumer that would need a mirrored "Corehost").

WHAT IT COVERS: only Brokerhost. Every _PROBE_INTERVAL_S, sends
'GAIA_DISCOVER' to whatever Brokerhost is CURRENTLY set to; if that host
answers as service=='gaia-core', Brokerhost is corrected to the reported
mqtt_host. This is self-correction, not zero-config network-wide discovery
-- it only helps when the current Brokerhost is already reachable (a small
drift, e.g. someone hand-edited it, or the deployment's Gaia Core changed
IP while remaining on the same subnet/reachable path). If Brokerhost points
at an address nothing answers on, this does nothing and the fixed value
stays in use -- no regression versus not having it.

FRAMING GOTCHA (cost real debugging time to find on TD-Gaia, will bite
again if re-derived from scratch): the beacon's reply is bare JSON with NO
line terminator, so the UDP Out DAT's Row/Callback Format must be 'One Per
Byte' -- 'One Per Line'/'One Per Message' never see a closed line and
onReceive never fires with a complete message. Buffer byte-by-byte and
attempt json.loads() on every arrival; a valid dict closes the message.
"""
import json
import time

_PROBE_INTERVAL_S = 30.0
_last_probe = 0.0

_rx_buffer = ''
_RX_BUFFER_MAX = 4096  # guard against a buffer that never closes


def _enabled(cfg):
	try:
		return bool(cfg.par.Beacondiscovery.eval())
	except Exception:
		return False


def resolve():
	"""Call every frame from an Execute DAT onFrameStart -- throttled
	internally, retries forever every _PROBE_INTERVAL_S (self-healing if
	Core's IP drifts while TD is already running)."""
	global _last_probe
	probe = op('beacon_probe')
	if probe is None or not _enabled(probe.parent()):
		return
	now = time.time()
	if (now - _last_probe) < _PROBE_INTERVAL_S:
		return
	_last_probe = now
	probe.send('GAIA_DISCOVER')


def onReceive(dat, rowIndex, message, bytes, peer):
	"""UDP Out DAT callback, one byte at a time -- see the framing note
	above for why this isn't a complete message per call."""
	global _rx_buffer
	if not _enabled(dat.parent()):
		_rx_buffer = ''
		return
	_rx_buffer += message
	if len(_rx_buffer) > _RX_BUFFER_MAX:
		_rx_buffer = ''
		return
	try:
		reply = json.loads(_rx_buffer)
	except (ValueError, TypeError):
		return  # not a complete JSON message yet, keep buffering
	_rx_buffer = ''
	_apply_reply(dat.parent(), reply)


def _apply_reply(cfg, reply):
	if reply.get('service') != 'gaia-core':
		return
	host = reply.get('mqtt_host')
	if not host:
		return

	changed = cfg.par.Brokerhost.eval() != host
	if changed:
		cfg.par.Brokerhost.val = host

	stamp = time.strftime('%H:%M:%S')
	cfg.par.Beaconstatus.val = 'auto: %s (beacon @ %s, %s)' % (
		host, reply.get('hostname', '?'), stamp)
	if changed:
		print('[GAIA Beacon] Brokerhost -> %s' % host)
	return
