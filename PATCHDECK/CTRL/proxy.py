# ------------------------------------------------
# CHOP Execute DAT - APC40 Controller Proxy
# Gestione SOLO Cook Toggle (con protezione Deck)
# Compatibile con UI multipagina (led_ctrl.ui_offset)
# ------------------------------------------------

apc_buttons = 24  # numero di pulsanti fisici APC per blocco
led_ctrl_op = '/PATCHDECK/CTRL/led_controller'

def onValueChange(channel, sampleIndex, val, prev):
    # ------------------------------
    # 0. MAPPING DIRETTO (Indice CHOP -> Indice Logico)
    # ------------------------------
    # Torniamo alla logica semplice: l'ordine dei canali nel CHOP comanda.
    # Questo risolve immediatamente il problema dei PAD traslati.
    button_idx = channel.index

    if button_idx < 0 or button_idx >= apc_buttons:
        return

    # ------------------------------
    # LED Controller (source of truth)
    # ------------------------------
    led_op = op(led_ctrl_op)
    if not led_op:
        return
    
    # Verifica sicura dell'extension
    if not hasattr(led_op.ext, 'PATCHDECKCTRLledcontroller1'):
        return
        
    led_ctrl = led_op.ext.PATCHDECKCTRLledcontroller1
    if not led_ctrl:
        return

    # Filtro Pressione: Reagiamo solo quando il tasto viene premuto (val > 0).
    if val <= 0:
        return

    # ------------------------------
    # 2. COOK TOGGLE LOGIC
    # ------------------------------
    led_ctrl.toggleCook(button_idx)
