# me - this DAT
# 
# frame - the current frame
# state - True if the timeline is paused
# 
# Make sure the corresponding toggle is enabled in the Execute DAT.

def onStart():
	return

def onCreate():
	return

def onExit():
	return

def onFrameStart(frame):

	curTime = absTime.seconds;
	lastFrameTime = me.fetch("lastFrameTime", curTime);

	if parent().par.Autorotate and not parent.Camera.TransformActive:
	
		frameTime = curTime - lastFrameTime;
	
		parent.Camera.AutoRotate(frameTime);
		
	if parent().par.Keysactive and not parent.Camera.TransformActive:
		
		frameTime = curTime - lastFrameTime;
		parent.Camera.DoKeyMovement(frameTime);
	

	me.store("lastFrameTime", curTime);

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

	