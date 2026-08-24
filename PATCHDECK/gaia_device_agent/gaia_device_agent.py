"""
GAIA Device Agent — vive DENTRO il progetto TouchDesigner (Text DAT +
Execute DAT + un mqttclientDAT nativo), non e' un processo di sistema
esterno. Nessun manifest sul filesystem, nessun path a TouchDesigner.exe:
gira ovunque il .toe gira, configurato con i parametri del componente che
lo ospita e salvato nel progetto stesso — portabile da una macchina
all'altra senza toccare nulla fuori dal .toe.

RISCRITTO 2026-08-05 (v2): la v1 usava paho.mqtt.client + thread Python
(queue.Queue, un registro su sys, un thread di heartbeat separato) perche'
il Python embedded di TD non ha pip. Quel disegno funzionava SOLO perche'
Envoy, quando parte, aggiunge il proprio venv a sys.path di TD
(EmbodyExt._setupEnvironment) — su una macchina "solo spettacolo" senza
Envoy mai avviato, l'import falliva silenziosamente. Il progetto ha gia'
un mqttclientDAT NATIVO (vedi Bridge/mqtt_bridge/mqtt_gaia, il firehose di
debug) — zero pacchetti esterni, zero sys.path, callback che girano gia'
sul thread principale di TD. Questa v2 usa lo stesso operatore nativo:
elimina la dipendenza da paho E tutta la macchina di thread-safety (non
serve piu': non esiste un client Python vivo da tracciare/fermare tra un
project.save() e l'altro, l'oggetto "client" e' l'operatore mqttclientDAT
stesso, gestito da TD come qualunque altro DAT esternalizzato).

SETUP IN TD
1. COMP contenitore ("gaia_agent"), Custom Page con:
     Deviceid  (Str)  default derivato dall'hostname macchina (espressione)
     Stanza    (Str)  es. "salotto"
     Name      (Str)  es. "AV Herbarium"
     Mqtthost  (Str)  espressione verso gaia_config
     Mqttport  (Int)  espressione verso gaia_config
2. Un mqttclientDAT "mqtt_agent" nello stesso COMP, Network Address =
   espressione 'tcp://%s:%d' % (Mqtthost, Mqttport), Active=1. La sua
   Callbacks DAT ("mqtt_agent_callbacks") delega qui (vedi in fondo).
3. Text DAT "gaia_device_agent" con QUESTO file come sorgente esterna.
4. Execute DAT "agent_lifecycle" nello stesso COMP:
       def onFrameStart(frame):
           op('gaia_device_agent').module.tick()
           return
   Un SOLO hook necessario: tick() e' un heartbeat throttlato via
   time.time() (stesso pattern di camera_resolver.py), NON serve piu'
   onCreate/onExit — il mqttclientDAT si connette da solo (Active=1 +
   Network Address validi) ogni volta che l'operatore e' vivo, incluso
   dopo un TDN reimport o uno strip/restore di Embody.

ESPORRE UN SERVIZIO REALE (facoltativo)
Senza fare nient'altro l'agent compare gia' in Admin (presenza + heartbeat,
"services" vuoto, i comandi restano no-op loggati). Per collegare un
controllo vero, da un TUO script di progetto — questo file resta identico
in ogni progetto, non editarlo qui:
    agent = op('gaia_agent/gaia_device_agent').module
    agent.register_service('osc_in',
        start=lambda: setattr(op('oscin1').par, 'active', 1),
        stop=lambda: setattr(op('oscin1').par, 'active', 0),
        status=lambda: bool(op('oscin1').par.active.eval()))
NOTA: start/stop/status vengono sempre invocati da on_message() (gia' sul
thread principale, dispatch nativo del Callbacks DAT), quindi e' sicuro
toccare op()/par dentro di essi.

Stesso protocollo MQTT degli agent Pi/OPS (pi/agent/agent.py,
ops/agent/agent.py): gaia/device/{id}/status (retained, ogni 30s) +
comandi enable/disable/restart su gaia/device/{id}/command e
gaia/device/all/command.

AGGIUNTO 2026-08-05: il payload di status ora include "ip" (stesso schema
pi/agent.py._get_ip()/ops/agent.py._get_ip() — nessuna dipendenza esterna,
solo socket della stdlib). Non è decorativo: pi/mediapipe/mediapipe_node.py
lo usa per il mocap diretto OPS→TD (canale 2, bypassa il Core) — prima la
destinazione OSC era un IP fisso in config, andato stantio in produzione
appena TD è girata su una macchina diversa da quella scritta lì. Ora
mediapipe ascolta gaia/device/+/status e si ridirige da solo verso il vero
IP del TD sulla STESSA macchina (match su device_id == "td-{hostname}").

AGGIUNTO 2026-08-06: on_connect ora fa anche l'announce col Device
Registry di Node-RED (gaia/devices/{id}/announce + subscribe a
gaia/devices/{id}/config) — mancava del tutto, per questo un'istanza TD
compariva in Pi Manager ma /api/provision/assign rispondeva "device non
trovato" e la Stanza restava un'etichetta mai registrata nel roomGraph
reale. Vedi _publish_announce().

AGGIUNTO 2026-08-06 (2): due migliorie richieste dopo aver visto quanto
poco l'agent facesse di suo — _publish_profile() (gaia/devices/{id}/profile,
retained, stesso schema di pi/agent.py/ops/agent.py: capabilities derivate
dai servizi REALMENTE registrati, non assunte) e _last_error nello status
(ultima eccezione da un servizio, visibile in Admin senza dover aprire il
Textport di TD).

FIX 2026-08-06: verificato dal vivo con Envoy, la stesura precedente era
stata scritta e verificata solo offline): _last_error non veniva MAI
azzerato dopo un successo, contraddicendo l'intento dichiarato ("resta
finche' non arriva un successo") — un errore transitorio sarebbe rimasto
visibile in Admin per sempre. _run() ora azzera _last_error quando fn()
non solleva eccezioni.

AGGIUNTO 2026-08-06 (3): fps/target_fps/dropped_frames nello status —
project.cookRate (via _target_fps) è SOLO il target configurato, non
l'fps reale (idea iniziale scartata su correzione esplicita). fps vero
misurato in perf_tick() (nuova chiamata, OGNI frame, non throttlata come
tick()) confrontando il tempo reale trascorso tra due frame consecutivi —
va aggiunta anche in agent_lifecycle.py, vedi lì.

AGGIUNTO 2026-08-24 (v3, register_param): register_service() copre solo
controlli booleani (on/off). ControllerV7 ha bisogno di esporre valori
CONTINUI per-canale (guadagno/soglie di un componente di analisi audio:
Low/Mid/High gain, soglie, smooth, per 47 canali) — un servizio booleano
non li rappresenta. Aggiunta additiva, stesso pattern di register_service:
    agent.register_param('ch0_Lowgain',
        get=lambda: float(op('...').par.Lowgain.eval()),
        set=lambda value: setattr(op('...').par, 'Lowgain', float(value)))
Comando MQTT: {"action": "set", "param": "ch0_Lowgain", "value": 1.2} su
gaia/device/{id}/command (stesso topic di enable/disable/restart, azione
diversa). Nessun progetto esistente (PatchDeck) usa register_param, quindi
il comportamento per chi non lo chiama e' identico a prima — _params parte
vuoto, "params" nello status e' {} finche' nessuno registra nulla.
"""
import json
import socket
import time

