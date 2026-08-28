# Toggles between the Master (POST_FX-mixed) output and Direct NDI mode
# (cache1/cache2 -> ndiout1/ndiout2). Fully stops POST_FX from cooking
# (Cooking flag, not just bypass -- POST_FX is a COMP so its 40 internal
# ops truly stop touching the GPU, not just passthrough), bypasses
# crossfade and MASTER_DIM (plain TOPs, no Cooking flag available), and
# disables the combined NDI_OUT feed. preview_A/preview_B keep cooking
# regardless: cache1/cache2 (and therefore ndiout1/ndiout2) depend on them
# either way.

def onValueChange(par, prev):
	if par.name != 'Directndimode':
		return

	direct_mode = bool(par.eval())

	post_fx = par.owner
	post_fx.bypass = direct_mode
	post_fx.allowCooking = not direct_mode

	patches = post_fx.parent()

	crossfade = patches.op('crossfade')
	if crossfade is not None:
		crossfade.bypass = direct_mode

	master_dim = patches.op('MASTER_DIM')
	if master_dim is not None:
		master_dim.bypass = direct_mode

	ndi_out = patches.op('NDI_OUT')
	if ndi_out is not None:
		ndi_out.par.active = not direct_mode

	return
