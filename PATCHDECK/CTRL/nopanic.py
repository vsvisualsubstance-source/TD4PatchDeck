import gc # Per pulizia RAM

print('[PANIC-GPU] 🚨 START')

# 1. Stop time (Commentato: spesso è meglio lasciare il tempo attivo per la UI)
# root.time.play = 0

# 2. Exit perform & Close Windows (Solo se necessario)
if ui.performMode:
    ui.performMode = False
    print('[PANIC-GPU] Perform OFF')

# Force close all Window COMPs to stop rendering
for w in root.findChildren(type=windowCOMP):
    try:
        w.par.winclose.pulse()
    except:
        pass
print('[PANIC-GPU] Windows closed')



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
