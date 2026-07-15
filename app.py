import streamlit as st
import math
import plotly.graph_objects as go

# ==========================================
# 1. ANAGRAFICHE DI BASE (Gestite in Memoria)
# ==========================================
if 'mezzi_db' not in st.session_state:
    st.session_state.mezzi_db = {
        "Furgone 35q (3m)": {"L": 300, "P": 180, "A": 190, "Portata": 1500},
        "Motrice 9m": {"L": 900, "P": 240, "A": 260, "Portata": 9000},
        "Bilico 13.6m": {"L": 1360, "P": 240, "A": 270, "Portata": 24000}
    }

if 'oggetti_db' not in st.session_state:
    st.session_state.oggetti_db = {
        "Macchinario Standard A": {"L": 120, "P": 80, "A": 150, "Peso": 300, "Sovrapponibile": False, "Ruotabile": True},
        "Cassa Ricambi Piccola": {"L": 80, "P": 60, "A": 60, "Peso": 50, "Sovrapponibile": True, "Ruotabile": True},
        "Tornio Pesante": {"L": 200, "P": 100, "A": 180, "Peso": 1200, "Sovrapponibile": False, "Ruotabile": False},
        "Pallet EPAL Standard": {"L": 120, "P": 80, "A": 15, "Peso": 25, "Sovrapponibile": True, "Ruotabile": True}
    }

# ==========================================
# 2. INIZIALIZZAZIONE MEMORIA (Session State)
# ==========================================
if 'carico' not in st.session_state:
    st.session_state.carico = []
if 'log_messaggi' not in st.session_state:
    st.session_state.log_messaggi = []

# ==========================================
# 3. MOTORE DI CALCOLO (Bin Packing 2D + Stacking)
# ==========================================
class BinPacker2D:
    def __init__(self, width, length):
        self.free_rects = [{'x': 0, 'y': 0, 'w': width, 'l': length}]

    def pack(self, w, l, ruotabile):
        # Prova orientamento originale
        idx, x, y = self._find_spot(w, l)
        rotated = False
        if idx == -1 and ruotabile:
            # Prova ruotato di 90 gradi
            idx, x, y = self._find_spot(l, w)
            rotated = True
            
        if idx != -1:
            pw = l if rotated else w
            pl = w if rotated else l
            self._split(idx, pw, pl)
            return x, y, rotated
        return None, None, None

    def _find_spot(self, w, l):
        for i, r in enumerate(self.free_rects):
            if r['w'] >= w and r['l'] >= l:
                return i, r['x'], r['y']
        return -1, None, None

    def _split(self, idx, w, l):
        rect = self.free_rects.pop(idx)
        w_rem = rect['w'] - w
        l_rem = rect['l'] - l

        # Taglio orizzontale o verticale (Guillotine Split)
        s1 = [{'x': rect['x']+w, 'y': rect['y'], 'w': w_rem, 'l': l},
              {'x': rect['x'], 'y': rect['y']+l, 'w': rect['w'], 'l': l_rem}]
        s2 = [{'x': rect['x']+w, 'y': rect['y'], 'w': w_rem, 'l': rect['l']},
              {'x': rect['x'], 'y': rect['y']+l, 'w': w, 'l': l_rem}]

        # Sceglie il taglio che lascia l'area singola più grande libera
        area1 = max((r['w']*r['l'] if r['w']>0 and r['l']>0 else 0) for r in s1)
        area2 = max((r['w']*r['l'] if r['w']>0 and r['l']>0 else 0) for r in s2)

        chosen = s1 if area1 > area2 else s2
        for r in chosen:
            if r['w'] > 0 and r['l'] > 0:
                self.free_rects.append(r)
        
        # Ordina dal basso a sinistra
        self.free_rects.sort(key=lambda r: (r['y'], r['x']))

