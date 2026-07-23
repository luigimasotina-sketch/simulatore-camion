import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import copy
import random

st.set_page_config(page_title="Simulatore di Carico Aziendale", layout="wide")

# Ingrandiamo i menu a tendina e compattiamo la vista
st.markdown("""
<style>
    .stSelectbox label { font-size: 1.2rem; font-weight: bold; }
    div[data-baseweb="select"] > div { font-size: 1.1rem; }
    .stNumberInput label { font-size: 1.1rem; }
    .stAlert { font-size: 1.1rem; }
    /* Nascondi temporaneamente la vecchia pagina di gestione per non fare confusione */
    [data-testid="stSidebarNav"] {display: none;} 
</style>
""", unsafe_allow_html=True)

if 'log_messaggi' not in st.session_state:
    st.session_state.log_messaggi = []

# Sostituisci questo URL con il link CSV 
GOOGLE_SHEETS_CSV_URL = "" 

@st.cache_data(ttl=60) # Ricarica i dati ogni 60 secondi
def carica_anagrafica_google(url):
    if url == "https://docs.google.com/spreadsheets/d/e/2PACX-1vSr0tNyiDkPywA93FffiOSoD1Q07zMrgXpLXwM9ftn3DKH8DsHu9ySZN-26KPzhkduuwdUFxfpWXHQg/pub?gid=1792566437&single=true&output=csv":
        return pd.DataFrame()
    try:
        df = pd.read_csv(url)
        # Rinominiamo le colonne per assicurarci che corrispondano alla logica interna
        rename_map = {
            'Descrizione': 'Nome',
            'L (cm)': 'L',
            'P (cm)': 'P',
            'A (cm)': 'A',
            'Non affincabile se di punta': 'NonAffiancabile'
        }
        df.rename(columns=rename_map, inplace=True)
        
        # Gestiamo i boolean (Vero/Falso in italiano)
        for col in ['Sovrapponibile', 'Ruotabile', 'NonAffiancabile']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.lower()
                df[col] = df[col].map({'vero': True, 'falso': False, 'true': True, 'false': False, 'v': True, 'f': False})
                df[col] = df[col].fillna(False) # Default a False
        
        # Pulizia numeri
        for col in ['L', 'P', 'A', 'Peso']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                
        return df
    except Exception as e:
        errore_str = str(e)
        if "401" in errore_str or "Unauthorized" in errore_str:
            st.error("🔒 Errore 401: Il Foglio Google è privato. Usa 'File -> Pubblica sul Web' oppure cambia le impostazioni di condivisione su 'Chiunque abbia il link'.")
        else:
            st.error(f"Errore nel caricamento del Foglio Google: {e}")
        return pd.DataFrame()

if 'mezzi' not in st.session_state:
    st.session_state.mezzi = pd.DataFrame([
        {"Nome": "Bilico 13.6m", "Lunghezza": 1360, "Larghezza": 240, "Altezza": 270, "Portata": 24000},
        {"Nome": "Motrice 9 mt", "Lunghezza": 960, "Larghezza": 240, "Altezza": 260, "Portata": 15000},
        {"Nome": "Motrice 7 mt", "Lunghezza": 750, "Larghezza": 240, "Altezza": 255, "Portata": 9000},
        {"Nome": "Daily", "Lunghezza": 445, "Larghezza": 210, "Altezza": 230, "Portata": 1000},
        {"Nome": "Container 20 piedi", "Lunghezza": 590, "Larghezza": 235, "Altezza": 239, "Portata": 9000},
        {"Nome": "Container 40 piedi", "Lunghezza": 1203, "Larghezza": 235, "Altezza": 239, "Portata": 24000},
        {"Nome": "Container 40 piedi HC", "Lunghezza": 1203, "Larghezza": 235, "Altezza": 269, "Portata": 24000}
    ])

# Carica gli oggetti all'avvio
st.session_state.oggetti_google = carica_anagrafica_google(GOOGLE_SHEETS_CSV_URL)

