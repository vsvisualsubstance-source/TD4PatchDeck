class PATCHDECKCTRLledcontroller1:

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.apc = None
        self.num_patches = 24  # numero totale di patch
        self.ui_offset = 0      # offset corrente della UI
        self.status_table = op('/PATCHDECK/UI/MAIN_INTERFACE/MIDI_status') # Cache per performance
        self.max_extra_active = 4  # patch extra oltre Deck A/B, sempre selezionabili da Akai
        self.vram_budget = 0.70    # warm pool: soglia VRAM oltre cui si spengono le patch "pronte" (LRU)

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
    # Warm pool: una patch che lascia un deck (o uno slot extra) NON viene
    # spenta ma resta con allowCooking=True. Non essendo in onda non cucina
    # (0 ms/frame) ma tiene la VRAM gia' allocata: ricaricarla su un deck e'
    # istantaneo, senza il freeze del primo cook (shader/texture/device).
    # Ordine LRU (piu' vecchia in testa). Quando la VRAM supera
    # self.vram_budget si spengono le piu' vecchie finche' si rientra.
    # ---------------------------
    def _getWarm(self):
        return list(self.ownerComp.fetch('warm_patches', [], search=False))

    def _setWarm(self, patches):
        self.ownerComp.store('warm_patches', list(patches))

    def releaseFromWarm(self, patch_num):
        """Toglie patch_num dal warm pool (es. quando torna su un deck)."""
        patch_num = int(patch_num)
        warm = self._getWarm()
        if patch_num in warm:
            warm.remove(patch_num)
            self._setWarm(warm)

    def retirePatch(self, patch_num):
        """Patch non piu' autorizzata (lasciata da un deck o da uno slot
        extra): la parcheggia nel warm pool invece di spegnerla, poi
        controlla il budget VRAM (subito e di nuovo fra ~1 s, quando la
        patch appena caricata ha allocato la sua memoria)."""
        patch_num = int(patch_num)
        patch_comp = op(f'/PATCHDECK/PATCHES/X{patch_num}')
        if not patch_comp:
            return
        if not bool(patch_comp.allowCooking):
            return  # mai accesa/gia' spenta: niente da tenere in caldo
        warm = [n for n in self._getWarm() if n != patch_num]
        warm.append(patch_num)
        self._setWarm(warm)
        print(f"[CTRL] ♨️ Patch {patch_num} → warm pool {warm}")
        self.enforceVramBudget()
        run("me.ext.PATCHDECKCTRLledcontroller1.enforceVramBudget()",
            fromOP=self.ownerComp, delayFrames=30)

    def enforceVramBudget(self):
        """Spegne le patch del warm pool (dalla meno recente) finche' la VRAM
        usata torna sotto self.vram_budget. Le patch su un deck o negli
        slot extra non vengono mai toccate. Ritorna le patch spente."""
        perf = self.ownerComp.op('perform_vram')
        if not perf:
            return []
        used = float(perf['gpu_mem_used'])
        total = float(perf['total_gpu_mem'])
        if total <= 0:
            return []
        limit = total * self.vram_budget
        warm = self._getWarm()
        extra = self._getExtraActive()
        evicted = []
        keep = []
        for n in warm:
            if used > limit and not self._isOnDeck(n) and n not in extra:
                patch_comp = op(f'/PATCHDECK/PATCHES/X{n}')
                if patch_comp:
                    # Perform CHOP si aggiorna solo al frame dopo: stimiamo
                    # la memoria liberata dai TOP della patch.
                    freed = sum(t.gpuMemory for t in patch_comp.findChildren(type=TOP)) / (1024 * 1024)
                    patch_comp.allowCooking = False
                    used -= freed
                evicted.append(n)
            else:
                keep.append(n)
        if evicted:
            self._setWarm(keep)
            print(f"[CTRL] ❄️ VRAM oltre {int(self.vram_budget * 100)}%: spente dal warm pool {evicted}")
            self.refreshAll()
        return evicted

    # ---------------------------
    # Preload scaletta: cuoce una patch alla volta (shader, texture, file,
    # device) e la lascia nel warm pool, cosi' durante lo show il primo
    # caricamento su un deck non causa freeze. Va lanciato a sala vuota:
    # ogni patch pesante blocca il frame per il tempo del suo primo cook.
    # Si ferma da solo quando la VRAM raggiunge self.vram_budget.
    # ---------------------------
    def _parseSetlist(self, text):
        import re
        nums = []
        for tok in re.split(r'[\s,;]+', str(text).strip()):
            if not tok:
                continue
            if '-' in tok:
                a, _, b = tok.partition('-')
                if a.isdigit() and b.isdigit():
                    nums.extend(range(int(a), int(b) + 1))
            elif tok.isdigit():
                nums.append(int(tok))
        if not nums:
            # Scaletta vuota = tutte le patch X1..Xn presenti, finche' c'e' VRAM
            patches_comp = op('/PATCHDECK/PATCHES')
            nums = sorted(int(c.name[1:]) for c in patches_comp.children
                          if c.isCOMP and re.match(r'^X\d+$', c.name) and c.name != 'X0')
        seen = set()
        return [n for n in nums if not (n in seen or seen.add(n))]

    def _setPreloadStatus(self, text):
        print(f"[PRELOAD] {text}")
        if hasattr(self.ownerComp.par, 'Preloadstatus'):
            self.ownerComp.par.Preloadstatus = text

    def preloadSetlist(self, setlist=None):
        """Avvia il preload. setlist: stringa tipo '5 11 26-30 40' (vuota =
        tutte le patch). Default: parametro Setlist del led_controller."""
        if setlist is None:
            setlist = self.ownerComp.par.Setlist.eval() if hasattr(self.ownerComp.par, 'Setlist') else ''
        queue = self._parseSetlist(setlist)
        self.ownerComp.store('preload_queue', queue)
        self.ownerComp.store('preload_done', [])
        self._setPreloadStatus(f"avvio: {len(queue)} patch in coda")
        run("me.ext.PATCHDECKCTRLledcontroller1._preloadStep()",
            fromOP=self.ownerComp, delayFrames=2)

    def stopPreload(self):
        self.ownerComp.store('preload_queue', [])
        self._setPreloadStatus("interrotto")

    def _preloadStep(self):
        queue = list(self.ownerComp.fetch('preload_queue', [], search=False))
        done = list(self.ownerComp.fetch('preload_done', [], search=False))
        if not queue:
            if done:
                self._setPreloadStatus(f"completato: {len(done)} patch pronte {done}")
            self.refreshAll()
            return

        perf = self.ownerComp.op('perform_vram')
        if perf and float(perf['total_gpu_mem']) > 0:
            used = float(perf['gpu_mem_used'])
            total = float(perf['total_gpu_mem'])
            if used >= total * self.vram_budget:
                self.ownerComp.store('preload_queue', [])
                self._setPreloadStatus(
                    f"VRAM al {int(used / total * 100)}%: fermato, pronte {done}, escluse {queue}")
                self.refreshAll()
                return

        patch_num = queue.pop(0)
        self.ownerComp.store('preload_queue', queue)
        patch_comp = op(f'/PATCHDECK/PATCHES/X{patch_num}')
        if patch_comp:
            patch_comp.allowCooking = True
            for o in patch_comp.findChildren():
                if o.family in ('TOP', 'POP'):
                    try:
                        o.cook(force=True)
                    except Exception as e:
                        print(f"[PRELOAD] X{patch_num} {o.path}: {e}")
            if not self._isOnDeck(patch_num) and patch_num not in self._getExtraActive():
                warm = [n for n in self._getWarm() if n != patch_num]
                warm.append(patch_num)
                self._setWarm(warm)
            done.append(patch_num)
            self.ownerComp.store('preload_done', done)
            self._setPreloadStatus(f"X{patch_num} pronta ({len(done)} fatte, {len(queue)} in coda)")

        # Pausa di qualche frame: lascia respirare UI/uscita e aggiorna il
        # Perform CHOP prima del controllo VRAM successivo.
        run("me.ext.PATCHDECKCTRLledcontroller1._preloadStep()",
            fromOP=self.ownerComp, delayFrames=10)

    # ---------------------------
    # Percorso remoto (Gaia/MQTT) -- indexexec.py resta il percorso dei
    # pad fisici, invariato. Questi 3 metodi replicano la stessa logica
    # di autorizzazione/spegnimento per un singolo deck alla volta, cosi'
    # da restare una unica fonte di verita' (MIDI_status, extra_active).
    # ---------------------------
    def loadPatchToDeck(self, patch_num, deck):
        """Carica patch_num sul deck indicato ('A' o 'B'). Mirror di
        indexexec.onOffToOn per il ramo is_deck_a/is_deck_b: stessa logica
        di autorizzazione e spegnimento della patch sostituita, se non piu'
        autorizzata altrove (deck opposto o extra_active)."""
        col = 0 if deck == 'A' else 1
        table = self.status_table
        if not table:
            return False

        patch_comp = op(f'/PATCHDECK/PATCHES/X{patch_num}')
        if not patch_comp:
            print(f"[CTRL] ❌ Patch {patch_num} non trovata (loadPatchToDeck)")
            return False

        old_val = str(table[1, col].val or "0")

        table[1, col].val = str(patch_num)
        patch_comp.allowCooking = True
        self.releaseFromExtra(patch_num)
        self.releaseFromWarm(patch_num)

        other_col = 1 - col
        other_val = str(table[1, other_col].val or "0")
        still_authorized = {str(patch_num), other_val} | {str(n) for n in self._getExtraActive()}
        still_authorized.discard("0")

        if old_val != "0" and old_val not in still_authorized:
            self.retirePatch(old_val)

        self.refreshAll()
        return True

    def clearDeck(self, deck):
        """Mirror esatto di 'Clear A/B' (UI + APC40 Dev View/Detail View):
        scollega la patch dal deck SENZA spegnere allowCooking -- stesso
        comportamento della console oggi. Ritorna il numero di patch appena
        scollegata (0 se il deck era gia' vuoto)."""
        col = 0 if deck == 'A' else 1
        table = self.status_table
        if not table:
            return 0
        old_val = str(table[1, col].val or "0")
        table[1, col].val = "0"
        self.refreshAll()
        return int(old_val) if old_val != "0" else 0

    def deckStatus(self, deck):
        """Numero di patch correntemente sul deck indicato ('A' o 'B'), 0 se vuoto."""
        col = 0 if deck == 'A' else 1
        table = self.status_table
        if not table:
            return 0
        val = str(table[1, col].val or "0")
        return int(val) if val != "0" else 0

    def reconcileCooking(self):
        """Spegne (allowCooking=False) qualunque patch X# NON compresa
        nell'insieme autorizzato (Deck A, Deck B, extra_active_patches) --
        indipendentemente da COME sia stata accesa (griglia APC40, editing
        manuale in TD, script esterno, o drift residuo da una sessione
        precedente). toggleCook() da solo protegge solo le patch accese
        tramite i pad fisici: questo chiude il buco per tutte le altre vie.
        Va chiamata a ogni init/reconnect dell'APC40 (vedi init_apc40) e puo'
        essere richiamata manualmente per un resync immediato."""
        import re
        table = self.status_table
        deck_a = str(table[1, 0].val or "0") if table else "0"
        deck_b = str(table[1, 1].val or "0") if table else "0"
        authorized = set(str(n) for n in self._getExtraActive())
        authorized.update(str(n) for n in self._getWarm())
        authorized.add(deck_a)
        authorized.add(deck_b)
        authorized.discard("0")

        patches_comp = op('/PATCHDECK/PATCHES')
        turned_off = []
        if patches_comp:
            for c in patches_comp.children:
                if not c.isCOMP:
                    continue
                m = re.match(r'^X(\d*)$', c.name)
                if not m:
                    continue
                num = m.group(1) if m.group(1) else '0'
                if num not in authorized and bool(c.allowCooking):
                    c.allowCooking = False
                    turned_off.append(c.name)

        if turned_off:
            print(f"[CTRL] 🔧 Reconcile: disattivate {len(turned_off)} patch non autorizzate: {turned_off}")
        else:
            print("[CTRL] 🔧 Reconcile: nessuna patch fuori budget, ok")

        self.refreshAll()
        return turned_off

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
            self.releaseFromWarm(patch_num)
        else:
            # Accendi: se i 4 slot sono pieni, libera il più vecchio
            if len(extra_active) >= self.max_extra_active:
                oldest = extra_active.pop(0)
                self._setExtraActive(extra_active)
                oldest_comp = op(f'/PATCHDECK/PATCHES/X{oldest}')
                if oldest_comp:
                    # Non la spegniamo: va nel warm pool (resta pronta finche'
                    # c'e' VRAM, vedi retirePatch/enforceVramBudget).
                    self.retirePatch(oldest)
                    print(f"[CTRL] ⏏️ Slot pieno: patch {oldest} spostata nel warm pool")
                    oldest_button = oldest - 1 - self.ui_offset
                    if 0 <= oldest_button < self.num_patches:
                        self.updateLed(oldest_button)
            patch_comp.allowCooking = True
            extra_active.append(patch_num)
            self._setExtraActive(extra_active)
            self.releaseFromWarm(patch_num)

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
        elif cooking and patch_num in self._getWarm():
            color = 13  # giallo: pronta nel warm pool (non in onda)
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
