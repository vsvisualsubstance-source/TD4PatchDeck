"""
PopMenu callbacks

Callbacks always take a single argument, which is a dictionary
of values relevant to the callback. Print this dictionary to see what is
being passed. The keys explain what each item is.

PopMenu info keys:
	'cell': either cell id or -1 for no cell
	'item': the item label in the menu list
	'row': the row from the wired dat input, if applicable
	'details': details provided by object that caused menu to open
"""

def onSelect(info):
	"""
	User selects a menu option
	"""
	debug('test')

def onRollover(info):
	"""
	Mouse rolled over an item
	"""

def onOpen(info):
	"""
	Menu opened
	"""

def onClose(info):
	"""
	Menu closed
	"""

def onMouseDown(info):
	"""
	Item pressed
	"""

def onMouseUp(info):
	"""
	Item released
	"""

def onClick(info):
	"""
	Item pressed and released
	"""
	debug('info')

def onLostFocus(info):
	"""
	Menu lost focus
	"""