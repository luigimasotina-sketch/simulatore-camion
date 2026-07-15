import streamlit as st
import math

# ==========================================
# 1. ANAGRAFICHE DI BASE (Dati Finti)
# ==========================================
MEZZI = {
    "Furgone 35q (3m)": {"L": 300, "P": 180, "A": 190, "Portata": 1500},
    "Motrice 9m": {"L": 900, "P": 240, "A": 260, "Portata": 9000},
    "Bilico 13.6m": {"L": 1360, "P": 240, "A": 270, "Portata": 24000}
}

OGGETTI = {
    "Macchinario Standard A": {"L": 120, "P": 80, "A": 150, "Peso": 300, "Sovrapponibile": False, "Ruotabile": True},
    "Cassa Ricambi Piccola": {"L": 80, "P": 60, "A": 60, "Peso": 50, "Sovrapponibile": True, "Ruotabile": True},
    "Tornio Pesante": {"L": 200, "P": 100, "A": 180, "Peso": 1200, "Sovrapponibile": False, "Ruotabile": False}
}

# ==========================================
# 2. INIZIALIZZAZIONE MEMORIA (Session State)
# ==========================================
if 'carico' not in st.session_state:
    st.session_state.carico = []
if 'log_messaggi' not in st.session_state:
    st.session_state.log_messaggi = []

# ==========================================
# 3. MOTORE DI CALCOLO (Bin Packing Semplificato)
# ==========================================
def verifica_spazio(mezzo, carico_attuale, nuovo_oggetto, quantita_richiesta):
    """
    Simula l'inserimento verificando Area, Peso e Altezza.
    Ritorna la quantità effettivamente caricabile (da 0 a quantita_richiesta).
    """
    # Controlli bloccanti di base (L'oggetto è fisicamente troppo grande per il camion?)
    if nuovo_oggetto['A'] > mezzo['A']:
        return 0, "Altezza oggetto superiore al tetto del mezzo."
    if nuovo_oggetto['L'] > mezzo['L'] or nuovo_oggetto['P'] > mezzo['P']:
        # Controllo base (migliorabile gestendo la rotazione 90°)
        if not (nuovo_oggetto['P'] <= mezzo['L'] and nuovo_oggetto['L'] <= mezzo['P']):
             return 0, "Oggetto più grande delle dimensioni del pianale."

    # Calcolo risorse totali del mezzo
    area_totale = mezzo['L'] * mezzo['P']
    portata_totale = mezzo['Portata']
    
    # Calcolo risorse già occupate
    area_occupata = 0
    peso_occupato = 0
    
    for item in carico_attuale:
        peso_occupato += (item['Peso'] * item['Quantità'])
        # Se non è sovrapponibile, occupa area a terra per ogni pezzo
        # (Se è sovrapponibile, il calcolo andrebbe affinato in base alle pile, per ora lo semplifichiamo)
        if not item['Sovrapponibile']:
             area_occupata += (item['L'] * item['P'] * item['Quantità'])
        else:
             # Simuliamo che si impilino fino all'altezza del camion
             livelli_possibili = math.floor(mezzo['A'] / item['A'])
             if livelli_possibili < 1: livelli_possibili = 1
             area_occupata += ((item['L'] * item['P'] * item['Quantità']) / livelli_possibili)

    # Verifica inserimento progressivo
    area_singolo = nuovo_oggetto['L'] * nuovo_oggetto['P']
    peso_singolo = nuovo_oggetto['Peso']
    
    if nuovo_oggetto['Sovrapponibile']:
        livelli_nuovo = math.floor(mezzo['A'] / nuovo_oggetto['A'])
        if livelli_nuovo < 1: livelli_nuovo = 1
        area_effettiva_singolo = area_singolo / livelli_nuovo
    else:
        area_effettiva_singolo = area_singolo

    quantita_caricabile = 0
    for i in range(quantita_richiesta):
        if (area_occupata + area_effettiva_singolo) <= area_totale and (peso_occupato + peso_singolo) <= portata_totale:
            quantita_caricabile += 1
            area_occupata += area_effettiva_singolo
            peso_occupato += peso_singolo
        else:
            break # Il camion è pieno

    if quantita_caricabile == quantita_richiesta:
        return quantita_caricabile, "OK"
    elif quantita_caricabile > 0:
        motivo = "Spazio/Peso insufficiente"
        return quantita_caricabile, f"Saturazione: Caricati {quantita_caricabile} su {quantita_richiesta}. {motivo}."
    else:
        return 0, "Spazio o portata insufficiente per aggiungere anche un solo pezzo."

# ==========================================
# 4. INTERFACCIA GRAFICA (UI)
# ==========================================
st.set_page_config(page_title="Simulatore Carico 3D", layout="wide")
st.title("🚛 Simulatore di Carico Aziendale")

# --- AREA A: SELEZIONE MEZZO ---
st.subheader("1. Seleziona il Mezzo")
mezzo_scelto = st.selectbox("Scegli il camion:", list(MEZZI.keys()))
dati_mezzo = MEZZI[mezzo_scelto]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Lunghezza (L)", f"{dati_mezzo['L']} cm")
col2.metric("Larghezza (P)", f"{dati_mezzo['P']} cm")
col3.metric("Altezza (A)", f"{dati_mezzo['A']} cm")
col4.metric("Portata Max", f"{dati_mezzo['Portata']} kg")

st.divider()

col_sx, col_dx = st.columns([1, 2])

