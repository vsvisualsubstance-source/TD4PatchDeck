# ------------------------------------------------
# CHOP Execute DAT - Panic & Resume
# Panic: Rec (103) + Session (94)
# Resume: Start (92)
# ------------------------------------------------

def onOffToOn(channel, sampleIndex, val, prev):
    # Riferimento al CHOP di input
    chop = channel.owner.inputs[0]
    if not chop:
        return

    # --- RESUME LOGIC (Start - 92) ---
    if 'n92' in channel.name:
        print("[RESUME] ▶️ Start premuto: Riattivazione sistemi...")
        
        # Riattiva cooking sui contenitori top-level disabilitati da nopanic
        targets = ['/PATCHDECK/PATCHES', '/PATCHDECK/PATCHES/POST_FX']
        for path in targets:
            comp = op(path)
            if comp:
                comp.allowCooking = True
                print(f"[RESUME] ✅ Cooking riattivato per {path}")

        # IMPORTANTE: non riaccendere tutte le 36 patch (rischio GPU memory
        # esaurita, causa nota di FPS basso). Rispettiamo lo stesso limite di
        # max 6 patch attive (Deck A + Deck B + fino a 4 extra) usato da
        # led_controller.toggleCook(): riaccendiamo solo Deck A, Deck B, e
        # quelle eventualmente ancora in extra_active_patches.
        midi_table = op('/PATCHDECK/UI/MAIN_INTERFACE/MIDI_status')
        led_op = op('/PATCHDECK/CTRL/led_controller')
        to_reactivate = set()
        if midi_table:
            for col in (0, 1):
                val = str(midi_table[1, col].val or "0")
                if val:
                    to_reactivate.add(val)
        if led_op and hasattr(led_op.ext, 'PATCHDECKCTRLledcontroller1'):
            ctrl = led_op.ext.PATCHDECKCTRLledcontroller1
            for n in ctrl._getExtraActive():
                to_reactivate.add(str(n))

        patches_comp = op('/PATCHDECK/PATCHES')
        if patches_comp:
            for patch_num in to_reactivate:
                c = op(f'/PATCHDECK/PATCHES/X{patch_num}')
                if c:
                    c.allowCooking = True
            print(f"[RESUME] ✅ Cooking riattivato per: {sorted(to_reactivate)} (Deck A/B + extra)")
        return

    # --- PANIC LOGIC (Rec + Session) ---
    # Leggi stato dei due pulsanti
    try:
        rec = chop['ch1n103'][0]
        session = chop['ch1n94'][0]
    except:
        return # Canali non trovati

    # Se entrambi sono premuti (AND logico)
    if rec > 0.5 and session > 0.5:
        print("[PANIC] 🚨 Combinazione REC + SESSION rilevata!")
        
        # Cerca ed esegui lo script nopanic
        script = op('nopanic')
        if not script:
            # Fallback se non è nella stessa rete (adatta il percorso se serve)
            script = op('/PATCHDECK/CTRL/nopanic')
            
        if script:
            script.run()
        else:
            print("[PANIC] ❌ Script 'nopanic' non trovato")
