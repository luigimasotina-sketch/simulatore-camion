import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math

# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="Simulatore di Carico Aziendale", layout="wide")

# --- CSS STYLING ---
# Ingrandiamo i menu a tendina e compattiamo la vista
st.markdown("""
<style>
    .stSelectbox label { font-size: 1.2rem; font-weight: bold; }
    div[data-baseweb="select"] > div { font-size: 1.1rem; }
    .stNumberInput label { font-size: 1.1rem; }
    .stAlert { font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE DATI (ANAGRAFICHE DI BASE) ---
if 'mezzi' not in st.session_state:
    st.session_state.mezzi = pd.DataFrame([
        {"Nome": "Bilico 13.6m", "Lunghezza": 1360, "Larghezza": 240, "Altezza": 270, "Portata": 24000},
        {"Nome": "Motrice 9 mt", "Lunghezza": 960, "Larghezza": 240, "Altezza": 260, "Portata": 15000},
        {"Nome": "Motrice 7 mt", "Lunghezza": 750, "Larghezza": 240, "Altezza": 255, "Portata": 9000},
        {"Nome": "Daily", "Lunghezza": 445, "Larghezza": 210, "Altezza": 230, "Portata": 24000},
        {"Nome": "Container 20 piedi", "Lunghezza": 590, "Larghezza": 235, "Altezza": 239, "Portata": 9000},
        {"Nome": "Container 40 piedi", "Lunghezza": 1203, "Larghezza": 235, "Altezza": 239, "Portata": 24000},
        {"Nome": "Container 40 piedi HC", "Lunghezza": 1203, "Larghezza": 235, "Altezza": 269, "Portata": 24000}
    ])

if 'oggetti' not in st.session_state:
    st.session_state.oggetti = pd.DataFrame([
        {"Nome": "Pallet EPAL Standard", "L": 120, "P": 80, "A": 15, "Peso": 25, "Sovrapponibile": True, "Ruotabile": True},
        {"Nome": "Macchinario Standard A", "L": 120, "P": 80, "A": 150, "Peso": 300, "Sovrapponibile": False, "Ruotabile": False},
        {"Nome": "Cassa Ricambi Piccola", "L": 80, "P": 60, "A": 60, "Peso": 50, "Sovrapponibile": True, "Ruotabile": True}
    ])

if 'carico' not in st.session_state:
    st.session_state.carico = []
if 'log_messaggi' not in st.session_state:
    st.session_state.log_messaggi = []

# --- MOTORE DI CALCOLO (BIN PACKING 2D + ALTEZZA) ---
class FreeSpace:
    def __init__(self, x, y, w, d):
        self.x = x
        self.y = y
        self.w = w
        self.d = d

def simula_carico_completo(mezzo, carico_attuale, nuovo_oggetto=None, qta_nuovo=0):
    # 1. Raggruppa oggetti identici prima di creare le pile
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
    
    # Controllo Peso Totale
    peso_totale = sum(i['dati']['Peso'] * i['qta'] for i in items)
    if peso_totale > mezzo['Portata']: 
        return False, [], []

    # 2. Algoritmo di piazzamento (Guillotine Split)
    free_spaces = [FreeSpace(0, 0, mezzo['Lunghezza'], mezzo['Larghezza'])]
    placed_blocks = []
    
    # Ordina gli oggetti da incastrare dal più ingombrante al più piccolo
    items.sort(key=lambda x: x['dati']['L'] * x['dati']['P'], reverse=True)
    
    for item in items:
        qta_rimasta = item['qta']
        dati = item['dati']
        
        while qta_rimasta > 0:
            best_space_idx = -1
            best_l, best_p = dati['L'], dati['P']
            
            # Cerca il primo spazio utile
            for i, space in enumerate(free_spaces):
                # Proviamo orientamento normale
                if space.w >= dati['L'] and space.d >= dati['P']:
                    best_space_idx = i
                    best_l, best_p = dati['L'], dati['P']
                    break
                # Proviamo ruotato
                elif dati.get('Ruotabile', True) and space.w >= dati['P'] and space.d >= dati['L']:
                    best_space_idx = i
                    best_l, best_p = dati['P'], dati['L']
                    break
                    
            if best_space_idx == -1:
                return False, [], [] # Spazio a terra finito
                
            space = free_spaces.pop(best_space_idx)
            
            # Calcola quanti impilarne in questo specifico punto (Altezza)
            qta_impilabile = 1
            if dati.get('Sovrapponibile', False):
                qta_impilabile = min(qta_rimasta, math.floor(mezzo['Altezza'] / dati['A']))
                
            if qta_impilabile == 0: 
                return False, [], [] # Non ci sta per l'altezza

            # Aggiungi blocco piazzato
            placed_blocks.append({
                'Nome': dati['Nome'],
                'x': space.x, 'y': space.y, 'z': 0,
                'l': best_l, 'p': best_p, 'a': dati['A'] * qta_impilabile,
                'qta_stack': qta_impilabile
            })
            qta_rimasta -= qta_impilabile
            
            # Taglio dello spazio residuo (Guillotine split sull'asse più lungo)
            w_rem = space.w - best_l
            d_rem = space.d - best_p
            
            if w_rem > 0:
                free_spaces.append(FreeSpace(space.x + best_l, space.y, w_rem, best_p))
            if d_rem > 0:
                free_spaces.append(FreeSpace(space.x, space.y + best_p, space.w, d_rem))
                
            # Riordina spazi liberi: si riempie dal fondo del camion (X minore)
            free_spaces.sort(key=lambda s: (s.x, s.y))
            
    return True, placed_blocks, free_spaces

def verifica_spazio(mezzo, carico_attuale, nuovo_oggetto, qta_richiesta):
    # Logica di Saturazione progressiva: provo a metterli tutti, sennò scalo
    for q in range(qta_richiesta, 0, -1):
        ok, _, _ = simula_carico_completo(mezzo, carico_attuale, nuovo_oggetto, q)
        if ok:
            if q == qta_richiesta:
                return q, "OK"
            else:
                return q, f"Spazio o portata in esaurimento: caricati solo {q} pezzi su {qta_richiesta}."
    return 0, "Spazio o portata insufficiente per aggiungere anche un solo pezzo."

# --- SIDEBAR NAVIGAZIONE ---
st.sidebar.title("🚛 Navigazione")
pagina = st.sidebar.radio("Scegli la pagina:", ["Simulatore di Carico", "Gestione Anagrafiche"])

if pagina == "Gestione Anagrafiche":
    st.title("⚙️ Gestione Anagrafiche")
    st.markdown("Modifica le tabelle qui sotto per aggiungere, modificare o eliminare (seleziona la riga e premi **Canc** sulla tastiera). Le modifiche vengono usate istantaneamente nel simulatore.")
    
    st.subheader("Anagrafica Mezzi")
    st.session_state.mezzi = st.data_editor(st.session_state.mezzi, num_rows="dynamic", use_container_width=True)
    
    st.subheader("Anagrafica Oggetti")
    st.session_state.oggetti = st.data_editor(st.session_state.oggetti, num_rows="dynamic", use_container_width=True)

else:
    # --- PAGINA PRINCIPALE (SIMULATORE) ---
    st.title("🚛 Simulatore di Carico Aziendale")

    # --- AREA A: SELEZIONE MEZZO ---
    nomi_mezzi = st.session_state.mezzi["Nome"].tolist()
    mezzo_selezionato = st.selectbox("1. Seleziona il Mezzo", nomi_mezzi, label_visibility="collapsed")
    dati_mezzo = st.session_state.mezzi[st.session_state.mezzi["Nome"] == mezzo_selezionato].iloc[0].to_dict()

    # APPLICAZIONE MARGINI DI SICUREZZA (10cm Lunghezza, 15cm Altezza)
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

    # --- AREA B: INSERIMENTO MERCE ---
    with col_sx:
        st.subheader("2. Aggiungi Merce")
        
        lista_oggetti = st.session_state.oggetti.to_dict('records')
        opzioni_menu = ["Oggetto non in anagrafica"] + [f"{o['Nome']} ({o['L']}x{o['P']}x{o['A']}cm | {o['Peso']}kg)" for o in lista_oggetti]
        
        scelta_oggetto = st.selectbox("Seleziona Oggetto:", opzioni_menu)
        
        if scelta_oggetto == "Oggetto non in anagrafica":
            st.info("Compila i dati dell'oggetto personalizzato")
            nome_da_aggiungere = st.text_input("Nome Oggetto", "Pallet Custom")
            c1, c2, c3 = st.columns(3)
            L = c1.number_input("Lunghezza (cm)", min_value=1, value=120)
            P = c2.number_input("Larghezza (cm)", min_value=1, value=80)
            A = c3.number_input("Altezza (cm)", min_value=1, value=100)
            Peso = st.number_input("Peso (kg)", min_value=1, value=200)
            c4, c5 = st.columns(2)
            sovr = c4.checkbox("Sovrapponibile", value=False)
            ruot = c5.checkbox("Ruotabile", value=True)
        else:
            idx = opzioni_menu.index(scelta_oggetto) - 1
            ogg_selezionato = lista_oggetti[idx]
            nome_da_aggiungere = ogg_selezionato['Nome']
            L, P, A = ogg_selezionato['L'], ogg_selezionato['P'], ogg_selezionato['A']
            Peso = ogg_selezionato['Peso']
            sovr = ogg_selezionato.get('Sovrapponibile', False)
            ruot = ogg_selezionato.get('Ruotabile', True)
            st.write(f"**Dimensioni:** {L}x{P}x{A}cm - **Peso:** {Peso}kg")
            st.write(f"{'✔️' if sovr else '❌'} Sovrapponibile | {'✔️' if ruot else '❌'} Ruotabile")

        quantita = st.number_input("Quantità da inserire", min_value=1, value=1)
        
        if st.button("➕ Aggiungi al Carico", type="primary", use_container_width=True):
            nuovo_oggetto_dict = {"Nome": nome_da_aggiungere, "L": L, "P": P, "A": A, "Peso": Peso, "Sovrapponibile": sovr, "Ruotabile": ruot}
            
            qta_inseribile, msg = verifica_spazio(dati_mezzo_effettivo, st.session_state.carico, nuovo_oggetto_dict, quantita)
            
            if qta_inseribile > 0:
                # RAGGRUPPAMENTO NELLA LISTA VISIVA (Evita doppioni in distinta)
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

    # --- AREA C: STATO DEL CARICO E MAPPA ---
    with col_dx:
        st.subheader("3. Stato del Carico")
        
        # Mostra i banner di log
        for tipo, msg in st.session_state.log_messaggi:
            if tipo == "success": st.success(msg)
            elif tipo == "warning": st.warning(msg)
            elif tipo == "error": st.error(msg)
        st.session_state.log_messaggi = [] # Svuota log

        # Riesegue il calcolo per avere i dati aggiornati per la mappa
        _, blocchi_piazzati, spazi_liberi = simula_carico_completo(dati_mezzo_effettivo, st.session_state.carico)
        
        peso_attuale = sum(c['Peso'] * c['Quantità'] for c in st.session_state.carico)
        area_occupata = sum((b['l']/100) * (b['p']/100) for b in blocchi_piazzati)
        area_totale = (dati_mezzo_effettivo['Lunghezza']/100) * (dati_mezzo_effettivo['Larghezza']/100)
        
        perc_peso = int((peso_attuale / dati_mezzo_effettivo['Portata']) * 100) if dati_mezzo_effettivo['Portata'] else 0
        perc_spazio = int((area_occupata / area_totale) * 100) if area_totale else 0
        
        # Calcolo geometrico reale degli EPAL residui basato sugli spazi liberi
        epal_residui = 0
        for space in spazi_liberi:
            epal_dritti = math.floor(space.w / 120) * math.floor(space.d / 80)
            epal_girati = math.floor(space.w / 80) * math.floor(space.d / 120)
            epal_residui += max(epal_dritti, epal_girati)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Saturazione Peso", f"{perc_peso}%", f"{dati_mezzo_effettivo['Portata'] - peso_attuale} kg liberi", delta_color="normal")
        c2.metric("Saturazione Pianale", f"{perc_spazio}%", f"{(area_totale - area_occupata):.1f} m² liberi", delta_color="normal")
        c3.metric("Spazi EPAL Certi", f"{epal_residui} plt")
        
        st.progress(min(perc_peso, 100), text="Grafico Peso")
        st.progress(min(perc_spazio, 100), text="Grafico Spazio")
        
        # MAPPA 2D ORIZZONTALE CON PLOTLY
        st.write("**Mappa di Carico (Vista dall'Alto):**")
        fig = go.Figure()
        
        # Disegna il pianale (X = Lunghezza, Y = Larghezza) - Scale 1:1 per non deformarlo
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
        
        # Disegna i blocchi della merce
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
            
            # Testo grande al centro del blocco
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
            height=300, # Altezza compatta
            plot_bgcolor="white",
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # DISTINTA DI CARICO
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