# Fallback se il foglio non è ancora collegato (per test)
if st.session_state.oggetti_google.empty:
    if 'oggetti' not in st.session_state:
        st.session_state.oggetti = pd.DataFrame([
            {"Categoria": "Spedizioni", "Nome": "Gabbia", "L": 120, "P": 100, "A": 110, "Peso": 150, "Sovrapponibile": True, "Ruotabile": True, "NonAffiancabile": False},
            {"Categoria": "Spedizioni", "Nome": "Pallet EPAL Standard", "L": 120, "P": 80, "A": 30, "Peso": 25, "Sovrapponibile": True, "Ruotabile": True, "NonAffiancabile": False},
            {"Categoria": "Spedizioni", "Nome": "KM 120 Pallet", "L": 219, "P": 138, "A": 170, "Peso": 880, "Sovrapponibile": False, "Ruotabile": True, "NonAffiancabile": True},
            {"Categoria": "Trasferimenti Interni", "Nome": "B260", "L": 234, "P": 152, "A": 181, "Peso": 1770, "Sovrapponibile": False, "Ruotabile": True, "NonAffiancabile": True},
        ])
else:
    st.session_state.oggetti = st.session_state.oggetti_google


if 'carico' not in st.session_state:
    st.session_state.carico = []

class Rect:
    def __init__(self, x, y, w, d):
        self.x = x
        self.y = y
        self.w = w
        self.d = d

    def intersects(self, other):
        return not (self.x >= other.x + other.w or 
                    self.x + self.w <= other.x or 
                    self.y >= other.y + other.d or 
                    self.y + self.d <= other.y)

def aggiorna_rettangoli(free_rectangles, new_block):
    new_free_rectangles = []
    for rect in free_rectangles:
        if not rect.intersects(new_block):
            new_free_rectangles.append(rect)
        else:
            if new_block.x > rect.x: new_free_rectangles.append(Rect(rect.x, rect.y, new_block.x - rect.x, rect.d))
            if new_block.x + new_block.w < rect.x + rect.w: new_free_rectangles.append(Rect(new_block.x + new_block.w, rect.y, rect.x + rect.w - (new_block.x + new_block.w), rect.d))
            if new_block.y > rect.y: new_free_rectangles.append(Rect(rect.x, rect.y, rect.w, new_block.y - rect.y))
            if new_block.y + new_block.d < rect.y + rect.d: new_free_rectangles.append(Rect(rect.x, new_block.y + new_block.d, rect.w, rect.y + rect.d - (new_block.y + new_block.d)))
    
    new_free_rectangles = [r for r in new_free_rectangles if r.w > 0 and r.d > 0]
    
    final_free_rectangles = []
    for r1 in new_free_rectangles:
        is_contained = False
        for r2 in new_free_rectangles:
            if r1 != r2 and r1.x >= r2.x and r1.y >= r2.y and r1.x + r1.w <= r2.x + r2.w and r1.y + r1.d <= r2.y + r2.d:
                is_contained = True
                break
        if not is_contained:
            final_free_rectangles.append(r1)
    return final_free_rectangles