_START_TS = time.time()
_services = {}   # name -> {"start": fn, "stop": fn, "status": fn}
_params = {}     # name -> {"get": fn, "set": fn(value)} — valori continui (AGGIUNTO v3)

_HEARTBEAT_S = 30
_last_heartbeat = 0.0

_last_error = None   # {"context","message","ts"} — ultimo errore, visibile in Admin senza dover aprire il Textport


def _record_error(context, exc):
	global _last_error
	_last_error = {"context": context, "message": str(exc), "ts": int(time.time() * 1000)}
	print(f"[GAIA Agent] Errore in {context}: {exc}")


# ── Performance reale (2026-08-06) ─────────────────────────────────────
_PERF_WINDOW = 90         # campioni recenti tenuti per la media fps
_perf_intervals = []      # secondi tra un frame e il successivo
_perf_last_time = None
_perf_dropped_window = 0  # frame "persi" stimati, azzerato ad ogni publish di status


def perf_tick():
	"""Chiamare OGNI frame da onFrameStart (agent_lifecycle.py), non
	throttlata — a differenza di tick()."""
	global _perf_last_time, _perf_dropped_window
	now = time.time()
	if _perf_last_time is not None:
		dt = now - _perf_last_time
		_perf_intervals.append(dt)
		if len(_perf_intervals) > _PERF_WINDOW:
			_perf_intervals.pop(0)
		target = _target_fps()
		if target and dt > 0:
			expected = dt * target
			if expected > 1.5:
				_perf_dropped_window += int(round(expected)) - 1
	_perf_last_time = now