# --- AREA B: INSERIMENTO MERCE ---
with col_sx:
    st.subheader("2. Aggiungi Merce")
    
    lista_oggetti = list(OGGETTI.keys()) + ["Oggetto non in anagrafica"]
    
    def formatta_nome_oggetto(nome):
        if nome in OGGETTI:
            d = OGGETTI[nome]
            return f"{nome} ({d['L']}x{d['P']}x{d['A']}cm | {d['Peso']}kg)"
        return nome
        
    oggetto_scelto = st.selectbox("Seleziona Oggetto:", lista_oggetti, format_func=formatta_nome_oggetto)
    
    # Form dinamico
    if oggetto_scelto == "Oggetto non in anagrafica":
        st.info("Compila i dati dell'oggetto personalizzato")
        nome_da_aggiungere = st.text_input("Nome Oggetto", value="Cassa Su Misura")
        c1, c2, c3 = st.columns(3)
        L = c1.number_input("Lunghezza (cm)", min_value=1, value=120)
        P = c2.number_input("Larghezza (cm)", min_value=1, value=80)
        A = c3.number_input("Altezza (cm)", min_value=1, value=100)
        Peso = st.number_input("Peso (kg)", min_value=1, value=200)
        c4, c5 = st.columns(2)
        sovr = c4.checkbox("Sovrapponibile")
        ruot = c5.checkbox("Ruotabile")
    else:
        dati_ogg = OGGETTI[oggetto_scelto]
        nome_da_aggiungere = oggetto_scelto
        L, P, A = dati_ogg["L"], dati_ogg["P"], dati_ogg["A"]
        Peso = dati_ogg["Peso"]
        sovr, ruot = dati_ogg["Sovrapponibile"], dati_ogg["Ruotabile"]
        st.write(f"*Dimensioni: {L}x{P}x{A}cm - Peso: {Peso}kg*")
        st.write(f"*{'Sovrapponibile' if sovr else 'Non sovrapponibile'} | {'Ruotabile' if ruot else 'Non ruotabile'}*")
    
    quantita = st.number_input("Quantità da inserire", min_value=1, value=1)
    
    if st.button("➕ Aggiungi al Carico", type="primary", use_container_width=True):
        nuovo_oggetto_dict = {
            "Nome": nome_da_aggiungere,
            "L": L, "P": P, "A": A, "Peso": Peso,
            "Sovrapponibile": sovr, "Ruotabile": ruot
        }
        
        qta_inseribile, msg = verifica_spazio(dati_mezzo, st.session_state.carico, nuovo_oggetto_dict, quantita)
        
        if qta_inseribile == quantita:
            nuovo_oggetto_dict["Quantità"] = qta_inseribile
            st.session_state.carico.append(nuovo_oggetto_dict)
            st.session_state.log_messaggi = [("success", f"Aggiunti {qta_inseribile} pz di '{nome_da_aggiungere}'.")]
        elif qta_inseribile > 0:
            nuovo_oggetto_dict["Quantità"] = qta_inseribile
            st.session_state.carico.append(nuovo_oggetto_dict)
            st.session_state.log_messaggi = [("warning", msg)]
        else:
            st.session_state.log_messaggi = [("error", msg)]
            
        st.rerun()

# --- AREA C: CRUSCOTTO E RISULTATI ---
with col_dx:
    st.subheader("3. Stato del Carico")
    
    # Mostriamo eventuali messaggi di sistema
    if st.session_state.log_messaggi:
        tipo, testo = st.session_state.log_messaggi[0]
        if tipo == "success": st.success(testo)
        elif tipo == "warning": st.warning(testo)
        elif tipo == "error": st.error(testo)
    
    if len(st.session_state.carico) == 0:
        st.info("Il camion è attualmente vuoto.")
    else:
        # Calcolo Totali
        peso_totale = sum(item['Peso'] * item['Quantità'] for item in st.session_state.carico)
        area_totale = dati_mezzo['L'] * dati_mezzo['P']
        
        # Stima area occupata (molto semplificata per la visualizzazione)
        area_occupata = 0
        for item in st.session_state.carico:
             if item['Sovrapponibile']:
                 livelli = max(1, math.floor(dati_mezzo['A'] / item['A']))
                 area_occupata += ((item['L'] * item['P'] * item['Quantità']) / livelli)
             else:
                 area_occupata += (item['L'] * item['P'] * item['Quantità'])
        
        perc_peso = min(100, int((peso_totale / dati_mezzo['Portata']) * 100))
        perc_area = min(100, int((area_occupata / area_totale) * 100))
        
        mq_residui = (area_totale - area_occupata) / 10000 # conversione cm2 in m2
        epal_residui = math.floor(mq_residui / 0.96)
        
        # Metriche in tempo reale
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Saturazione Peso", f"{perc_peso}%", f"{dati_mezzo['Portata'] - peso_totale} kg liberi")
        mc2.metric("Saturazione Pianale", f"{perc_area}%", f"{mq_residui:.1f} m² liberi")
        mc3.metric("Spazio Residuo EPAL", f"{epal_residui} plt")
        
        st.progress(perc_peso, text="Grafico Peso")
        st.progress(perc_area, text="Grafico Spazio")
        
        st.divider()
        st.write("**Distinta di Carico:**")
        
        for i, item in enumerate(st.session_state.carico):
            c_desc, c_btn = st.columns([5,1])
            with c_desc:
                st.write(f"- **{item['Quantità']}x {item['Nome']}** ({item['Peso']}kg cad. | {item['L']}x{item['P']}x{item['A']})")
            with c_btn:
                if st.button("❌", key=f"del_{i}"):
                    st.session_state.carico.pop(i)
                    st.session_state.log_messaggi = [("info", f"Elemento rimosso dal carico.")]
                    st.rerun()
            
        st.divider()
        if st.button("🗑️ Svuota intero Camion", type="secondary"):
            st.session_state.carico = []
            st.session_state.log_messaggi = []
            st.rerun()