def simula_carico_completo(mezzo, carico_attuale, nuovo_oggetto=None, qta_nuovo=0):
    lista_totale = []
    for c in carico_attuale:
        lista_totale.append({'dati': c, 'qta': c['Quantità']})
        
    if nuovo_oggetto and qta_nuovo > 0:
        lista_totale.append({'dati': nuovo_oggetto, 'qta': qta_nuovo})
        
    peso_totale = sum(i['dati']['Peso'] * i['qta'] for i in lista_totale)
    if peso_totale > mezzo['Portata']:
        return False, [], []
        
    stacks_da_piazzare = []
    for item in lista_totale:
        dati = item['dati']
        qta_rimasta = item['qta']
        qta_impilabile = 1
        if dati.get('Sovrapponibile', False):
            qta_impilabile = max(1, math.floor(mezzo['Altezza'] / dati['A']))
            
        while qta_rimasta > 0:
            qta_in_questo_stack = min(qta_rimasta, qta_impilabile)
            stacks_da_piazzare.append({
                'Nome': dati['Nome'], 'L': dati['L'], 'P': dati['P'],
                'A': dati['A'] * qta_in_questo_stack,
                'Ruotabile': dati.get('Ruotabile', True),
                'NonAffiancabile': dati.get('NonAffiancabile', False),
                'qta_stack': qta_in_questo_stack
            })
            qta_rimasta -= qta_in_questo_stack

    # Ordine base INTELLIGENTE
    stacks_da_piazzare.sort(key=lambda x: x['L'] * x['P'], reverse=True)

    best_placed = []
    best_free = []
    max_packed_count = -1
    best_length = float('inf')

    # --- SOTTOFUNZIONE: Esegue un singolo tentativo ---
    def esegui_tentativo(stacks, strategia_rotazione):
        placed = []
        free_rects = [Rect(0, 0, mezzo['Lunghezza'], mezzo['Larghezza'])]
        success = True

        for stack in stacks:
            best_score = (float('inf'), float('inf'))
            best_pos = None
            best_dim = None
            best_rect_idx = -1
            is_virtual_full_width = False

            orientations = [(stack['L'], stack['P'], False)]
            if stack['Ruotabile'] and stack['L'] != stack['P']:
                orientations.append((stack['P'], stack['L'], True))

            if strategia_rotazione == 'girato':
                orientations.reverse()
            elif strategia_rotazione == 'random' and random.choice([True, False]):
                orientations.reverse()

            for w, d, is_rot in orientations:
                virtual_d = d
                occupies_full_width = False
                
                # Applica logica "Non Affiancabile se di punta"
                if stack['NonAffiancabile'] and (w == stack['L'] or stack['L'] == stack['P']):
                    virtual_d = mezzo['Larghezza']
                    occupies_full_width = True

                for i, rect in enumerate(free_rects):
                    if rect.w >= w and rect.d >= virtual_d:
                        score = (rect.x, rect.y)
                        if score < best_score:
                            best_score = score
                            best_pos = (rect.x, rect.y)
                            best_dim = (w, d)
                            best_rect_idx = i
                            is_virtual_full_width = occupies_full_width

            if best_pos:
                w, d = best_dim
                sel_rect = free_rects[best_rect_idx]
                
                if is_virtual_full_width:
                    blocking_rect = Rect(sel_rect.x, 0, w, mezzo['Larghezza']) 
                    free_rects = aggiorna_rettangoli(free_rects, blocking_rect)
                    draw_y = (mezzo['Larghezza'] - d) / 2
                    placed.append({
                        'Nome': stack['Nome'],
                        'x': sel_rect.x, 'y': draw_y, 'z': 0,
                        'l': w, 'p': d, 'a': stack['A'],
                        'qta_stack': stack['qta_stack']
                    })
                else:
                    new_block = Rect(sel_rect.x, sel_rect.y, w, d)
                    free_rects = aggiorna_rettangoli(free_rects, new_block)
                    placed.append({
                        'Nome': stack['Nome'],
                        'x': new_block.x, 'y': new_block.y, 'z': 0,
                        'l': w, 'p': d, 'a': stack['A'],
                        'qta_stack': stack['qta_stack']
                    })
            else:
                success = False
                break
        return placed, free_rects

    # FASE 1: FAST PATH
    for strategia in ['dritto', 'girato']:
        placed, free_rects = esegui_tentativo(stacks_da_piazzare, strategia)
        if len(placed) > max_packed_count:
            max_packed_count = len(placed)
            best_placed = placed
            best_free = free_rects
            if len(placed) > 0:
                best_length = max(b['x'] + b['l'] for b in placed)
        elif len(placed) == max_packed_count and len(placed) > 0:
            current_length = max(b['x'] + b['l'] for b in placed)
            if current_length < best_length:
                best_length = current_length
                best_placed = placed
                best_free = free_rects

    # FASE 2: RESCUE PATH (Solo se Fase 1 fallisce)
    is_total_success = (max_packed_count == len(stacks_da_piazzare))
    
    if not is_total_success:
        for tentativo in range(1000):
            current_stacks = list(stacks_da_piazzare)
            current_stacks.sort(key=lambda x: (x['L'] * x['P']) + random.randint(-1500, 1500), reverse=True)
                
            placed, free_rects = esegui_tentativo(current_stacks, 'random')

            if len(placed) > max_packed_count:
                max_packed_count = len(placed)
                best_placed = placed
                best_free = free_rects
                if len(placed) > 0:
                    best_length = max(b['x'] + b['l'] for b in placed)
            elif len(placed) == max_packed_count and len(placed) > 0:
                current_length = max(b['x'] + b['l'] for b in placed)
                if current_length < best_length:
                    best_length = current_length
                    best_placed = placed
                    best_free = free_rects

            if max_packed_count == len(stacks_da_piazzare):
                is_total_success = True
                break

    return is_total_success, best_placed, best_free

