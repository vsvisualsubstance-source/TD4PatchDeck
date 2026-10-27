import gc # Per pulizia RAM

print('[PANIC-GPU] 🚨 START')

# 1. Stop time (Commentato: spesso è meglio lasciare il tempo attivo per la UI)
# root.time.play = 0

# 2. Close Windows, ma non PERFORM: chiudere la finestra di show fa uscire
# TD da Perform Mode (nessuna finestra su cui renderizzarlo).




# 4. Disable Cooking & Pause Movies
targets = ['/PATCHDECK/PATCHES', '/PATCHDECK/OUTPUT', '/PATCHDECK/PATCHES/POST_FX']

# Pause all movies inside PATCHDECK to save VRAM/Decode
deck = op('/PATCHDECK')
if deck:
    for m in deck.findChildren(type=moviefileinTOP):
        m.par.play = 0
        m.unload() # FORCE VRAM RELEASE: Scarica il file dalla GPU
        
    # Pulisce anche i Cache TOP che occupano molta memoria
    for c in deck.findChildren(type=cacheTOP):
        c.par.reset.pulse()
        
    print('[PANIC-GPU] Movies unloaded & Caches cleared')

# --- RESET STATO (Clean Start) ---
# 1. Resetta assegnazione Deck (Nessun deck selezionato)
midi_status = op('/PATCHDECK/UI/MAIN_INTERFACE/MIDI_status')
if midi_status:
    midi_status[1, 0] = 0
    midi_status[1, 1] = 0

# 2. Spegne tutte le patch singolarmente per evitare che ripartano al Resume
patches_comp = op('/PATCHDECK/PATCHES')
if patches_comp:
    for c in patches_comp.children:
        if c.isCOMP:
            c.allowCooking = False

# 3. Svuota il warm pool (le patch sono appena state spente tutte)
led_op = op('/PATCHDECK/CTRL/led_controller')
if led_op:
    led_op.store('warm_patches', [])

for path in targets:
    comp = op(path)
    if not comp: continue

    # Disabilitare il Parent ferma automaticamente il cooking dei figli
    if comp.isCOMP:
        comp.allowCooking = False
    print(f'[PANIC-GPU] Cooking disabled for {path} and children')

# 6. RAM Garbage Collection (Pulisce memoria Python inutilizzata)
n = gc.collect()
print(f'[PANIC-GPU] RAM Garbage Collected ({n} objects)')

# 7. Relaunch Init
try:
    if op('init_apc40'):
        op('init_apc40').run()
        print('[PANIC-GPU] Init script relaunched')
except Exception as e:
    print(f'[PANIC-GPU][WARN] Init failed: {e}')

print('[PANIC-GPU] ✅ DONE')
