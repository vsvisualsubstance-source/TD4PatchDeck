# me - this DAT
# 
# channel - the Channel object which has changed
# sampleIndex - the index of the changed sample
# val - the numeric value of the changed sample
# prev - the previous sample value
# 
# Make sure the corresponding toggle is enabled in the CHOP Execute DAT.

def onOffToOn(channel, sampleIndex, val, prev):
	return

def whileOn(channel, sampleIndex, val, prev):
	return

def onOnToOff(channel, sampleIndex, val, prev):
	return

def whileOff(channel, sampleIndex, val, prev):
	return

def onValueChange(channel, sampleIndex, val, prev):

	# hack to prevent jumps when initializing the device
	# regular movements shouldn't be this large
	if abs(val-prev) > 0.5:
		return

	mult = me.parent().par.Mouse3dmult;

	rotate = tdu.Vector(0,0,0);
	translate = tdu.Vector(0,0,0);

	if( channel.name == "xaxis" ):
		translate.x = val - prev;
	
	elif( channel.name == "yaxis" ):
		translate.y = -1 * (val - prev);
	
	elif( channel.name == "zaxis" ):
		translate.z = val - prev;
		
	elif( channel.name == "xrot" ):
		rotate.x = val - prev;
	
	elif( channel.name == "yrot" ):
		rotate.y = -1 * (val - prev);
	
	elif( channel.name == "zrot" ):
		rotate.z = val - prev;
	
	rotate = rotate * mult;
	translate = translate * mult;
	
	parent.Camera.StartTransform(action="3d", u=0, v=0, mode="object");
	parent.Camera.Move3D( translate, rotate ); 
	parent.Camera.EndTransform();

	return
	