def stima_epal_residui(free_rectangles_iniziali):
    free_rects = copy.deepcopy(free_rectangles_iniziali)
    epal_count = 0
    
    while True:
        best_idx = -1
        best_score = (float('inf'), float('inf'))
        best_dim = None

        for i, rect in enumerate(free_rects):
            # Prova EPAL dritto
            if rect.w >= 120 and rect.d >= 80:
                score = (rect.x, rect.y)
                if score < best_score:
                    best_score = score
                    best_idx = i
                    best_dim = (120, 80)
            # Prova EPAL ruotato
            if rect.w >= 80 and rect.d >= 120:
                score = (rect.x, rect.y)
                if score < best_score:
                    best_score = score
                    best_idx = i
                    best_dim = (80, 120)

        if best_idx == -1:
            break 

        rect = free_rects[best_idx]
        new_block = Rect(rect.x, rect.y, best_dim[0], best_dim[1])
        epal_count += 1
        free_rects = aggiorna_rettangoli(free_rects, new_block)

    return epal_count

def verifica_spazio(mezzo, carico_attuale, nuovo_oggetto, qta_richiesta):
    for q in range(qta_richiesta, 0, -1):
        ok, _, _ = simula_carico_completo(mezzo, carico_attuale, nuovo_oggetto, q)
        if ok:
            if q == qta_richiesta:
                return q, "OK"
            else:
                return q, f"Spazio in esaurimento: trovata combinazione per caricare {q} pezzi su {qta_richiesta}."
    return 0, "Spazio o portata insufficiente. Impossibile incastrare altri pezzi."


st.sidebar.title("🚛 Navigazione")
st.sidebar.markdown("**Modalità operative:**")

# Selettore Categoria
categoria_selezionata = st.sidebar.radio(
    "Scegli il contesto di carico:",
    ["Spedizioni", "Trasferimenti Interni"]
)

if 'Categoria' in st.session_state.oggetti.columns:
    if categoria_selezionata == "Trasferimenti Interni":
        oggetti_filtrati = st.session_state.oggetti[st.session_state.oggetti['Categoria'].str.contains("Trasferiment", case=False, na=False)]
    else:
        oggetti_filtrati = st.session_state.oggetti[st.session_state.oggetti['Categoria'].str.contains("Spedizion", case=False, na=False)]
else:
    oggetti_filtrati = st.session_state.oggetti

st.title("🚛 Simulatore di Carico Aziendale")

nomi_mezzi = st.session_state.mezzi["Nome"].tolist()
mezzo_selezionato = st.selectbox("1. Seleziona il Mezzo", nomi_mezzi, label_visibility="collapsed")
dati_mezzo = st.session_state.mezzi[st.session_state.mezzi["Nome"] == mezzo_selezionato].iloc[0].to_dict()

dati_mezzo_effettivo = dati_mezzo.copy()
dati_mezzo_effettivo['Lunghezza'] = max(0, dati_mezzo['Lunghezza'] - 10)
dati_mezzo_effettivo['Altezza'] = max(0, dati_mezzo['Altezza'] - 15)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Lunghezza Utile", f"{dati_mezzo_effettivo['Lunghezza']} cm", f"(-10cm margine)", delta_color="off")
col_m2.metric("Larghezza (P)", f"{dati_mezzo_effettivo['Larghezza']} cm")
col_m3.metric("Altezza Utile", f"{dati_mezzo_effettivo['Altezza']} cm", f"(-15cm margine)", delta_color="off")
col_m4.metric("Portata Max", f"{dati_mezzo_effettivo['Portata']} kg")