def _target_fps():
	try:
		return round(float(project.cookRate), 2)
	except Exception:
		return None


def _measured_fps():
	if len(_perf_intervals) < 2:
		return None
	avg_dt = sum(_perf_intervals) / len(_perf_intervals)
	return round(1.0 / avg_dt, 1) if avg_dt > 0 else None


def _get_ip():
	"""Stesso approccio di pi/agent/agent.py e ops/agent/agent.py (UDP
	'connect' a un indirizzo pubblico, nessun pacchetto reale inviato,
	legge solo l'IP locale scelto dal routing)."""
	try:
		with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
			s.connect(("8.8.8.8", 80))
			return s.getsockname()[0]
	except Exception:
		return "unknown"


def register_service(name, start=None, stop=None, status=None):
	"""Chiamalo dal tuo script di progetto per esporre un controllo reale.
	status() deve restituire True/False (o None se sconosciuto). Le tre
	funzioni sono sempre chiamate da on_message()/tick() sul thread
	principale — possono toccare op()/par liberamente."""
	_services[name] = {"start": start, "stop": stop, "status": status}


def register_param(name, get=None, set=None):
	"""AGGIUNTO v3 — chiamalo dal tuo script di progetto per esporre un
	valore CONTINUO controllabile (gain, soglia, ecc.), non un semplice
	on/off. get() deve restituire il valore corrente (qualunque tipo
	JSON-serializzabile); set(value) applica un nuovo valore. Sempre
	invocate da on_message() sul thread principale — sicuro toccare
	op()/par dentro di esse."""
	_params[name] = {"get": get, "set": set}


def _mqtt():
	return me.parent().op('mqtt_agent')


def _read_config():
	host = me.parent()

	def par(name, default):
		try:
			v = host.par[name].eval()
			return v if v not in (None, "") else default
		except Exception:
			return default

	return {
		"device_id": par("Deviceid", f"td-{project.name}"),
		"stanza":    par("Stanza", "unknown"),
		"name":      par("Name", project.name),
	}


def _service_status(name):
	fn = _services.get(name, {}).get("status")
	if not fn:
		return "unknown"
	try:
		return "active" if fn() else "inactive"
	except Exception as e:
		_record_error(f"status({name})", e)
		return "unknown"


def _param_value(name):
	"""AGGIUNTO v3 — valore corrente di un parametro registrato, per lo status."""
	fn = _params.get(name, {}).get("get")
	if not fn:
		return None
	try:
		return fn()
	except Exception as e:
		_record_error(f"get({name})", e)
		return None


def _capabilities():
	"""Derivate da cosa e' REALMENTE registrato (register_service), non
	assunte a priori — un progetto senza dmx_out non deve dichiarare dmx."""
	return {
		"display": True,   # sempre vero: un'istanza TD e' per definizione uno strato visivo
		"dmx":     "dmx_out" in _services,
		"mocap":   "mocap_bridge" in _services,
	}


def _publish_status():
	global _perf_dropped_window
	dat = _mqtt()
	if dat is None or not dat.isConnected:
		return
	cfg = _read_config()
	payload = {
		"device_id":      cfg["device_id"],
		"name":           cfg["name"],
		"stanza":         cfg["stanza"],
		"role":           "touchdesigner",
		"ip":             _get_ip(),
		"services":       {n: _service_status(n) for n in _services},
		"params":         {n: _param_value(n) for n in _params},   # AGGIUNTO v3
		"uptime":         int(time.time() - _START_TS),
		"last_error":     _last_error,
		"fps":            _measured_fps(),
		"target_fps":     _target_fps(),
		"dropped_frames": _perf_dropped_window,
		"ts":             int(time.time() * 1000),
	}
	dat.publish(f"gaia/device/{cfg['device_id']}/status", json.dumps(payload).encode('utf-8'), retain=True)
	_publish_profile(dat, cfg)
	_perf_dropped_window = 0   # finestra chiusa, riparte da zero fino al prossimo publish


