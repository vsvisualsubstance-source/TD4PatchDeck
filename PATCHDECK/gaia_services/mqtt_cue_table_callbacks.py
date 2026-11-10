"""
Tabella delle patch della timeline video pubblicata dalla Plancia
(GAIA_INTERFACE, OPS 56). Il topic e' retained: arriva a ogni connessione.
"""

CUE_TABLE_TOPIC = 'gaia/show/video/cue_table'


def onConnect(dat):
	dat.subscribe(CUE_TABLE_TOPIC, qos=1)
	return


def onMessage(dat, topic, payload, qos, retained, dup):
	if topic == CUE_TABLE_TOPIC:
		op('../CTRL/led_controller').ext.PATCHDECKCTRLledcontroller1.applyCueTable(payload)
	return
