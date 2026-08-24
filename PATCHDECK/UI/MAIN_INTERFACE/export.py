ctrl = op("control_ui")

def onValueChange(channel, sampleIndex, val, prev):
	ctrl.par[channel.name]=channel
	return
	