st.divider()
col_sx, col_dx = st.columns([1, 2], gap="large")

with col_sx:
    st.subheader(f"2. Aggiungi Merce ({categoria_selezionata})")
    
    lista_oggetti = oggetti_filtrati.to_dict('records')
    for o in lista_oggetti:
        if 'NonAffiancabile' not in o:
            o['NonAffiancabile'] = False
            
    opzioni_menu = ["Oggetto non in anagrafica"] + [f"{o['Nome']} ({o.get('L',0)}x{o.get('P',0)}x{o.get('A',0)}cm | {o.get('Peso',0)}kg)" for o in lista_oggetti]
    
    scelta_oggetto = st.selectbox("Seleziona Oggetto:", opzioni_menu)
    
    if scelta_oggetto == "Oggetto non in anagrafica":
        st.info("Compila i dati dell'oggetto personalizzato")
        nome_da_aggiungere = st.text_input("Nome Oggetto", "Pallet Custom")
        c1, c2, c3 = st.columns(3)
        L = c1.number_input("Lunghezza (cm)", min_value=1, value=120)
        P = c2.number_input("Larghezza (cm)", min_value=1, value=80)
        A = c3.number_input("Altezza (cm)", min_value=1, value=100)
        Peso = st.number_input("Peso (kg)", min_value=1, value=200)
        c4, c5, c6 = st.columns(3)
        sovr = c4.checkbox("Sovrapponibile", value=False)
        ruot = c5.checkbox("Ruotabile", value=True)
        non_aff = c6.checkbox("Non Affiancabile se di punta", value=False)
    else:
        idx = opzioni_menu.index(scelta_oggetto) - 1
        ogg_selezionato = lista_oggetti[idx]
        nome_da_aggiungere = ogg_selezionato['Nome']
        L, P, A = ogg_selezionato.get('L',0), ogg_selezionato.get('P',0), ogg_selezionato.get('A',0)
        Peso = ogg_selezionato.get('Peso',0)
        sovr = ogg_selezionato.get('Sovrapponibile', False)
        ruot = ogg_selezionato.get('Ruotabile', True)
        non_aff = ogg_selezionato.get('NonAffiancabile', False)
        st.write(f"**Dimensioni:** {L}x{P}x{A}cm - **Peso:** {Peso}kg")
        st.write(f"{'✔️' if sovr else '❌'} Sovrapponibile | {'✔️' if ruot else '❌'} Ruotabile")
        if non_aff:
            st.warning("⚠️ Questo oggetto non permette affiancamento se caricato di punta.")

    quantita = st.number_input("Quantità da inserire", min_value=1, value=1)
    
    if st.button("➕ Aggiungi al Carico", type="primary", use_container_width=True):
        nuovo_oggetto_dict = {
            "Nome": nome_da_aggiungere, "L": L, "P": P, "A": A, "Peso": Peso, 
            "Sovrapponibile": sovr, "Ruotabile": ruot, "NonAffiancabile": non_aff
        }
        
        qta_inseribile, msg = verifica_spazio(dati_mezzo_effettivo, st.session_state.carico, nuovo_oggetto_dict, quantita)
        
        if qta_inseribile > 0:
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

