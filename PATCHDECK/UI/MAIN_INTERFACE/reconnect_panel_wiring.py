
# ------------------------------------------------
# Execute DAT - self-heal for control_ui's panel hierarchy.
#
# TD's Container COMP with externaltox enabled re-wires its
# comp-level input connector to whatever it was connected to
# THE FIRST TIME that .tox was saved, on every project load --
# not to the current live wiring, and not to whatever the last
# save_externalization/save_project wrote. Confirmed via the
# TD forum (externaltox loses in/out connections on project
# load). Re-saving the .tox repeatedly does not change this.
#
# The exact frame this reload lands on is NOT predictable --
# fixed-delay retries (checkpoints at 30/90/.../900 frames) were
# still broken well past all of them in testing. So instead of
# guessing a frame, this polls-and-corrects every POLL_INTERVAL
# frames for the first POLL_WINDOW frames after start, which
# converges regardless of when the native reload actually fires.
# Stops after the window -- never runs continuously. Idempotent,
# runs are cheap (a handful of .connect() calls).
#
# MAIN_INTERFACE itself has externaltox set, so its OWN reload
# can destroy and recreate this DAT after the project's initial
# onStart already fired -- a recreated op only gets onCreate(),
# so both callbacks arm the same poll window.
#
# KNOWN ISSUE (2026-09-16): in testing, TD never actually invoked
# onCreate/onStart/onFrameStart on this DAT automatically at all --
# totalCooks stayed at 5 across a full restart + ~2 min runtime,
# matching only manual execute_python calls. Calling
# ReconnectPanelWiring() directly always works correctly. Left in
# place for manual testing; do not assume it self-heals until that
# is independently confirmed.
#
# Intended hierarchy:
#   control_ui -> 2_rotary_panel -> (rotaries_a, rotaries_b)
#   control_ui -> container2 -> (sliders_a, sliders_b)
# ------------------------------------------------

POLL_INTERVAL = 30
POLL_WINDOW = 3600  # ~2 min at 30fps -- generous startup coverage

def ReconnectPanelWiring():
	p = me.parent()
	pairs = [
		('control_ui', '2_rotary_panel'),
		('2_rotary_panel', 'rotaries_a'),
		('2_rotary_panel', 'rotaries_b'),
		('control_ui', 'container2'),
		('container2', 'sliders_a'),
		('container2', 'sliders_b'),
	]
	fixed = 0
	for src_name, dst_name in pairs:
		src = p.op(src_name)
		dst = p.op(dst_name)
		if src is None or dst is None:
			continue
		dst.inputCOMPConnectors[0].connect(src)
		fixed += 1
	return fixed

def _armPolling():
	me.store('_poll_start_frame', absTime.frame)
	me.par.active = True
	return

def onStart():
	_armPolling()
	return

def onCreate():
	_armPolling()
	return

def onExit():
	return

def onFrameStart(frame):
	start = me.fetch('_poll_start_frame', None)
	if start is None:
		return
	elapsed = frame - start
	if elapsed > POLL_WINDOW:
		me.par.active = False
		return
	if elapsed % POLL_INTERVAL == 0:
		fixed = ReconnectPanelWiring()
		debug(f'ReconnectPanelWiring: reasserted {fixed} panel connection(s) (frame {frame}, +{elapsed})')
	return

def onFrameEnd(frame):
	return

def onPlayStateChange(state):
	return

def onDeviceChange():
	return

def onProjectPreSave():
	return

def onProjectPostSave():
	return
