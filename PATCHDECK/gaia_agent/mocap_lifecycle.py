"""
Execute DAT

me - this DAT

Make sure the corresponding toggle is enabled in the Execute DAT.
"""

import time

_RESET_INTERVAL_S = 90.0
_last_reset = 0.0

_TERMINAL_CHOPS = ('chop_pose', 'chop_hand', 'chop_face', 'chop_meta')


def onStart():
	"""
	Called when the project starts.
	"""
	return

def onCreate():
	"""
	Called when the DAT is created.
	"""
	return

def onExit():
	"""
	Called when the project exits.
	"""
	return

_COOK_EVERY_N_FRAMES = 4  # ~15Hz at 60fps project rate -- see perf note below

def onFrameStart(frame: int):
	"""
	Called at the start of each frame.
	
	Args:
		frame: The current frame number
	"""
	global _last_reset

	# Terminal Script CHOPs read oscin_mocap via a plain op() call (not a
	# wired CHOP input), so TD's normal cook-dependency graph does not pick
	# up new OSC data automatically -- force-cook them so they reflect
	# latest mocap regardless of whether anything is currently demanding
	# their output.
	#
	# PERF: measured live -- force-cooking all 4 every frame cost ~12.5ms/
	# frame CPU (get_op_performance on gaia_agent, childrenCPUCookTime),
	# dropping project fps to 52 (below performance.md's 54fps/90% stop
	# threshold). Each cook does an O(raw channel count) Python scan over
	# oscin_mocap, which also grows over a session (item 55) -- uncapped,
	# this only gets worse. Throttled to every Nth frame instead: mocap-
	# driven abstract visuals don't need 60Hz semantic updates, and this
	# cut the cost proportionally with fps back above target in testing.
	if frame % _COOK_EVERY_N_FRAMES == 0:
		for name in _TERMINAL_CHOPS:
			chop = op(name)
			if chop is not None:
				chop.cook(force=True)

	# oscin_mocap has no automatic channel expiry (verified live: 2025+
	# channels within under a minute of live traffic) -- periodically wipe
	# and let it rebuild from live OSC only, bounding its own CPU memory.
	# The terminal CHOPs above are bounded regardless, so this only protects
	# oscin_mocap's own footprint, not correctness of what's read from it.
	now = time.time()
	if (now - _last_reset) >= _RESET_INTERVAL_S:
		_last_reset = now
		mocap = op('oscin_mocap')
		if mocap is not None:
			mocap.par.resetchannelspulse.pulse()
	return

def onFrameEnd(frame: int):
	"""
	Called at the end of each frame.
	
	Args:
		frame: The current frame number
	"""
	return

def onPlayStateChange(state: bool):
	"""
	Called when the play state changes.
	
	Args:
		state: False if the timeline was just paused
	"""
	return

def onDeviceChange():
	"""
	Called when a device change occurs.
	"""
	return

def onProjectPreSave():
	"""
	Called before the project is saved.
	"""
	return

def onProjectPostSave():
	"""
	Called after the project is saved.
	"""
	return
