"""
Script POP Callbacks

me - this DAT

scriptOp - the OP which is cooking
"""

import math

# press 'Setup Parameters' in the OP to call this function to re-create 
# the parameters
def onSetupParameters(scriptOp: scriptPOP):
	"""
	Called to setup custom parameters for the Script POP.
	"""
	page = scriptOp.appendCustomPage('Custom')
	p = page.appendFloat('Value', label='Value')
	return

def onPulse(par: Par):
	"""
	Called when a custom pulse parameter is pushed.
	
	Args:
		par: The parameter that was pulsed
	"""
	return

FACE_REGIONS = [
	('eye_left', 16), ('eye_right', 16),
	('eyebrow_left', 10), ('eyebrow_right', 10),
	('lips', 40), ('nose', 24), ('oval', 36),
]  # order/sizes verified live against chop_face -- see patchdeck-known-issues #56/#60
FACE_POINTS_PER_PERSON = sum(n for _, n in FACE_REGIONS)  # 152 -> *3 floats = 456, matches chop_face


def onCook(scriptOp: scriptPOP):
	"""
	Called when the Script POP needs to cook.

	Draws CONNECTED LINE shapes, not a scattered point cloud (a plain point
	cloud from this data read as unrecognizable noise -- fixed per user
	feedback). Face renders as real per-region contour outlines (eyes,
	brows, lips, nose, oval) using chop_face's now-numerically-sorted
	per-region point order (patchdeck-known-issues #60) -- when a face is
	actually being detected; pose/hand OSC indices are not decodable
	per-landmark (#55/#56) so they each become ONE closed line loop whose
	radius is modulated by their raw per-channel values in order -- an
	honest "energy waveform ring", not a fake skeleton. Color from out_soul
	mood (same palette as X36/X37).
	"""
	stagingData = scriptPOP.createGeometryStagingData()
	stagingData.createPointAttrib(name="P")
	stagingData.createVertAttrib(name="Color", numComps=4, numMatCols=1, arrSize=0, type=AttribDataType.FLOAT32, qualifier=AttribQualifier.COLOR, defaultValue=(1, 1, 1, 1))

	positions = []
	colors = []
	strips = []

	soul = op.Gaia.op('out_soul') if hasattr(op, 'Gaia') else None
	if soul is not None:
		mood_r = soul['mood_r'].eval()
		mood_g = soul['mood_g'].eval()
		mood_b = soul['mood_b'].eval()
	else:
		mood_r, mood_g, mood_b = 0.6, 0.5, 0.9

	face = op.Gaia.op('chop_face') if hasattr(op, 'Gaia') else None
	if face is not None:
		vals = [c.eval() for c in face.chans()]
		per_person = FACE_POINTS_PER_PERSON * 3
		num_persons = len(vals) // per_person
		for p in range(num_persons):
			base = p * per_person
			offset = 0
			for region_name, npts in FACE_REGIONS:
				start = len(positions)
				for k in range(npts):
					idx = base + offset + k * 3
					if idx + 2 >= len(vals):
						break
					x, y, z = vals[idx], vals[idx + 1], vals[idx + 2]
					positions.append(((x - 0.5) * 5.0, (0.5 - y) * 5.0 + 1.0, z * 5.0))
					colors.append((1.0, 0.92, 0.85, 1.0))
				end = len(positions)
				if end - start >= 2:
					strip = list(range(start, end))
					strip.append(start)  # close the loop -- eye/brow/lips/oval are closed contours
					strips.append(strip)
				offset += npts * 3

	for chop_name, radius, y_center, base_color in (
		('chop_pose', 3.2, -1.2, (mood_r, mood_g, mood_b, 0.85)),
		('chop_hand', 2.2, 0.9, (mood_r, mood_g, mood_b, 0.85)),
	):
		chop = op.Gaia.op(chop_name) if hasattr(op, 'Gaia') else None
		if chop is None:
			continue
		chans = list(chop.chans())
		n = len(chans)
		if n < 3:
			continue
		start = len(positions)
		for i, ch in enumerate(chans):
			v = ch.eval()
			angle = (i / n) * 2.0 * math.pi
			r = radius + v * 1.2
			positions.append((math.cos(angle) * r, y_center + v * 0.4, math.sin(angle) * r))
			colors.append(base_color)
		end = len(positions)
		strip = list(range(start, end))
		strip.append(start)
		strips.append(strip)

	if not positions:
		positions = [(0.0, 0.0, 0.0)]
		colors = [(0.3, 0.3, 0.3, 1.0)]

	stagingData.appendPointAttribValues("P", positions)
	stagingData.appendVertAttribValues("Color", colors)
	for strip in strips:
		stagingData.appendPrimLineStrip(tuple(strip))
	if not strips:
		stagingData.appendPrimPoints(list(range(len(positions))))

	scriptOp.buildGeometry(stagingData)
	return

def onGetCookLevel(scriptOp: scriptPOP) -> CookLevel:
	"""
	Sets the scriptOp's cook level, the conditions necessary to cause a cook.

	Return one of the following:
		CookLevel.AUTOMATIC - inputs changed and output being used. 
							 TD default behavior.
		CookLevel.ON_CHANGE - inputs changed, output used or not.
		CookLevel.WHEN_USED - every frame when output is being used
		CookLevel.ALWAYS - every frame
	"""

	return CookLevel.WHEN_USED
