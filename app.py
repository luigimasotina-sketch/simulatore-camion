# ... existing code ...
        self.free_rects.sort(key=lambda r: (r['y'], r['x']))

def simula_carico_completo(mezzo, carico_attuale, nuovo_oggetto=None, qta_nuovo=0):
    # Raggruppa oggetti identici prima di creare le pile
    oggetti_raggruppati = {}
    
    def crea_chiave(d):
        return (d['Nome'], d['L'], d['P'], d['A'], d.get('Sovrapponibile', False), d.get('Ruotabile', True))
        
    for c in carico_attuale:
        k = crea_chiave(c)
        if k not in oggetti_raggruppati:
            oggetti_raggruppati[k] = {'dati': c, 'qta': 0}
        oggetti_raggruppati[k]['qta'] += c['Quantità']
        
    if nuovo_oggetto and qta_nuovo > 0:
        k = crea_chiave(nuovo_oggetto)
        if k not in oggetti_raggruppati:
            oggetti_raggruppati[k] = {'dati': nuovo_oggetto, 'qta': 0}
        oggetti_raggruppati[k]['qta'] += qta_nuovo
        
    items = list(oggetti_raggruppati.values())
        
    piles = []
    peso_totale = sum(i['dati']['Peso'] * i['qta'] for i in items)
    if peso_totale > mezzo['Portata']: return False, []
# ... existing code ...
```

### Modifica 2: L'Interfaccia (Raggruppa la lista visiva)
Questa modifica fa in modo che anche la "Distinta di Carico" in basso diventi più pulita. Invece di avere 10 righe con scritto "1x Pallet", avrai una sola riga con "10x Pallet". Vai nella sezione **AREA B: INSERIMENTO MERCE** e sostituisci il comportamento del bottone rosso.

```python:Simulatore Carico 3D:app.py
# ... existing code ...
        quantita = st.number_input("Quantità da inserire", min_value=1, value=1)
        
        if st.button("➕ Aggiungi al Carico", type="primary", use_container_width=True):
            nuovo_oggetto_dict = {"Nome": nome_da_aggiungere, "L": L, "P": P, "A": A, "Peso": Peso, "Sovrapponibile": sovr, "Ruotabile": ruot}
            qta_inseribile, msg = verifica_spazio(dati_mezzo, st.session_state.carico, nuovo_oggetto_dict, quantita)
            
            if qta_inseribile > 0:
                # Cerca se l'oggetto esiste già per sommare le quantità nella distinta
                trovato = False
                for c in st.session_state.carico:
                    if (c['Nome'] == nuovo_oggetto_dict['Nome'] and 
                        c['L'] == nuovo_oggetto_dict['L'] and 
                        c['P'] == nuovo_oggetto_dict['P'] and 
                        c['A'] == nuovo_oggetto_dict['A']):
                        c['Quantità'] += qta_inseribile
                        trovato = True
                        break
                
                if not trovato:
                    nuovo_oggetto_dict["Quantità"] = qta_inseribile
                    st.session_state.carico.append(nuovo_oggetto_dict)
                    
                if qta_inseribile == quantita:
                    st.session_state.log_messaggi = [("success", f"Aggiunti {qta_inseribile} pz di '{nome_da_aggiungere}'.")]
                else:
                    st.session_state.log_messaggi = [("warning", msg)]
            else:
                st.session_state.log_messaggi = [("error", msg)]
                
            st.rerun()

    # --- CRUSCOTTO E MAPPA (ORIZZONTALE) ---
    with col_dx:
# ... existing code ...
```

