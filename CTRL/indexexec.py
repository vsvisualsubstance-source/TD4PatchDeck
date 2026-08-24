# ------------------------------------------------
# CHOP Execute DAT - Deck Loading Logic
# Gestisce il caricamento su Deck A/B quando i tasti modificatori sono premuti
# ------------------------------------------------

def onOffToOn(channel, sampleIndex, val, prev):
    raw_idx = channel.index
    if raw_idx < 0 or raw_idx >= 24:
        return

    # Mapping Hardware: Invertiamo le righe (Bottom-Up -> Top-Down)
    row = raw_idx // 8
    col = raw_idx % 8
    button_idx = ((2 - row) * 8) + col

    # Riferimenti
    led_op = op('/PATCHDECK/CTRL/led_controller')
    deck_ctrl = op('/PATCHDECK/CTRL/select_deck')
    midi_table = op('/PATCHDECK/UI/MAIN_INTERFACE/MIDI_status')

    if not led_op or not hasattr(led_op.ext, 'PATCHDECKCTRLledcontroller1'):
        return
        
    led_ctrl = led_op.ext.PATCHDECKCTRLledcontroller1

    if not led_ctrl or not deck_ctrl or not midi_table:
        return

    # --- AUTO-SYNC OFFSET ---
    # Leggiamo la pagina direttamente dalla UI per essere sicuri al 100%
    # Questo bypassa qualsiasi errore di sincronizzazione precedente
    tabs = op('/PATCHDECK/UI/MAIN_INTERFACE/folderTabs')
    current_page = 0
    if tabs:
        # Cerca il parametro corretto (Value0, Menuindex, ecc.)
        for p_name in ['Value0', 'Menuindex', 'Value', 'value']:
            if hasattr(tabs.par, p_name):
                current_page = int(getattr(tabs.par, p_name))
                break
    
    # Calcoliamo l'offset reale basato sulla pagina UI (24 patch per pagina)
    real_offset = current_page * 24
    
    # Aggiorniamo il controller per correggere eventuali errori visivi (LED)
    if led_ctrl.ui_offset != real_offset:
        led_ctrl.setUIoffset(real_offset)

    # Verifica se i tasti Deck sono premuti (canali normalizzati ch1n59/ch1n60)
    is_deck_a = False
    is_deck_b = False

    if deck_ctrl:
        # Fix: usa iterazione diretta per evitare errori su chanNames
        for c in deck_ctrl.chans():
            if c.name == 'ch1n59' and c.eval() > 0.5:
                is_deck_a = True
            if c.name == 'ch1n60' and c.eval() > 0.5:
                is_deck_b = True

    # Se nessun deck è selezionato, usiamo la griglia per il Cook Toggle (Comportamento Standard)
    if not is_deck_a and not is_deck_b:
        led_ctrl.toggleCook(button_idx)
        return

    # Calcola numero patch reale
    patch_num = real_offset + button_idx + 1
    
    # DEBUG: Controlliamo i valori calcolati
    print(f"[GRID] Raw={raw_idx} | Btn={button_idx} | Page={current_page} | Offset={real_offset} | -> Patch={patch_num}")

    # Esegui caricamento
    # I patch su Deck A/B sono sempre garantiti attivi (allowCooking=True),
    # anche se erano stati spenti in precedenza, e non contano nel limite
    # dei 4 slot extra gestito da toggleCook/releaseFromExtra.
    patch_comp = op(f'/PATCHDECK/PATCHES/X{patch_num}')

    if is_deck_a:
        midi_table[1, 0].val = str(patch_num)
        if patch_comp:
            patch_comp.allowCooking = True
            led_ctrl.releaseFromExtra(patch_num)
        print(f"[DECK] ✅ Patch {patch_num} → Deck A")
    
    if is_deck_b:
        midi_table[1, 1].val = str(patch_num)
        if patch_comp:
            patch_comp.allowCooking = True
            led_ctrl.releaseFromExtra(patch_num)
        print(f"[DECK] ✅ Patch {patch_num} → Deck B")

    # Aggiorna LED
    led_ctrl.refreshAll()