def simula_carico_completo(mezzo, carico_attuale, nuovo_oggetto=None, qta_nuovo=0):
    """Crea le pile di merce e calcola fisicamente le coordinate (X,Y)."""
    items = [{'dati': c, 'qta': c['Quantità']} for c in carico_attuale]
    if nuovo_oggetto and qta_nuovo > 0:
        items.append({'dati': nuovo_oggetto, 'qta': qta_nuovo})
        
    piles = []
    peso_totale = sum(i['dati']['Peso'] * i['qta'] for i in items)
    if peso_totale > mezzo['Portata']: return False, []
        
    for item in items:
        dati = item['dati']
        qta = item['qta']
        # Calcolo impilabilità
        max_stack = math.floor(mezzo['A'] / dati['A']) if dati['Sovrapponibile'] else 1
        max_stack = max(1, max_stack)
        
        num_piles = math.ceil(qta / max_stack)
        rimanenti = qta
        for _ in range(num_piles):
            in_pile = min(rimanenti, max_stack)
            rimanenti -= in_pile
            piles.append({
                'nome': dati['Nome'],
                'w': dati['P'], # Asse X del camion = Larghezza
                'l': dati['L'], # Asse Y del camion = Lunghezza
                'ruotabile': dati.get('Ruotabile', True),
                'elementi': in_pile
            })
            
    # Ordiniamo gli oggetti dal più ingombrante al più piccolo per ottimizzare l'incastro
    piles.sort(key=lambda p: (p['w'] * p['l'], p['elementi']), reverse=True)
    
    packer = BinPacker2D(mezzo['P'], mezzo['L'])
    for p in piles:
        x, y, rot = packer.pack(p['w'], p['l'], p['ruotabile'])
        if x is None: return False, [] # Spazio geometrico finito
        p['x'], p['y'], p['rot'] = x, y, rot
        
    return True, piles

def verifica_spazio(mezzo, carico_attuale, nuovo_oggetto, quantita_richiesta):
    if nuovo_oggetto['A'] > mezzo['A']: return 0, "Altezza superiore al tetto"
    
    max_valid = 0
    # Cerca la quantità massima che si incastra senza sforare
    for q in range(1, quantita_richiesta + 1):
        success, _ = simula_carico_completo(mezzo, carico_attuale, nuovo_oggetto, q)
        if success: max_valid = q
        else: break
            
    if max_valid == quantita_richiesta:
        return max_valid, "OK"
    elif max_valid > 0:
        return max_valid, f"Spazio/Peso in esaurimento. Caricati solo {max_valid} pezzi su {quantita_richiesta}."
    else:
        return 0, "Impossibile incastrare fisicamente l'oggetto. Spazio terminato."

# ==========================================
# 4. INTERFACCIA GRAFICA (UI)
# ==========================================
st.set_page_config(page_title="Simulatore Carico 3D", layout="wide")

# --- MENU LATERALE (IMPOSTAZIONI ANAGRAFICHE) ---
with st.sidebar:
    st.header("⚙️ Impostazioni Database")
    
    st.subheader("🚛 Aggiungi Nuovo Mezzo")
    nuovo_nome_mezzo = st.text_input("Nome Mezzo (es. Ducato)")
    c1, c2 = st.columns(2)
    nuovo_L_mezzo = c1.number_input("Lung (cm)", min_value=1, value=300, key="m_L")
    nuovo_P_mezzo = c2.number_input("Larg (cm)", min_value=1, value=180, key="m_P")
    nuovo_A_mezzo = c1.number_input("Alt (cm)", min_value=1, value=190, key="m_A")
    nuovo_Portata = c2.number_input("Kg Max", min_value=1, value=1500, key="m_Kg")
    
    if st.button("💾 Salva Mezzo", use_container_width=True):
        if nuovo_nome_mezzo and nuovo_nome_mezzo not in st.session_state.mezzi_db:
            st.session_state.mezzi_db[nuovo_nome_mezzo] = {"L": nuovo_L_mezzo, "P": nuovo_P_mezzo, "A": nuovo_A_mezzo, "Portata": nuovo_Portata}
            st.success(f"Mezzo aggiunto!")
            st.rerun()
            
    st.divider()
    
    st.subheader("📦 Aggiungi Oggetto Frequente")
    nuovo_nome_ogg = st.text_input("Nome Oggetto (es. Cestello)")
    c3, c4 = st.columns(2)
    nuovo_L_ogg = c3.number_input("Lung (cm)", min_value=1, value=120, key="o_L")
    nuovo_P_ogg = c4.number_input("Larg (cm)", min_value=1, value=80, key="o_P")
    nuovo_A_ogg = c3.number_input("Alt (cm)", min_value=1, value=100, key="o_A")
    nuovo_Peso_ogg = c4.number_input("Peso (kg)", min_value=1, value=50, key="o_Kg")
    sovrapp_ogg = st.checkbox("Sovrapponibile", value=False, key="o_Sov")
    ruot_ogg = st.checkbox("Ruotabile", value=True, key="o_Ruo")
    
    if st.button("💾 Salva Oggetto", use_container_width=True):
        if nuovo_nome_ogg and nuovo_nome_ogg not in st.session_state.oggetti_db:
            st.session_state.oggetti_db[nuovo_nome_ogg] = {
                "L": nuovo_L_ogg, "P": nuovo_P_ogg, "A": nuovo_A_ogg, "Peso": nuovo_Peso_ogg,
                "Sovrapponibile": sovrapp_ogg, "Ruotabile": ruot_ogg
            }
            st.success("Oggetto aggiunto!")
            st.rerun()

