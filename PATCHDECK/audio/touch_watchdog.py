"""
Watchdog Touch In (porte 8000/8001 da ControllerV8).

Ogni CHECK_EVERY frame legge info_touchin1/info_touchin2. Se un Touch In
attivo resta disconnesso o senza nuovi frame per STALL_SEC secondi, forza
una riconnessione: alza il flag storage 'touch_kick_<nome>' sul COMP audio
(l'espressione di Active lo legge -> active=0), e lo riabbassa dopo
KICK_FRAMES frame (-> active=1, nuova connessione). Tra due tentativi
sullo stesso Touch In passano almeno BACKOFF_SEC secondi.
Un Touch In che nessuno cuoce viene ignorato (mai forzato a cuocere).
"""

CHECK_EVERY = 30     # frame (~1 s a 30 fps)
STALL_SEC = 3.0      # secondi senza dati/connessione prima di intervenire
KICK_FRAMES = 3      # frame con Active spento durante la riconnessione
BACKOFF_SEC = 5.0    # attesa minima tra due riconnessioni

_state = {}


def onFrameEnd(frame):
	if absTime.frame % CHECK_EVERY:
		return
	now = absTime.seconds
	for name in ('touchin1', 'touchin2'):
		_checkTouchIn(name, now)
	return


def _checkTouchIn(name, now):
	touch_in = op(name)
	info = op('info_' + name)
	if not touch_in or not info:
		return
	st = _state.setdefault(name, {'frames': -1.0, 'healthy_at': now, 'last_kick': -1e9})

	if not touch_in.par.active.eval():
		# Spento (on-demand o durante un kick): niente da sorvegliare.
		st['frames'] = -1.0
		st['healthy_at'] = now
		return

	# Se nessun consumatore cuoce il Touch In, non leggere l'Info CHOP:
	# leggerlo forzerebbe la cottura e smaltirebbe in un colpo solo tutto
	# l'arretrato UDP (con l'audio 8001 erano ~350 ms di blocco al secondo).
	# Un consumatore vero lo cuoce ~ogni frame; le cotture indotte dalla
	# lettura stessa sono 1-2, quindi serve almeno meta' dei frame.
	cooks = touch_in.totalCooks
	consumed = (cooks - st.get('cooks', cooks)) >= CHECK_EVERY // 2
	st['cooks'] = cooks
	if not consumed:
		st['frames'] = -1.0
		st['healthy_at'] = now
		return

	frames_ch = info['frames_received']
	connected_ch = info['connected']
	frames = frames_ch.eval() if frames_ch is not None else 0.0
	connected = connected_ch.eval() if connected_ch is not None else 0.0

	receiving = frames != st['frames']
	st['frames'] = frames
	if connected >= 0.5 and receiving:
		st['healthy_at'] = now
		return

	if (now - st['healthy_at']) < STALL_SEC or (now - st['last_kick']) < BACKOFF_SEC:
		return

	st['last_kick'] = now
	st['healthy_at'] = now
	reason = 'disconnesso' if connected < 0.5 else 'nessun dato'
	debug(f"[TOUCH] {name}: {reason} da {STALL_SEC:.0f}s -> riconnessione")
	key = 'touch_kick_' + name
	parent().store(key, True)
	run("me.parent().store(args[0], False)", key, fromOP=me, delayFrames=KICK_FRAMES)
