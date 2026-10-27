# ------------------------------------------------
# CHOP Execute DAT - Cambio tab UI
# Collegato al select2 della UI
# Aggiorna l'offset interno dell'extension
# ------------------------------------------------

_last_menu_index = -1  # memorizza ultimo tab selezionato

def updateTabOffset():
    global _last_menu_index

    select2 = op('/PATCHDECK/UI/MAIN_INTERFACE/2_PATCHES/select2')
    if not select2:
        print("[TAB] ❌ select2 non trovato")
        return

    try:
        menu_index = int(select2[0])
    except Exception as e:
        print(f"[TAB] ❌ menuIndex non numerico: {select2[0]}")
        return

    if menu_index == _last_menu_index:
        return
    _last_menu_index = menu_index

    print(f"[TAB] MenuIndex={menu_index}")

    led_ctrl = op('/PATCHDECK/CTRL/led_controller').ext.PATCHDECKCTRLledcontroller1
    if led_ctrl:
        led_ctrl.ui_offset = menu_index * 24  # ogni blocco UI = 24 patch
        led_ctrl.refreshAll()
        print(f"[LED] Tutti i LED aggiornati e sincronizzati per menu {menu_index}")

def onValueChange(channel, sampleIndex, val, prev):
    updateTabOffset()

# Init all'avvio
if me.time.frame == 1:
    updateTabOffset()
    print("[CHOP EXEC TAB] ✅ Sistema tab UI pronto")
