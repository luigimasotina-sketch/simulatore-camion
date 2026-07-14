import streamlit as st

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
# Serve per non far dimenticare all'app cosa c'è sul camion se clicchiamo un bottone
if 'carico' not in st.session_state:
    st.session_state.carico = []

# ==========================================
# 3. INTERFACCIA GRAFICA (UI)
# ==========================================
st.set_page_config(page_title="Simulatore Carico 3D", layout="wide")
st.title("🚛 Simulatore di Carico Aziendale")

# --- AREA A: SELEZIONE MEZZO ---
st.subheader("1. Seleziona il Mezzo")
mezzo_scelto = st.selectbox("Scegli il camion:", list(MEZZI.keys()))
dati_mezzo = MEZZI[mezzo_scelto]

# Mostriamo le info del mezzo
col1, col2, col3, col4 = st.columns(4)
col1.metric("Lunghezza", f"{dati_mezzo['L']} cm")
col2.metric("Larghezza", f"{dati_mezzo['P']} cm")
col3.metric("Altezza", f"{dati_mezzo['A']} cm")
col4.metric("Portata Max", f"{dati_mezzo['Portata']} kg")

st.divider()

# Creiamo due colonne principali per l'Area B e l'Area C
col_sx, col_dx = st.columns([1, 2])

# --- AREA B: INSERIMENTO MERCE ---
with col_sx:
    st.subheader("2. Aggiungi Merce")
    
    lista_oggetti = list(OGGETTI.keys()) + ["Oggetto non in anagrafica"]
    oggetto_scelto = st.selectbox("Seleziona Oggetto:", lista_oggetti)
    
    # Variabili che riempiremo in base alla scelta
    nome_da_aggiungere = ""
    L, P, A, Peso = 0, 0, 0, 0
    sovr, ruot = False, False
    
    if oggetto_scelto == "Oggetto non in anagrafica":
        st.info("Compila i dati dell'oggetto personalizzato")
        nome_da_aggiungere = st.text_input("Nome Oggetto")
        c1, c2, c3 = st.columns(3)
        L = c1.number_input("Lunghezza (cm)", min_value=1, value=100)
        P = c2.number_input("Larghezza (cm)", min_value=1, value=100)
        A = c3.number_input("Altezza (cm)", min_value=1, value=100)
        Peso = st.number_input("Peso (kg)", min_value=1, value=100)
        c4, c5 = st.columns(2)
        sovr = c4.checkbox("Sovrapponibile")
        ruot = c5.checkbox("Ruotabile")
    else:
        # Prende i dati dall'anagrafica
        dati_ogg = OGGETTI[oggetto_scelto]
        nome_da_aggiungere = oggetto_scelto
        L, P, A = dati_ogg["L"], dati_ogg["P"], dati_ogg["A"]
        Peso = dati_ogg["Peso"]
        sovr, ruot = dati_ogg["Sovrapponibile"], dati_ogg["Ruotabile"]
        st.write(f"*Dimensioni: {L}x{P}x{A}cm - Peso: {Peso}kg*")
    
    quantita = st.number_input("Quantità da inserire", min_value=1, value=1)
    
    if st.button("➕ Aggiungi al Carico", type="primary", use_container_width=True):
        # QUI ANDRÀ IL MOTORE MATEMATICO. 
        # Per ora facciamo finta che entri tutto e lo salviamo in memoria
        st.session_state.carico.append({
            "Nome": nome_da_aggiungere,
            "Quantità": quantita,
            "L": L, "P": P, "A": A, "Peso": Peso
        })
        st.success(f"Aggiunto alla lista di calcolo!")
        st.rerun()

# --- AREA C: CRUSCOTTO E RISULTATI ---
with col_dx:
    st.subheader("3. Stato del Carico")
    
    if len(st.session_state.carico) == 0:
        st.info("Il camion è attualmente vuoto.")
    else:
        # Tabella degli oggetti
        st.write("**Lista Oggetti Inseriti:**")
        for i, item in enumerate(st.session_state.carico):
            st.write(f"- **{item['Quantità']}x {item['Nome']}** ({item['Peso']}kg cad.)")
            
        if st.button("🗑️ Svuota Camion"):
            st.session_state.carico = []
            st.rerun()
            
        st.divider()
        st.write("📊 *Indicatori di Spazio e Disegno 3D (Work in progress nei prossimi passaggi...)*")
