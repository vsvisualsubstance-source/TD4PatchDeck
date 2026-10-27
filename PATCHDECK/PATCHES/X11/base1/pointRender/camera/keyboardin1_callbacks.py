# me is this DAT.
# 
# dat is the DAT that recieved the key event.
# key is the name of the key attached to the event
# character is the ASCII value of the pressed key as a string
# alt is true if the alt modifier is pressed
# ctrl is true if the ctrl modifier is pressed
# shift is true if the shift modifier is pressed
# state is true if the event is a key press event
# time is the time when the event came in milliseconds

def keyEvent(dat, key, character, alt, lalt, ralt, ctrl, lctrl, rctrl, shift, lshift, rshift, state, time):

	if (key == 'h') or (key == 'n'):
		parent.Camera.Home()

	elif key == 'f':
		parent.Camera.Frame()
		
	elif key == 't':
		parent.Camera.FrameLookAt( tdu.Vector(0,-1,0), tdu.Vector(0,0,-1) );

	elif key == 'r':
		parent.Camera.FrameLookAt( tdu.Vector(-1,0,0), tdu.Vector(0,1,0) );
		
	elif key == 'l':
		parent.Camera.FrameLookAt( tdu.Vector(1,0,0), tdu.Vector(0,1,0) );
		
	# wsad qe
	elif key == 'a':
		parent.Camera.SetKeyAction("track_left", state);
	
	elif key == 'd':
		parent.Camera.SetKeyAction("track_right", state);
		
	elif key == 'w':
		parent.Camera.SetKeyAction("walk_forward", state);
		
	elif key == 's':
		parent.Camera.SetKeyAction("walk_back", state);
		
	elif key == 'q':
		parent.Camera.SetKeyAction("turn_left", state);
		
	elif key == 'e':
		parent.Camera.SetKeyAction("turn_right", state);

	return

#shortcutName is the name of the shortcut

def shortcutEvent(dat, shortcutName, time):
	return;
	