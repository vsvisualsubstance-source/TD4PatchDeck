"""
Execute DAT

me - this DAT

Make sure the corresponding toggle is enabled in the Execute DAT.
"""

import time

_RESET_INTERVAL_S = 90.0
_last_reset = 0.0

_TERMINAL_CHOPS = ('chop_pose', 'chop_hand', 'chop_face', 'chop_meta')

_COOK_EVERY_N_FRAMES = 4  # ~15Hz at 60fps project rate -- see perf note below

def onFrameStart(frame: int):
	"""
	Called at the start of each frame.

	Terminal Script CHOPs read oscin_mocap via a plain op() call (not a
	wired CHOP input), so TD's normal cook-dependency graph does not pick
	up new OSC data automatically -- force-cook them so they reflect
	latest mocap regardless of whether anything is currently demanding
	their output.

	PERF: force-cooking all 4 every frame measured ~12.5ms/frame CPU
	(childrenCPUCookTime), dropping project fps below performance.md's
	90%-of-target stop threshold. Throttled to every Nth frame instead:
	mocap-driven abstract visuals don't need 60Hz semantic updates, and
	this cuts the cost proportionally.
	"""
	global _last_reset

	if frame % _COOK_EVERY_N_FRAMES == 0:
		for name in _TERMINAL_CHOPS:
			chop = op(name)
			if chop is not None:
				chop.cook(force=True)

	# oscin_mocap has no automatic channel expiry (2000+ channels within
	# under a minute of live traffic, verified live) -- periodically wipe
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
