import apc40mk2

# ------------------------------------------------
# INIT APC40 + LED (stabile)
# ------------------------------------------------
# Questo Text DAT deve essere eseguito all'avvio
# ------------------------------------------------

# 1. Inizializza APC40
apc = apc40mk2.APC40MK2(op('midiout1'))
apc.mode.set_device_mode(1) # 0=Generic, 1=Ableton (Full LED Control)
print("[APC] Modalità 1 (Ableton) attiva")

# 2. Collega l'extension LED
led_ctrl = op('/PATCHDECK/CTRL/led_controller').ext.PATCHDECKCTRLledcontroller1
led_ctrl.apc = apc  # deve essere fatto prima di refreshAll()/reconcileCooking()

# 3. Riconcilia lo stato di cooking (spegne eventuali patch accese fuori dal
#    budget Deck A/B + extra_active_patches, per qualunque via) e aggiorna
#    tutti i LED di conseguenza (reconcileCooking chiama refreshAll internamente)
led_ctrl.reconcileCooking()
print("[INIT] ✅ Cooking riconciliato e LED aggiornati")
