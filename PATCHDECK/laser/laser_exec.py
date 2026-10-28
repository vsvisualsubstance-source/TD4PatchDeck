"""
Execute DAT -- sorgente laser 'patchdeck' per il laser gateway di OPS
(TD4Gaia OPS 33, formato GLF1 via gaia_laser_out).

A fine frame legge l'uscita video ridotta (null_contours: pre_dim ->
160x90 -> Soglia/Bordi) e ne trova i contorni con OpenCV
(findContours + approxPolyDP) sopra Threshold. Scarta le forme piu'
piccole di Minsize, mette prima le piu' grandi fino a Maxpoints e manda
una polilinea: un punto nero apre ogni forma (spostamento a raggio
spento), l'ultimo punto la richiude.

Le immagini si leggono con numpyArray(delayed=True): arriva il frame
precedente (33 ms di ritardo) ma la GPU non si ferma ad aspettare il
download. Un Trace SOP lo faceva in modo sincrono e costava ~10 ms per
frame (28 fps invece di 30).

Coordinate: x -1..1 sulla larghezza, y in proporzione 16:9, per Size e
per l'audio del controller (low0/kick0, canale ch0) se Audioamount > 0.
Colore: Video = pixel di null_color (32x18) sotto ogni punto, portato
alla massima luminosita' (il contorno cade a meta' tra chiaro e scuro);
Palette = colore fisso. Tutto moltiplicato per il dim del master
(PATCHES/MASTER_DIM brightness1), cosi' un blackout video spegne anche
il laser. Arming e sicurezza restano nel gateway.
"""

import cv2
import numpy as np

_SOURCE = 'patchdeck'
_GLF_PORT = 7480
_TARGET_FPS = 30.0
_APPROX_PX = 0.75  # tolleranza di semplificazione dei contorni, in pixel della 160x90
_state = {'active': False, 'error': None}


def _laser():
	return parent()


def _gateway(L):
	return (str(L.par.Gateway.eval()).strip() or '192.168.1.240', _GLF_PORT)


def _target(L):
	t = str(L.par.Target.eval())
	return '*' if t == 'all' else t


def _scale(L):
	scale = 2.0 * float(L.par.Size.eval())
	amount = float(L.par.Audioamount.eval())
	audio = op('null_audio')
	if amount > 0 and audio is not None:
		levels = [c.eval() for c in (audio['low0'], audio['kick0']) if c is not None]
		if levels:
			scale *= 1.0 + amount * min(max(max(levels), 0.0), 1.0)
	return scale


def _image(name):
	"""Ultimo download pronto del TOP (numpy, righe dall'alto), senza
	fermare la GPU; None solo se non c'e' ancora niente."""
	return op(name).numpyArray(delayed=True)


def _shapes(L):
	"""Forme come array Nx2 di pixel (colonna, riga dall'alto), dalla piu'
	grande, richiuse sul primo punto, senza superare Maxpoints (blank
	compresi)."""
	img = _image('null_contours')
	if img is None:
		return [], (1, 1)
	h, w = img.shape[0], img.shape[1]
	lum = img[:, :, 0] * 0.299 + img[:, :, 1] * 0.587 + img[:, :, 2] * 0.114
	mask = (lum > float(L.par.Threshold.eval())).astype(np.uint8)
	contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
	min_px = float(L.par.Minsize.eval()) * w
	found = []
	for c in contours:
		x, y, bw, bh = cv2.boundingRect(c)
		if max(bw, bh) < min_px:
			continue
		pts = cv2.approxPolyDP(c, _APPROX_PX, True).reshape(-1, 2)
		if len(pts) < 2:
			continue
		found.append((bw + bh, pts))
	found.sort(key=lambda s: -s[0])
	budget = int(L.par.Maxpoints.eval())
	shapes, used = [], 0
	for _, pts in found:
		need = len(pts) + 2  # punto nero d'ingresso + chiusura
		if used + need > budget:
			continue
		shapes.append(np.vstack((pts, pts[:1])))
		used += need
	return shapes, (w, h)


def _colors(L, u, v):
	"""RGB 0..1 per ogni punto (array Nx3); u, v 0..1 con v dall'alto."""
	if L.par.Color.eval() == 'palette':
		base = np.array([L.par.Paletter.eval(), L.par.Paletteg.eval(), L.par.Paletteb.eval()], dtype=np.float32)
		return np.tile(base, (len(u), 1))
	img = _image('null_color')
	if img is None:
		return np.ones((len(u), 3), dtype=np.float32)
	h, w = img.shape[0], img.shape[1]
	col = np.clip((u * w).astype(int), 0, w - 1)
	row = np.clip((v * h).astype(int), 0, h - 1)
	rgb = img[row, col, :3].astype(np.float32)
	peak = rgb.max(axis=1, keepdims=True)
	return np.where(peak > 0.02, rgb / np.maximum(peak, 1e-6), 1.0)


def _send_frame(L):
	out = mod('gaia_laser_out')
	gateway, target = _gateway(L), _target(L)
	shapes, (w, h) = _shapes(L)
	if not shapes:
		out.blackout(_SOURCE, target=target, gateway=gateway)
		return 0
	pts = np.vstack([np.vstack((s[:1], s)) for s in shapes]).astype(np.float32)
	lit = np.concatenate([np.r_[0.0, np.ones(len(s))] for s in shapes]).astype(np.float32)
	u = (pts[:, 0] + 0.5) / w
	v = (pts[:, 1] + 0.5) / h
	scale = _scale(L)
	x = (u - 0.5) * scale
	y = (0.5 - v) * (h / w) * scale
	rgb = _colors(L, u, v)
	dim = min(max(float(op('../PATCHES/MASTER_DIM').par.brightness1.eval()), 0.0), 1.0)
	rgb *= (lit * dim)[:, None]
	out.send_points(x, y, rgb[:, 0], rgb[:, 1], rgb[:, 2],
		source=_SOURCE, target=target, gateway=gateway)
	return len(pts)


def _report(L, n, error=None):
	if L.par.Points.eval() != n:
		L.par.Points = n
	if error != _state['error']:
		_state['error'] = error
		if error:
			debug('[laser] invio fallito:', error)


def onFrameEnd(frame: int):
	"""
	Called at the end of each frame.
	"""
	L = _laser()
	if not L.par.Enable.eval():
		if _state['active']:
			_state['active'] = False
			mod('gaia_laser_out').blackout(_SOURCE, target=_target(L), gateway=_gateway(L))
			_report(L, 0)
		return
	_state['active'] = True
	step = max(1, int(round(project.cookRate / _TARGET_FPS)))
	if frame % step:
		return
	try:
		_report(L, _send_frame(L))
	except Exception as e:
		_report(L, 0, '%s: %s' % (type(e).__name__, e))
	return
