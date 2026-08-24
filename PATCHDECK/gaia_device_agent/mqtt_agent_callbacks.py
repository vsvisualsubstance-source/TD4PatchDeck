"""
MQTT Client DAT Callbacks

me - this DAT
"""

def onConnect(dat: mqttclientDAT):
	"""
	Called when MQTT connection is established.
	
	Args:
		dat: The MQTT Client DAT
	"""
	op('gaia_device_agent').module.on_connect(dat)
	return

def onConnectFailure(dat: mqttclientDAT, msg: str):
	"""
	Called when MQTT connection fails.
	
	Args:
		dat: The MQTT Client DAT
		msg: Reason for failure
	"""
	op('gaia_device_agent').module.on_connect_failure(msg)
	return

def onConnectionLost(dat: mqttclientDAT, msg: str):
	"""
	Called when current MQTT connection is lost.
	
	Args:
		dat: The MQTT Client DAT
		msg: Reason for failure
	"""
	op('gaia_device_agent').module.on_connection_lost(msg)
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
	op('gaia_device_agent').module.on_message(topic, payload)
	return
