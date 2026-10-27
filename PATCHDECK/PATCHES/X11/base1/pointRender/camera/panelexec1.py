# me is this DAT.
# 
# panelValue is the PanelValue object that changed.
# 
# Make sure the corresponding toggle is enabled in the Panel Execute DAT.

mouseButtons = { 
	"left" : "lselect",
	"right" : "rselect",
	"middle" : "mselect"
};

# match the key menu values to the panel button code
def matchMouse( mouse, panelVal ):
	return mouseButtons.get( str(mouse), "" ) == panelVal;
	
# match the modifier menu values to the panel vutton
def matchModifier( mod, panel ):

	if mod == "none":
		return True;
	
	elif mod == "alt":
		return panel.alt;
		
	elif mod == "ctrl":
		return panel.ctrl;
		
	elif mod == "shift":
		return panel.shift;
		
	else:
		return False;

# map the panel action to a camera action
def getCameraAction( panelValue ):

	if matchMouse( parent.Camera.par.Tumblemouse, panelValue.name ) and \
		matchModifier( parent.Camera.par.Tumblemod, panelValue.owner.panel ):
		return "tumble";
		
	elif matchMouse( parent.Camera.par.Dollymouse, panelValue.name ) and \
		matchModifier( parent.Camera.par.Dollymod, panelValue.owner.panel ):
		return "dolly";
	
	elif matchMouse( parent.Camera.par.Panmouse, panelValue.name ) and \
		matchModifier( parent.Camera.par.Panmod, panelValue.owner.panel ):
		return "pan";

	return None;

# start the camera movement when the button is pressed
def offToOn(panelValue):
	valueName = panelValue.name
	panelOwner = panelValue.owner.panel

	u = panelOwner.u
	v = panelOwner.v
	
	mode = parent.Camera.par.Navigationmode;
	
	action = getCameraAction( panelValue );
	
	if not (action is None):
		parent.Camera.StartTransform(action=action, u=u, v=v, mode=mode);
		
	return

# move the camera while the button is pressed
def whileOn(panelValue):
	valueName = panelValue.name
	panelOwner = panelValue.owner.panel

	u = panelOwner.u
	v = panelOwner.v

	# speed adjustments
	speedMult = 1.0;
	if parent.Camera.GetAction() == "tumble":
		speedMult = parent.Camera.par.Tumblemult;

	elif parent.Camera.GetAction() == "dolly":
		speedMult = parent.Camera.par.Dollymult;
		
	elif parent.Camera.GetAction() == "pan":
		speedMult = parent.Camera.par.Panmult;
	
	# do the transform
	parent.Camera.Transform(u=u, v=v, scaler=speedMult)

	return

# make sure the camera movement has ended	
def onToOff(panelValue):

	parent.Camera.EndTransform();
	
	# make sure keyboard movement is stopped when the panel
	# loses focus since we won't get the key release messages
	if panelValue.name == "focusselect":
		parent.Camera.ResetKeys();
	
	return;

# handle mouse wheel movements, they start and end in one action	
def valueChange(panelValue):

	valueName = panelValue.name
	panelOwner = panelValue.owner.panel

	uv = panelValue.owner.locateMouseUV();

	if valueName == 'wheel' and (panelOwner.wheel.val != 0):
	
		mode = parent.Camera.par.Navigationmode;
	
		parent.Camera.StartTransform(action="wheel", u=uv[0], v=uv[1], mode=mode);
	
		parent.Camera.Transform( du=panelOwner.wheel * 0.2, dv=0, scaler=1)
	
		parent.Camera.EndTransform();
	
	return