def _publish_profile(dat, cfg):
	"""Profilo semantico retained (docs/gaia-semantico.md), stesso schema
	di pi/agent.py._publish_profile()/ops/agent.py._publish_profile()."""
	profile = {
		"device_id":    cfg["device_id"],
		"role":         "touchdesigner",
		"room":         cfg["stanza"],
		"ip":           _get_ip(),
		"capabilities": _capabilities(),
		"services":     {n: _service_status(n) for n in _services},
		"sw_version":   "1.0",
		"ts":           int(time.time() * 1000),
	}
	dat.publish(f"gaia/devices/{cfg['device_id']}/profile", json.dumps(profile).encode('utf-8'), retain=True)


def _apply_command(cmd):
	action  = cmd.get("action", "")
	service = cmd.get("service", "")
	param   = cmd.get("param", "")
	svc = _services.get(service)
	prm = _params.get(param)
	print(f"[GAIA Agent] Comando: {cmd}")

	def _run(fn, label):
		global _last_error
		try:
			fn()
			_last_error = None
		except Exception as e:
			_record_error(f"{label}({service or param})", e)

	if action == "set":
		# AGGIUNTO v3 — set di un valore continuo registrato via register_param
		if not prm or not prm.get("set"):
			print(f"[GAIA Agent] Parametro '{param}' non registrato o non scrivibile")
		else:
			_run(lambda: prm["set"](cmd.get("value")), "set")
	elif action in ("enable", "disable", "restart") and not svc:
		print(f"[GAIA Agent] Servizio '{service}' non registrato (register_service mai chiamato)")
	elif action == "enable" and svc.get("start"):
		_run(svc["start"], "start")
	elif action == "disable" and svc.get("stop"):
		_run(svc["stop"], "stop")
	elif action == "restart" and svc:
		if svc.get("stop"):
			_run(svc["stop"], "stop")
		if svc.get("start"):
			_run(svc["start"], "start")
	elif action == "status":
		pass
	else:
		print(f"[GAIA Agent] Azione ignorata: {action}")

	_publish_status()


def tick():
	"""Chiamare da Execute DAT onFrameStart, OGNI FRAME — heartbeat
	throttlato internamente a _HEARTBEAT_S (stesso pattern di
	camera_resolver.py), nessun thread separato necessario."""
	global _last_heartbeat
	now = time.time()
	if (now - _last_heartbeat) < _HEARTBEAT_S:
		return
	_last_heartbeat = now
	_publish_status()


# ---- Chiamate da mqtt_agent_callbacks — girano gia' sul thread principale
# (dispatch nativo del Callbacks DAT, verificato su mqtt_bridge/mqtt_gaia). --

def _publish_announce(dat, cfg):
	"""Handshake col Device Registry di Node-RED. Stesso payload esatto di
	pi/mediapipe/mediapipe_node.py._on_connect (room_claim, non room)."""
	announce = {
		"device_id":  cfg["device_id"],
		"type":       "touchdesigner",
		"ip":         _get_ip(),
		"room_claim": cfg["stanza"],
		"ts":         int(time.time() * 1000),
	}
	dat.publish(f"gaia/devices/{cfg['device_id']}/announce", json.dumps(announce).encode('utf-8'))


def on_connect(dat):
	cfg = _read_config()
	dat.subscribe(f"gaia/device/{cfg['device_id']}/command")
	dat.subscribe("gaia/device/all/command")
	dat.subscribe(f"gaia/devices/{cfg['device_id']}/config")
	print(f"[GAIA Agent] Connesso — device_id: {cfg['device_id']}")
	_publish_status()
	_publish_announce(dat, cfg)


def on_connect_failure(msg):
	print(f"[GAIA Agent] Connessione MQTT fallita: {msg}")


def on_connection_lost(msg):
	print(f"[GAIA Agent] Disconnesso: {msg}")


def on_message(topic, payload):
	if isinstance(payload, bytes):
		payload = payload.decode('utf-8', errors='replace')
	try:
		d = json.loads(payload)
	except Exception as e:
		print(f"[GAIA Agent] Messaggio non valido: {e}")
		return
	if topic.endswith('/config'):
		# Risposta autoritativa del Device Registry (retained) — solo log,
		# NON sovrascrive Stanza in automatico: è un parametro scelto
		# dall'artista nel COMP, non va cambiato di nascosto sotto un nome
		# diverso senza che se ne accorga.
		print(f"[GAIA Agent] Config dal Device Registry: {d}")
		return
	_apply_command(d)