with col_dx:
    st.subheader("3. Stato del Carico")
    
    for tipo, msg in st.session_state.log_messaggi:
        if tipo == "success": st.success(msg)
        elif tipo == "warning": st.warning(msg)
        elif tipo == "error": st.error(msg)
    st.session_state.log_messaggi = []

    _, blocchi_piazzati, spazi_liberi = simula_carico_completo(dati_mezzo_effettivo, st.session_state.carico)
    
    peso_attuale = sum(c['Peso'] * c['Quantità'] for c in st.session_state.carico)
    area_occupata = sum((b['l']/100) * (b['p']/100) for b in blocchi_piazzati)
    area_totale = (dati_mezzo_effettivo['Lunghezza']/100) * (dati_mezzo_effettivo['Larghezza']/100)
    
    perc_peso = int((peso_attuale / dati_mezzo_effettivo['Portata']) * 100) if dati_mezzo_effettivo['Portata'] else 0
    perc_spazio = int((area_occupata / area_totale) * 100) if area_totale else 0
    
    max_x_raggiunto = max([b['x'] + b['l'] for b in blocchi_piazzati], default=0)
    cm_restanti = max(0, dati_mezzo_effettivo['Lunghezza'] - max_x_raggiunto)
    
    epal_residui = stima_epal_residui(spazi_liberi)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Saturazione Peso", f"{perc_peso}%", f"{dati_mezzo_effettivo['Portata'] - peso_attuale} kg liberi", delta_color="normal")
    c2.metric("Saturazione Pianale", f"{perc_spazio}%", f"{(area_totale - area_occupata):.1f} m² liberi", delta_color="normal")
    c3.metric("Spazi EPAL Certi", f"{epal_residui} plt", "Basato su incastri reali")
    
    st.markdown(f"**Spazio lineare residuo a fondo camion:** <span style='color:#00CC96; font-size:1.2rem; font-weight:bold;'>{int(cm_restanti)} cm</span>", unsafe_allow_html=True)
    
    st.progress(min(perc_peso, 100), text="Grafico Peso")
    st.progress(min(perc_spazio, 100), text="Grafico Spazio")
    
    st.write("**Mappa di Carico (Vista dall'Alto):**")
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=[0, dati_mezzo_effettivo['Lunghezza'], dati_mezzo_effettivo['Lunghezza'], 0, 0],
        y=[0, 0, dati_mezzo_effettivo['Larghezza'], dati_mezzo_effettivo['Larghezza'], 0],
        fill="toself",
        fillcolor="lightgray",
        line=dict(color="black", width=2),
        mode="lines",
        name="Pianale",
        hoverinfo="skip"
    ))
    
    colors = ['#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52']
    
    for i, b in enumerate(blocchi_piazzati):
        c = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=[b['x'], b['x']+b['l'], b['x']+b['l'], b['x'], b['x']],
            y=[b['y'], b['y'], b['y']+b['p'], b['y']+b['p'], b['y']],
            fill="toself",
            fillcolor=c,
            line=dict(color="black", width=1),
            mode="lines",
            name=f"{b['Nome']} (x{b['qta_stack']})",
            text=f"<b>{b['Nome']}</b><br>x{b['qta_stack']}",
            hoverinfo="text"
        ))
        
        fig.add_trace(go.Scatter(
            x=[b['x'] + b['l']/2],
            y=[b['y'] + b['p']/2],
            mode="text",
            text=[f"<b>{b['qta_stack']}x</b><br>{b['Nome'][:10]}"],
            textfont=dict(size=14, color="white"),
            hoverinfo="skip",
            showlegend=False
        ))
        
    fig.update_layout(
        xaxis=dict(range=[-10, dati_mezzo_effettivo['Lunghezza']+10], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-10, dati_mezzo_effettivo['Larghezza']+10], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
        margin=dict(l=0, r=0, t=10, b=0),
        height=300,
        plot_bgcolor="white",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

    st.write("**Distinta di Carico:**")
    for i, c in enumerate(st.session_state.carico):
        col_txt, col_btn = st.columns([8, 1])
        col_txt.write(f"- **{c['Quantità']}x {c['Nome']}** ({c['Peso']}kg cad. | {c['L']}x{c['P']}x{c['A']})")
        if col_btn.button("❌", key=f"del_{i}"):
            st.session_state.carico.pop(i)
            st.rerun()
            
    if st.session_state.carico:
        if st.button("🗑️ Svuota Camion", type="secondary"):
            st.session_state.carico = []
            st.rerun()
