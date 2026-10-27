# ------------------------------------------------
# CHOP Execute DAT - Bank/Page Navigation
# Pulsanti: Bank Left (97), Bank Right (98)
# ------------------------------------------------

def onOffToOn(channel, sampleIndex, val, prev):
    name = channel.name
    
    # Lista di possibili nomi del parametro
    candidate_names = ['Value0', 'Menuindex', 'Value', 'value', 'Index']
    
    target_par = None
    tabs_op = None

    # Cerca il contenitore dei Tab (Assicurati che questo sia il percorso definitivo)
    outer_tabs = op('/PATCHDECK/UI/MAIN_INTERFACE/folderTabs')
    if outer_tabs:
        for p_name in candidate_names:
            if hasattr(outer_tabs.par, p_name):
                target_par = getattr(outer_tabs.par, p_name)
                tabs_op = outer_tabs
                break

    if target_par is None:
        print(f"[BANK] ❌ Nessun parametro valido trovato tra {candidate_names}")
        # Debug dell'esterno (che abbiamo saltato nel log precedente)
        if outer_tabs:
            print(f"👉 Parametri Custom su {outer_tabs.path}: {[p.name for p in outer_tabs.customPars]}")
        return

    # Leggi valore attuale pagina (0, 1, 2...)
    try:
        current_val = int(target_par.eval())
    except:
        current_val = 0
    
    new_val = current_val
    if 'n98' in name:
        new_val = current_val - 1 # Indietro (Invertito)
    elif 'n97' in name:
        new_val = current_val + 1 # Avanti (Invertito)
       
    target_par.val = new_val
