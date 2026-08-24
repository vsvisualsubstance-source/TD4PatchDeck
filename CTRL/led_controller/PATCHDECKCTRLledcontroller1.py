class PATCHDECKCTRLledcontroller1:

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.apc = None
        self.num_patches = 24  # numero totale di patch
        self.ui_offset = 0      # offset corrente della UI
        self.status_table = op('/PATCHDECK/UI/MAIN_INTERFACE/MIDI_status') # Cache per performance
        self.max_extra_active = 4  # patch extra oltre Deck A/B, sempre selezionabili da Akai

    # ---------------------------
    # Imposta l'offset UI
    # ---------------------------
    def setUIoffset(self, offset):
        # --- AUTO-RIPARAZIONE ---
        # Se qualche vecchio script invia 28 (vecchio layout), lo forziamo a 24.
        if offset == 28:
            print("[CTRL] ⚠️ Rilevato offset 28 (Legacy). Correzione forzata a 24.")
            offset = 24
        
        self.ui_offset = offset
        print(f"[CTRL] Offset impostato a: {self.ui_offset}")
        self.refreshAll()

    # ---------------------------
    # Imposta Pagina (Metodo Sicuro)
    # ---------------------------
    def setPage(self, page_index):
        # Calcola l'offset internamente usando il valore corretto (24)
        safe_offset = page_index * 24
        self.setUIoffset(safe_offset)

    # ---------------------------
    # Navigazione Pagine (Bank Select)
    # ---------------------------
    def changePage(self, direction):
        """Cambia pagina (offset) di +/- 24 patch"""
        step = 24
        new_offset = self.ui_offset + (direction * step)

        # 1. Controllo Limite Inferiore
        if new_offset < 0:
            return # Siamo già all'inizio

        # 2. Controllo Limite Superiore (esiste la patch?)
        # Cerchiamo se esiste la prima patch della nuova pagina (es. X25)
        next_patch_num = new_offset + 1
        if direction > 0:
            if not op(f'/PATCHDECK/PATCHES/X{next_patch_num}'):
                print(f"[CTRL] ⚠️ Nessuna patch trovata oltre {self.ui_offset + 24}")
                return

        # 3. Applica Modifica
        self.ui_offset = new_offset
        print(f"[CTRL] 📄 Cambio Pagina → Offset {self.ui_offset}")
        
        self.refreshAll()

    # ---------------------------
    # Gestione slot "extra active" (oltre Deck A/B, max self.max_extra_active)
    # ---------------------------
    def _isOnDeck(self, patch_num):
        table = self.status_table
        if not table:
            return False
        deck_a = str(table[1, 0].val or "0")
        deck_b = str(table[1, 1].val or "0")
        return str(patch_num) in (deck_a, deck_b)

    def _getExtraActive(self):
        return list(self.ownerComp.fetch('extra_active_patches', []))

    def _setExtraActive(self, patches):
        self.ownerComp.store('extra_active_patches', list(patches))

    def releaseFromExtra(self, patch_num):
        """Rimuove patch_num dal pool extra-active (es. quando finisce su un Deck,
        dove è sempre attivo e non conta più nel limite dei 4 slot)."""
        extra_active = self._getExtraActive()
        if patch_num in extra_active:
            extra_active.remove(patch_num)
            self._setExtraActive(extra_active)

    # ---------------------------
    # Logica Business: Toggle Cook
    # ---------------------------
    def toggleCook(self, button_idx):
        """Gestisce il toggle del cooking per un dato pulsante fisico.

        Deck A/B sono sempre attivi e non passano da qui (il toggle sui loro
        pad è ignorato per non spegnere accidentalmente l'uscita live).
        Le patch extra (fuori Deck) sono limitate a self.max_extra_active:
        quando se ne attiva una in più, la più vecchia viene spenta
        automaticamente (FIFO) così il pad risponde sempre.
        """
        patch_idx = self.ui_offset + button_idx
        patch_num = patch_idx + 1

        patch_comp = op(f'/PATCHDECK/PATCHES/X{patch_num}')
        if not patch_comp:
            print(f"[CTRL] ❌ Patch {patch_num} non trovata")
            return

        if self._isOnDeck(patch_num):
            print(f"[CTRL] Patch {patch_num} è su un Deck attivo -- toggle ignorato")
            return

        extra_active = self._getExtraActive()

        if bool(patch_comp.allowCooking):
            # Spegni: libera lo slot
            patch_comp.allowCooking = False
            if patch_num in extra_active:
                extra_active.remove(patch_num)
            self._setExtraActive(extra_active)
        else:
            # Accendi: se i 4 slot sono pieni, libera il più vecchio
            if len(extra_active) >= self.max_extra_active:
                oldest = extra_active.pop(0)
                oldest_comp = op(f'/PATCHDECK/PATCHES/X{oldest}')
                if oldest_comp:
                    oldest_comp.allowCooking = False
                    print(f"[CTRL] ⏏️ Slot pieno: patch {oldest} disattivata automaticamente")
                    oldest_button = oldest - 1 - self.ui_offset
                    if 0 <= oldest_button < self.num_patches:
                        self.updateLed(oldest_button)
            patch_comp.allowCooking = True
            extra_active.append(patch_num)
            self._setExtraActive(extra_active)

        print(f"[CTRL] Patch {patch_num} → cooking = {patch_comp.allowCooking}")
        self.updateLed(button_idx)

    # ---------------------------
    # Mapping button_idx → APC40
    # ---------------------------
    def _mapButtonIdxToRowCol(self, button_idx):
        if not (0 <= button_idx < 24):
            raise ValueError("button_idx deve essere 0–23")

        # Invertiamo l'ordine per matchare la UI (0=Top, 23=Bottom)
        row_order = [3, 4, 5]
        row = row_order[button_idx // 8]
        col = (button_idx % 8) + 1
        return row, col

    # ---------------------------
    # Aggiornamento LED
    # ---------------------------
    def refreshAll(self):
        """Aggiorna tutti i LED secondo stato deck e cooking"""
        for idx in range(self.num_patches):
            self.updateLed(idx)

    def updateLed(self, button_idx):
        patch_idx = self.ui_offset + button_idx
        patch_num = patch_idx + 1

        # Stato deck
        table = self.status_table
        deck_a = str(table[1, 0].val or "0") if table else "0"
        deck_b = str(table[1, 1].val or "0") if table else "0"
        on_deck = (str(patch_num) == deck_a) or (str(patch_num) == deck_b)

        # Stato cooking
        patch_comp = op(f'/PATCHDECK/PATCHES/X{patch_num}')
        cooking = bool(patch_comp.allowCooking) if patch_comp else False

        # Colore LED
        if on_deck and cooking:
            color = 21  # verde
        elif on_deck and not cooking:
            color = 9   # arancione
        elif cooking:
            color = 5   # rosso
        else:
            color = 45  # blu idle

        self.sendLed(button_idx, color)

    # ---------------------------
    # Invio LED a APC40
    # ---------------------------
    def sendLed(self, button_idx, color):
        row, col = self._mapButtonIdxToRowCol(button_idx)
        if self.apc:
            # 1. Aggiorna PAD Griglia
            self.apc.led.set_clip_launch(
                row=row,
                column=col,
                color=color
            )

            # 2. Aggiorna Pulsanti Laterali (1-8, Solo, Rec)
            # Usiamo logica semplice On/Off (True/False) perché questi pulsanti hanno colori fissi hardware
            is_active = (color == 5 or color == 21) # Rosso o Verde = Attivo

            try:
                # Mapping: 0-7=Track Activator (1-8)
                if 0 <= button_idx <= 7:
                    track = button_idx + 1
                    self.apc.led.set_track_number(track, is_active)
                # Mapping: 8-23 Interlacciato (Solo 1, Rec 1, Solo 2, Rec 2...)
                elif 8 <= button_idx <= 23:
                    rel_idx = button_idx - 8
                    track = (rel_idx // 2) + 1      # Ogni 2 pulsanti incrementa la traccia
                    is_rec = (rel_idx % 2) == 1     # Dispari = Rec, Pari = Solo
                    
                    if is_rec:
                        self.apc.led.set_track_record(track, is_active)
                    else:
                        self.apc.led.set_track_solo(track, is_active)
            except Exception as e:
                print(f"[LED] Errore update pulsanti laterali: {e}")
