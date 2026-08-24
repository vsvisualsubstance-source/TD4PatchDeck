"""
MQTT Client DAT Callbacks

me - this DAT
"""

import json
import time

TOPIC_DATS = {
	'gaia/td/canvas': 'topic_canvas',
	'gaia/brain/state': 'topic_brainstate',
	'gaia/brain/dream': 'topic_dream',
}

def onConnect(dat: mqttclientDAT):
	"""
	Called when MQTT connection is established.
	
	Args:
		dat: The MQTT Client DAT
	"""
	parent.Gaia.par.Connectionstatus = 'connected'
	dat.subscribe(list(TOPIC_DATS.keys()))
	return

def onConnectFailure(dat: mqttclientDAT, msg: str):
	"""
	Called when MQTT connection fails.
	
	Args:
		dat: The MQTT Client DAT
		msg: Reason for failure
	"""
	parent.Gaia.par.Connectionstatus = 'connect failed: %s' % msg
	return

def onConnectionLost(dat: mqttclientDAT, msg: str):
	"""
	Called when current MQTT connection is lost.
	
	Args:
		dat: The MQTT Client DAT
		msg: Reason for failure
	"""
	parent.Gaia.par.Connectionstatus = 'connection lost: %s' % msg
	return

def onSubscribe(dat: mqttclientDAT):
	"""
	Called when the subscribe call succeeds and is sent to the server.
	
	Args:
		dat: The MQTT Client DAT
	"""
	return

def onSubscribeFailure(dat: mqttclientDAT, msg: str):
	"""
	Called when subscription request fails.
	
	Args:
		dat: The MQTT Client DAT
		msg: Reason for failure
	"""
	parent.Gaia.par.Connectionstatus = 'subscribe failed: %s' % msg
	return

def onUnsubscribe(dat: mqttclientDAT):
	"""
	Called when the unsubscribe call succeeds and is sent to the server.
	
	Args:
		dat: The MQTT Client DAT
	"""
	return

def onUnsubscribeFailure(dat: mqttclientDAT, msg: str):
	"""
	Called when unsubscription request fails.
	
	Args:
		dat: The MQTT Client DAT
		msg: Reason for failure
	"""
	return

def onPublish(dat: mqttclientDAT, topic: str):
	"""
	Called when the publish call succeeds and is sent to the server.
	
	Args:
		dat: The MQTT Client DAT
		topic: Topic name of the published message
	"""
	return

def onMessage(dat: mqttclientDAT, topic: str, payload: str, qos: int,
			  retained: bool, dup: bool):
	"""
	Called when new content is received from server.
	
	Args:
		dat: The MQTT Client DAT
		topic: Topic name of the incoming message
		payload: Payload of the incoming message
		qos: QoS flag of the incoming message
		retained: Retained flag of the incoming message
		dup: Dup flag of the incoming message
	"""
	dat_name = TOPIC_DATS.get(topic)
	if dat_name is None:
		return

	# payload arrives as bytes at runtime despite the str type hint above
	raw = payload.decode('utf-8', errors='replace') if isinstance(payload, bytes) else payload

	try:
		obj = json.loads(raw)
		text = json.dumps(obj, indent=2)
	except (json.JSONDecodeError, TypeError, ValueError):
		text = raw

	target = op(dat_name)
	if target is not None:
		target.text = text

	parent.Gaia.par.Lastmessage = '%s @ %s' % (topic, time.strftime('%H:%M:%S'))
	return
