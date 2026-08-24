
# The function below is called when any passed values have changed.
# Be sure to turn on the related parameter in the CHOP to retrieve these values.
#
# me - this DAT
# renderPickChop - the connected Render Pick CHOP
#
# event - a named tuple with the fields listed below.
# eventPrev - a event holding the previous values.
#
#	u			- The selection u coordinate.			(float)
#	v			- The selection v coordinate.			(float)
#	select		- True when a selection is ongoing.		(bool)
#	selectStart	- True at the start of a selection.		(bool)
#	selectEnd	- True at the end of a selection.		(bool)
#	pickOp		- Currently picked operator.			(OP)
#	pos			- 3D position of picked point.			(Position)
#	texture		- Texture coordinate of picked point.	(Position)
#	color		- Color of picked point.				(4-tuple)
#	normal		- Geometry normal of picked point.		(Vector)
#	depth		- Post projection space depth.			(float)
#	instanceId	- Instance ID of the object.			(int)

def onEvent(renderPickChop, event, eventPrev):
	return

	