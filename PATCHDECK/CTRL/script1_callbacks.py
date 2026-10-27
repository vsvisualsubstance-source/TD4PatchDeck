def onCook(scriptOp):
    # Usa l'input diretto (il cavo collegato) invece di op('null1')
    if len(scriptOp.inputs) > 0:
        src = scriptOp.inputs[0]
    else:
        # Se il cavo è scollegato, resettiamo tutto a 0 per sicurezza
        scriptOp.clear()
        scriptOp.appendChan('ch1n59')[0] = 0
        scriptOp.appendChan('ch1n60')[0] = 0
        return

    # --- 1. Leggi lo stato di input precedente (dal frame prima) ---
    # fetch/store vanno su parent(), non su scriptOp stesso: chiamarli
    # sull'op che sta cooking in quel momento crea un cook dependency loop
    # (verificato: la stessa chiamata su parent() e' pulita).
    prev_input_state = parent().fetch('prev_input_state', {})

    # --- 2. Rileva i "click" (edge detection) ---
    click_59 = False
    click_60 = False

    current_input_state = {}
    for ch in src.chans():
        current_input_state[ch.name] = ch.eval() > 0.5

    all_channel_names = set(prev_input_state.keys()) | set(current_input_state.keys())

    for name in all_channel_names:
        current_val = current_input_state.get(name, False)
        prev_val = prev_input_state.get(name, False)

        if current_val != prev_val:
            # Reagiamo solo alla pressione (0->1), ignorando il rilascio
            if current_val:
                if 'n59' in name:
                    click_59 = True
                elif 'n60' in name:
                    click_60 = True

    # Salva lo stato corrente per il prossimo frame
    parent().store('prev_input_state', current_input_state)

    # --- 3. Applica la logica Toggle allo stato di output normalizzato ---
    state_59 = parent().fetch('state_59', 0)
    state_60 = parent().fetch('state_60', 0)

    if click_59:
        state_59 = 1 - state_59
        if state_59 == 1:
            state_60 = 0

    if click_60:
        state_60 = 1 - state_60
        if state_60 == 1:
            state_59 = 0

    parent().store('state_59', state_59)
    parent().store('state_60', state_60)

    # --- 4. Scrivi l'output pulito e normalizzato ---
    scriptOp.clear()
    scriptOp.appendChan('ch1n59')[0] = state_59
    scriptOp.appendChan('ch1n60')[0] = state_60
