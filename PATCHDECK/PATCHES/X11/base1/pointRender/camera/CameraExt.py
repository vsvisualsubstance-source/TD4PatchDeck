TDF = op.TDModules.mod.TDFunctions # utility functions

class CameraExt():
	"""
	The CameraExt Class helps with interactively controlling a Camera COMP
	given a Container COMP with the Mouse UV Buttons Parameters for left, 
	middle and right enabled.

	Attributes
	----------
		ownerComp : OP
			Reference to the COMP this Class is initiated by.

	Methods
	-------
		StartTransform(btn=None, u=0, v=0)
			Will begin a transform depending on the mouse button pressed.
		Transform(btn=None, u=0, v=0, scaler=1)
			Applies a transform to the ArcBall depending on the mouse button pressed.
		EndTransform()
			TODO
		Reset()
			Resets the camera.
		LoadTransform(dat=None,matrix=None)
			Given a tableDAT or a tdu.Matrix() it can be used to recall a saved transformation.
		SaveTransform(dat=op('newMat'))
			Will save out the current Camera's transformation matrix to a tableDAT. If no
			TableDAT is given, the internal newMat TableDAT is being used.

	"""
	
	def __init__(self, ownerComp : OP):
		#The component to which this extension is attached
		self.ownerComp = ownerComp
		self.cameraInst = tdu.Camera()
		self.matrix = tdu.Matrix()
		
		# for tracking the change in mouse movement
		self.lastU = 0;
		self.lastV = 0;
		self.startTime = 0;
		self.spinSum = (0.0, 0.0);
		self.spinSpeed = (0.0, 0.0);
		
		self.camSpeed = (1.0, 1.0);
		
		self.keyStates = {};
		
		# navigation mode and current action
		self.mode = "viewport";
		self.action = "";

		# initialize camera to saved out transformation matrix
		matrixDAT = op('newMat')
		for i in range(4):
			for j in range(4):
				self.matrix[i,j] = float(matrixDAT[i,j])

		matCopy = tdu.Matrix(self.matrix)
		self.cameraInst.setTransform(matCopy)
		
		TDF.createProperty(self, 'Pivot', value=tdu.Vector(0,0,0));
		TDF.createProperty(self, 'PivotUV', value=(0,0));
		TDF.createProperty(self, 'TransformActive', value=False);

	def getAspect(self):
	
		if parent.Camera.par.Refpanel == None:
			return 1;
	
		aspect = op(parent.Camera.par.Refpanel).width / op(parent.Camera.par.Refpanel).height;
		
		return aspect;
		
	def getHfov(self):
	
		aspect = self.getAspect();
		fov = parent.Camera.par.fov / 180 * math.pi;
		
		if parent.Camera.par.viewanglemethod == 'horzfov':
			return fov;
			
		elif parent.Camera.par.viewanglemethod == 'vertfov':
			return fov * aspect;
		
		# todo: handle focal length/aperature
		return 45;

	# calculate a common speed mult based on the pivot distance, fov and panel aspect
	def calcCameraSpeed(self):
	
		pivotDist = (self.cameraInst.position - self.cameraInst.pivot).length();
		
		pivotWidth = pivotDist;
		pivotHeight = pivotDist;
		
		aspect = self.getAspect();
		
		if parent.Camera.par.viewanglemethod == 'horzfov':
			pivotWidth = 2.0 * pivotDist * math.tan( parent.Camera.par.fov / 2 / 180 * math.pi );
			pivotHeight = pivotWidth / aspect;
				
		elif parent.Camera.par.viewanglemethod == 'vertfov':
			pivotHeight = 2.0 * pivotDist * math.tan( parent.Camera.par.fov / 2 / 180 * math.pi );
			pivotWidth = pivotHeight * aspect;
			
		# todo: we don't handle the focal length / aperature model right now
		
		speedu = pivotWidth;
		speedv = pivotHeight;

		return speedu, speedv;
		
	# return the current coords in the render pick chop
	def getPickPos(self):
	
		pickNode = op('renderpick1');
		if pickNode['picked']:
			return tdu.Vector( pickNode['tx'], pickNode['ty'], pickNode['tz'] );
	
		return None;

	# set the pivot to the center of the viewport at the same distance as the last pivot
	def getPivotFromViewportCenter(self):
	
		pivotDist = (self.cameraInst.position - self.cameraInst.pivot).length();
		pivotDist = max(pivotDist, 0.1);
		
		pivotPos = tdu.Position(0, 0, -1 * pivotDist);
		pivotPos = self.matrix * pivotPos;
		
		return pivotPos;

	# set the pivot to the center of the viewport at the same distance as the last pivot
	def getPivotFromCursor(self, u, v):
	
		pivotDist = (self.cameraInst.position - self.cameraInst.pivot).length();
		pivotDist = max(pivotDist, 0.1);

		screenPos = tdu.Position( (u * 2) -1, (v * 2) - 1, 0 );

		projMat = me.parent().projectionInverse( self.getAspect(), 1 );
		viewProjMat = self.matrix * projMat;
		
		worldPos1 = viewProjMat * screenPos;
		
		screenPos.z = 1.0;
		worldPos2 = viewProjMat * screenPos;
		
		camDir = worldPos2 - worldPos1;
		camDir.normalize();

		camPos = tdu.Vector( self.matrix.vals[12], self.matrix.vals[13], self.matrix.vals[14] );
		
		pivotPos = camPos + (camDir * pivotDist);
		return pivotPos;
		
	# loop through all geos given in the rendertop's geometry list and find the max bounds	
	def getObjectBounds(self):
	
		renderOp = parent.Camera.par.Refrender.eval();
		if renderOp is None:
			return tdu.Vector(0), tdu.Vector(0)
				
		geoOps = renderOp.parent().ops( renderOp.par.geometry.val );
				
		bmin = None;
		bmax = None;
	
		for gop in geoOps:
		
			if getattr(gop, 'computeBounds', None) is not None:
			
				bounds = gop.computeBounds(display=True, render=True, selected=False, recurse=True);
		
				if bmin is None:
					bmin = bounds.min;
				
				if bmax is None:
					bmax = bounds.max;	
					
				for i in range(3):
					bmin[i] = min(bmin[i], bounds.min[i])
					bmax[i] = max(bmax[i], bounds.max[i])
	
		if bmin is None:
			bmin = tdu.Vector(0);
			bmax = tdu.Vector(0);
	
		return bmin, bmax;
	
	# set the pivot to the center of the selected bounding boxes
	def getPivotFromObjects(self):
	
		bmin, bmax = self.getObjectBounds();
	
		#geoComp = op( parent.Camera.par.Refgeo );
		if bmin is None:
			return tdu.Vector(0,0,0);
			
		#bounds = geoComp.computeBounds(display=True, render=True, selected=False, recurse=True);
	
		#print(bounds);
		#pivotPos = bounds[2];
		pivotPos = ( (bmin[0] + bmax[0]) / 2.0, (bmin[1] + bmax[1]) / 2.0, (bmin[2] + bmax[2]) / 2.0 );
	
		return pivotPos;

	def GetAction(self):
		return self.action;

	def StartTransform(self, action : str = None, u : float = 0, v : float = 0, mode = "cursor") -> None:

		self.lastU = float(u);
		self.lastV = float(v);
		self.startTime = absTime.seconds;
		self.spinSum = (0.0, 0.0);

		self.mode = mode;
		self.action = action;
		
		if self.action != "autotumble":
			self.spinSpeed = (0.0, 0.0);
		
		if action is None:
			return;
		
		newPivot = None;
		
		if self.action == "3d":
			newPivot = self.getPivotFromObjects();
		
		# in cursor mode, we always try to get a new pivot
		elif mode == "cursor":
		
			pickPos = self.getPickPos();
			if not (pickPos is None):
				newPivot = pickPos;
			
			else:
				newPivot = self.getPivotFromCursor(u, v);

		# if we're doing the tumble action
		elif self.action == "tumble":
						
			if mode == "object":
				newPivot = self.getPivotFromObjects();
				
		# if we're doing a dolly (either by dragging or the mouse wheel)
		elif self.action == "dolly" or self.action == "wheel":
			newPivot = self.getPivotFromCursor(u, v);
			
			
		# if nothing else set the pivot, default to the center of the screen
		if newPivot is None:
			newPivot = self.getPivotFromViewportCenter();
	
		self.cameraInst.pivot = newPivot;
		
		self.camSpeed = self.calcCameraSpeed();
		self.updatePivot();
		self.TransformActive = True;

		return

		
	def Transform(self, u : float = 0, v : float = 0, du : float = None, dv : float = None, scaler : float = 1) -> None:

		# if we're given du/dv use those (like from the mouse wheel), otherwise subtract from our last position
		deltaU = (u - self.lastU) if du is None else du;
		deltaV = (v - self.lastV) if dv is None else dv;
		
		# multiply by the camera speed and any user scaling
		moveU = deltaU * scaler;
		moveV = deltaV * scaler;
		
		# tumble/look
		if self.action == "tumble" or self.action == "autotumble":
		
			if self.mode == 'camera':
				self.cameraInst.look(moveU, moveV)
			else:
				self.cameraInst.tumble(moveU, moveV)

		# pan/track		
		elif self.action == "pan":
		
			if self.mode == 'camera':
				self.cameraInst.track(moveU * self.camSpeed[0], moveV * self.camSpeed[1])
			else:
				self.cameraInst.pan(moveU * self.camSpeed[0], moveV * self.camSpeed[1])
		
		# dolly/zoom
		elif self.action == "dolly":
		
			if self.mode == 'camera':
				self.cameraInst.walk( moveU, moveV * self.camSpeed[1] )
			else:
				self.cameraInst.dolly( (moveU * self.camSpeed[0]) + (moveV * self.camSpeed[1]) )
				
		# wheel
		elif self.action == "wheel":
			self.cameraInst.dolly( (moveU * self.camSpeed[0]) + (moveV * self.camSpeed[1]) )
			
		self.spinSum = ( self.spinSum[0] + moveU, self.spinSum[1] + moveV );
			

		self.fillMat()
		self.lastU = float(u);
		self.lastV = float(v);
		self.updatePivot();

		return
		
	# just clear the current action when the mouse is released
	def EndTransform(self) -> None:
	
		if self.action == "tumble" and parent().par.Autorotate:
			
			deltaTime = absTime.seconds - self.startTime;
			
			if deltaTime > 0:
			
				su = self.spinSum[0] if (abs(self.spinSum[0]) > 0.001) else 0;
				sv = self.spinSum[1] if (abs(self.spinSum[1]) > 0.001) else 0;
				self.spinSpeed = ( su / deltaTime, sv / deltaTime );

		self.action = None;
		self.TransformActive = False;
		
		return;
		
	def AutoRotate(self, time) -> None:
	
		if (self.spinSpeed[0] != 0) or (self.spinSpeed[1] != 0):
		
			self.StartTransform(action="autotumble", u=0, v=0, mode=self.mode);
	
			self.Transform( du=self.spinSpeed[0]*time, dv=self.spinSpeed[1]*time, scaler=1)
	
			self.EndTransform();

	# do a 3d move from a spacemouse via the joystick chop			
	def Move3D(self, translate, rotate) -> None:
	
		self.cameraInst.move3D( translate, rotate, mode="object" );
		
		self.fillMat()
		self.updatePivot();
	
		return
		
	def ResetKeys(self) -> None:
	
		self.keyStates = {};
	
		return;
		
	def SetKeyAction(self, action, newActive) -> None:
	
		if not (action in self.keyStates.keys()):	
			self.keyStates[action] = { "active" : newActive };
		
		else:
			self.keyStates[action]["active"] = newActive;
	
		return;
	
	def DoKeyMovement(self, time) -> None:
	
		moved = False;
		turnSpeed = self.ownerComp.par.Turnmult * time;
		walkSpeed = self.ownerComp.par.Walkmult * time;
	
		for action, state in self.keyStates.items():
		
			if state["active"]:
			
				if action == "track_left":
					self.cameraInst.track(-walkSpeed, 0);
				
				elif action == "track_right":
					self.cameraInst.track(walkSpeed, 0);
				
				elif action == "walk_forward":
					self.cameraInst.walk(0, walkSpeed);
				
				elif action == "walk_back":
					self.cameraInst.walk(0, -walkSpeed);
				
				elif action == "turn_left":
					self.cameraInst.walk(-turnSpeed, 0);
				
				elif action == "turn_right":
					self.cameraInst.walk(turnSpeed, 0);				
		
				
				moved = True;
				
		
		if moved:
			self.fillMat();		 
		
		return;
		
	def Reset(self) -> None:
	
		mat = tdu.Matrix();
		mat.translate(0,0,5);
		self.cameraInst.setTransform(mat);
		self.fillMat()
	
		self.cameraInst.pivot = tdu.Vector(0,0,0);
		self.updatePivot();
		
		return;
		
	def Home(self, selected : bool = False) -> None:
	
		# reset the cam to the default direction and then frame
		self.Reset();
		self.Frame(selected);
	
		return;
		
	def Frame(self, selected : bool = False) -> None:
	
		bmin, bmax = self.getObjectBounds();

		# if nothing was selected, do a full frame instead
		#if selected and tdu.Vector(bmin).length() == 0 and tdu.Vector(bmax).length() == 0:
		#	bounds = geoComp.computeBounds(display=True, render=True, selected=False, recurse=True);
				
		aspect = self.getAspect();
		hfov = self.getHfov();
	
		self.cameraInst.frameBounds( bmin, bmax, hfov, aspect );
		
		self.fillMat();
	
		return;
		
	def FrameLookAt(self, dir, up : tdu.Vector(0,1,0) ) -> None:
	
		m = tdu.Matrix();
		center = tdu.Position(0,0,0);
		target = center + dir;

		m.lookat( center, target, up );

		self.cameraInst.setTransform(m);
				
		self.Frame();
	
		return;
		
	def LoadTransform(self, dat : tableDAT = None, matrix : tdu.Matrix = None) -> None:
		"""
		Parameters
		----------
			dat : tableDAT
				An tableDAT operator reference to the tableDAT that holds the matrix to be loaded.
			matrix : tdu.MAtrix
				A tdu.Matrix object that holds the matrix to be loaded.
		"""

		if dat and dat.numRows == 4 and dat.numCols == 4:
			matrix = tdu.Matrix()
			for i in range(4):
				for j in range(4):
					matrix[i,j] = float(dat[i,j])

		self.cameraInst.setTransform(matrix)
		self.fillMat()
		return

	def SaveTransform(self, dat : tableDAT = op('newMat')) -> None:
		"""
		Parameters
		----------
			dat : tableDAT
				A tableDAT operator reference to the tableDAT where to write the current transform matrix into. 
		"""

		if dat.OPType == 'tableDAT':
			self.matrix.fillTable(dat)

	def fillMat(self):
		newMat = self.cameraInst.transform()
		self.matrix = newMat
		self.ownerComp.cook(force=True)
		newMat.fillTable(op('newMat'))
		return
	
	# return the current pivot position in 0-1 UV space	
	def updatePivot(self):
	
		self.Pivot = self.cameraInst.pivot;
		
		pivot = tdu.Position( self.Pivot );
		
		projMat = me.parent().projection( self.getAspect(), 1 );
		invViewMat = tdu.Matrix(self.matrix);
		invViewMat.invert();
		
		viewProjMat = projMat * invViewMat;

		pivot *= viewProjMat;

		self.PivotUV = ( (pivot.x / pivot.z) * 0.5 + 0.5, (pivot.y / pivot.z) * 0.5 + 0.5 );

		return;