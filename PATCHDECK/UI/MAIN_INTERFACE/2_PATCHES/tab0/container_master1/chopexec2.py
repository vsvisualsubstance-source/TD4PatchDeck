def onOffToOn(channel, sampleIndex, val, prev):
    # Gestione Stato Locale
    current_deck = me.parent().fetch('current_deck', 0) # 0=A, 1=B

    # Pulsanti Deck (dalla UI)
    if channel.name == 'ch1n60' and val > 0:   # Deck A
        current_deck = 0
        me.parent().store('current_deck', current_deck)
        print("UI Deck selezionato: A")
        return

    if channel.name == 'ch1n59' and val > 0:   # Deck B
        current_deck = 1
        me.parent().store('current_deck', current_deck)
        print("UI Deck selezionato: B")
        return

    # Pulsanti video
    if val > 0:
        idx = parent(1).digits  # o channel.index, a seconda di come vuoi leggere l'indice
        
        # Aggiorna indice
        # Usa percorso assoluto per sicurezza (come OLDUI)
        # Percorso: /PATCHDECK/UI/MAIN_INTERFACE/2_PATCHES/STATE
        state_path = '/PATCHDECK/UI/MAIN_INTERFACE/2_PATCHES/STATE'
        
        if op(f'{state_path}/selected_index'):
            op(f'{state_path}/selected_index').par.value0.val = idx
            op(f'{state_path}/selected_desk').par.value0.val = current_deck
            
        # Aggiorna MIDI_status per Deck B (Colonna 1)
        # Fondamentale per il feedback LED (Verde/Arancione)
        midi_status = op('/PATCHDECK/UI/MAIN_INTERFACE/MIDI_status')
        if midi_status:
            midi_status[1, 1] = idx
            
        print(f"Caricato indice {idx} su Deck {'B' if current_deck == 1 else 'A'}")
