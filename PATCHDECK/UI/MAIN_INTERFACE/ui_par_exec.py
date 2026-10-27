def onValueChange(par, val, prev):
    # Riferimento al controller LED
    led_op = op('/PATCHDECK/CTRL/led_controller')
    if not led_op:
        print("[UI] ❌ OP /PATCHDECK/CTRL/led_controller non trovato")
        return
    
    # Verifica se l'extension è caricata correttamente
    if not hasattr(led_op.ext, 'PATCHDECKCTRLledcontroller1'):
        print("[UI] ❌ Extension PATCHDECKCTRLledcontroller1 non trovata su led_controller. Verifica 'Extension Object' sul COMP.")
        return

    led_ctrl = led_op.ext.PATCHDECKCTRLledcontroller1
    if not led_ctrl:
        print("[UI] ❌ Oggetto Extension vuoto/None")
        return
    
    # Usa il metodo setPage per garantire che il calcolo sia fatto internamente (x24)
    # Questo evita errori di calcolo esterni
    print(f"[UI] 📄 Cambio Pagina UI: Index={val} -> Aggiornamento LED")
    led_ctrl.setPage(int(val))