# Alias per far funzionare le variabili nel resto del codice senza modificarlo
MEZZI = st.session_state.mezzi_db
OGGETTI = st.session_state.oggetti_db

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
        peso_totale = sum(item['Peso'] * item['Quantità'] for item in st.session_state.carico)
        area_totale = dati_mezzo['L'] * dati_mezzo['P']
        
        # 🟢 NUOVO: Calcoliamo il layout grafico reale
        success, layout = simula_carico_completo(dati_mezzo, st.session_state.carico)
        
        # L'area occupata ora è data dall'impronta a terra dei pezzi effettivi!
        area_occupata = sum(p['w'] * p['l'] for p in layout) if success else area_totale
        
        perc_peso = min(100, int((peso_totale / dati_mezzo['Portata']) * 100))
        perc_area = min(100, int((area_occupata / area_totale) * 100))
        
        mq_residui = max(0, (area_totale - area_occupata) / 10000)
        epal_residui = math.floor(mq_residui / 0.96)
        
        # Metriche in tempo reale
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Saturazione Peso", f"{perc_peso}%", f"{dati_mezzo['Portata'] - peso_totale} kg liberi")
        mc2.metric("Saturazione Pianale", f"{perc_area}%", f"{mq_residui:.1f} m² liberi")
        mc3.metric("Spazio Residuo EPAL", f"{epal_residui} plt")
        
        st.progress(perc_peso, text="Grafico Peso")
        st.progress(perc_area, text="Grafico Spazio")
        
        # 🟢 NUOVO: Disegno della Mappa 2D interattiva
        if success and layout:
            st.divider()
            st.write("**Mappa di Carico (Vista dall'Alto):**")
            fig = go.Figure()
            
            # Disegna Pianale (Il camion)
            fig.add_shape(type="rect", x0=0, y0=0, x1=dati_mezzo['P'], y1=dati_mezzo['L'],
                          line=dict(color="black", width=3), fillcolor="lightgray", opacity=0.3)
            
            # Disegna la merce incastrata
            colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#e377c2", "#17becf"]
            for p in layout:
                c_idx = abs(hash(p['nome'])) % len(colors)
                pw = p['l'] if p['rot'] else p['w']
                pl = p['w'] if p['rot'] else p['l']
                
                fig.add_shape(type="rect", x0=p['x'], y0=p['y'], x1=p['x']+pw, y1=p['y']+pl,
                              line=dict(color="black", width=1), fillcolor=colors[c_idx], opacity=0.8)
                
                # Etichetta centrata sul pezzo (Nome e Quantità impilata)
                center_x = p['x'] + pw/2
                center_y = p['y'] + pl/2
                testo = f"{p['nome'][:6]}<br>x{p['elementi']}"
                fig.add_annotation(x=center_x, y=center_y, text=testo, showarrow=False, font=dict(size=10, color="white"))
            
            # Imposta le proporzioni reali della griglia
            fig.update_layout(
                xaxis=dict(title="Larghezza Pianale (cm)", range=[-10, dati_mezzo['P']+10]),
                yaxis=dict(title="Lunghezza Pianale (cm)", range=[-10, dati_mezzo['L']+10], scaleanchor="x", scaleratio=1),
                margin=dict(l=10, r=10, t=10, b=10), height=650
            )
            st.plotly_chart(fig, use_container_width=True)
            
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
