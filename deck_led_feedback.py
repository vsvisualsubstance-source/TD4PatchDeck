# ------------------------------------------------
# CHOP Execute DAT - Deck LED Feedback
# Monitora lo stato logico dei Deck e aggiorna i LED
# Collegare all'uscita di script1_callbacks (o al Null 'select_deck')
# ------------------------------------------------

def onValueChange(channel, sampleIndex, val, prev):
    # Riferimento al controller per accedere all'oggetto APC
    led_ctrl_op = op('/PATCHDECK/CTRL/led_controller')
    if not led_ctrl_op or not hasattr(led_ctrl_op.ext, 'PATCHDECKCTRLledcontroller1'):
        return
        
    apc = led_ctrl_op.ext.PATCHDECKCTRLledcontroller1.apc
    if not apc:
        return

    # Mappa canali a note MIDI
    # ch1n59 -> Deck A
    # ch1n60 -> Deck B
    note = -1
    if 'n59' in channel.name:
        note = 58 # Corretto: Device Left (era 59)
    elif 'n60' in channel.name:
        note = 59 # Corretto: Device Right (era 60)
        
    if note != -1:
        # Invia comando MIDI
        # Canale 1 è standard per i pulsanti globali su APC40MK2
        # Velocity 1 = Acceso, 0 = Spento
        velocity = 1 if val > 0.5 else 0
        apc.midiout.sendNoteOn(1, note, velocity)