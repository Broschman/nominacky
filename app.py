import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

SOUBOR_DATA = "vysledky_jms.csv"
POVOLENE_ZAVODY = ["Sprint", "Dráhový test", "Střední trať (krátká)", "Dlouhá trať (klasika)"]

# --- POMOCNÉ FUNKCE (zůstávají stejné) ---
def urci_kategorii(klub):
    vyjimky_holky = ["UOL0740", "SJ10750", "SJI0750"]
    klub_upraveny = str(klub).strip()
    if klub_upraveny in vyjimky_holky: return "Juniorky"
    match = re.search(r"\d{4}$", klub_upraveny)
    if match and int(match.group(0)[2:4]) >= 50: return "Juniorky"
    return "Junioři"

def ziskej_body_za_umisteni(poradi):
    if pd.isna(poradi) or str(poradi).strip() == "": return 0
    try: poradi = int(float(poradi))
    except ValueError: return 0
    if poradi == 1: return 11
    elif poradi == 2: return 9
    elif poradi == 3: return 7
    elif poradi == 4: return 5
    elif poradi == 5: return 3
    elif poradi == 6: return 2
    elif poradi == 7: return 1
    else: return 0

def ziskej_body_za_drahu(cas_str, klub):
    if not isinstance(cas_str, str) or ":" not in cas_str: return 0
    casti = cas_str.split(':')
    try: sekundy = int(casti[0]) * 60 + int(casti[1])
    except ValueError: return 0
    kategorie = urci_kategorii(klub)
    if kategorie == "Juniorky":
        if sekundy <= 645: return 7
        elif sekundy <= 655: return 6
        elif sekundy <= 665: return 5
        elif sekundy <= 675: return 4
        elif sekundy <= 685: return 3
        elif sekundy <= 695: return 2
        elif sekundy <= 705: return 1
        else: return 0
    else:
        if sekundy <= 535: return 7
        elif sekundy <= 545: return 6
        elif sekundy <= 555: return 5
        elif sekundy <= 565: return 4
        elif sekundy <= 575: return 3
        elif sekundy <= 585: return 2
        elif sekundy <= 595: return 1
        else: return 0

def spocitej_skore_a_kriteria(df_zavodnik):
    body_draha = 0
    body_ob = []
    body_stredni = 0
    for index, radek in df_zavodnik.iterrows():
        body = radek["Získané body"]
        if radek["Závod"] == "Dráhový test": body_draha += body
        else:
            body_ob.append(body)
            if radek["Závod"] == "Střední trať (krátká)": body_stredni = body
    body_ob.sort(reverse=True)
    soucet_dvou_ob = sum(body_ob[:2])
    nejlepsi_ob = body_ob[0] if len(body_ob) > 0 else 0
    return pd.Series({'Celkové body': body_draha + soucet_dvou_ob, 'Tie1_OB2': soucet_dvou_ob, 'Tie2_OBmax': nejlepsi_ob, 'Tie3_Stredni': body_stredni})

def format_body(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    try: return str(int(float(val)))
    except ValueError: return str(val)

def style_table(row):
    styles = [''] * len(row)
    if 'Pořadí' in row.index:
        try:
            poradi = int(str(row['Pořadí']).replace('.', ''))
            if poradi <= 4: styles = ['background-color: rgba(46, 204, 113, 0.3);'] * len(row)
            elif poradi <= 6: styles = ['background-color: rgba(241, 196, 15, 0.2);'] * len(row)
        except ValueError: pass
    ob_cols = ["Sprint", "Střední trať (krátká)", "Dlouhá trať (klasika)"]
    ob_scores = []
    for col in ob_cols:
        if col in row.index and str(row[col]).strip() != "":
            try: ob_scores.append((col, float(row[col])))
            except ValueError: pass
    if len(ob_scores) == 3:
        min_col = min(ob_scores, key=lambda x: x[1])[0]
        col_idx = row.index.get_loc(min_col)
        styles[col_idx] += ' text-decoration: line-through; color: #a8a8a8;'
    return styles

# --- HLAVNÍ LOGIKA ---
st.title("Nominační žebříček JMS 2026")

if os.path.exists(SOUBOR_DATA):
    df_real = pd.read_csv(SOUBOR_DATA)
    if "Pořadí" in df_real.columns and "Pořadí/Čas" not in df_real.columns:
        df_real.rename(columns={"Pořadí": "Pořadí/Čas"}, inplace=True)
else:
    df_real = pd.DataFrame(columns=["Závod", "Pořadí/Čas", "Jméno", "Klub", "Získané body"])

# SIMULACE: Přepínač a logika
if 'sim_mode' not in st.session_state: st.session_state.sim_mode = False
sim_mode = st.toggle("Zapnout režim SIMULACE (What-if)", value=st.session_state.sim_mode)
st.session_state.sim_mode = sim_mode

if sim_mode:
    st.warning("⚠️ JSI V REŽIMU SIMULACE! Data se neukládají do ostré databáze.")
    if 'df_sim' not in st.session_state: st.session_state.df_sim = df_real.copy()
    df_source = st.session_state.df_sim
else:
    df_source = df_real

# --- ZOBRAZENÍ TABULEK ---
if not df_source.empty:
    df_skore = df_source.groupby('Jméno').apply(spocitej_skore_a_kriteria).reset_index()
    df_unikatni = df_source[['Jméno', 'Klub']].drop_duplicates()
    df_pivot_zobr = df_source.drop_duplicates(subset=['Jméno', 'Závod'], keep='last').pivot(index='Jméno', columns='Závod', values='Získané body').reset_index()
    
    df_zobr = pd.merge(df_unikatni, df_pivot_zobr, on='Jméno', how='left')
    df_zobr = pd.merge(df_zobr, df_skore, on='Jméno', how='left')
    df_zobr['Kategorie'] = df_zobr['Klub'].apply(urci_kategorii)
    df_zobr.sort_values(['Celkové body', 'Tie1_OB2', 'Tie2_OBmax', 'Tie3_Stredni'], ascending=[False, False, False, False], inplace=True)
    
    for col in POVOLENE_ZAVODY + ['Celkové body']:
        if col in df_zobr.columns: df_zobr[col] = df_zobr[col].apply(format_body)
    
    def process_category(cat):
        df_cat = df_zobr[df_zobr['Kategorie'] == cat].copy().reset_index(drop=True)
        df_cat.insert(0, 'Pořadí', range(1, len(df_cat) + 1))
        df_cat['Pořadí'] = df_cat['Pořadí'].astype(str) + "."
        return df_cat.drop(columns=['Kategorie', 'Tie1_OB2', 'Tie2_OBmax', 'Tie3_Stredni']).fillna("")

    styled_juniorky = process_category('Juniorky').style.apply(style_table, axis=1)
    styled_juniori = process_category('Junioři').style.apply(style_table, axis=1)
    
    cols = st.columns(2)
    with cols[0]:
        st.subheader("Juniorky")
        st.dataframe(styled_juniorky, width="stretch", hide_index=True)
    with cols[1]:
        st.subheader("Junioři")
        st.dataframe(styled_juniori, width="stretch", hide_index=True)
    st.divider()

st.subheader("Přidat / Upravit výsledky")
zalozka_pdf, zalozka_rucne = st.tabs(["📄 Nahrát z PDF", "✍️ Celková editovatelná tabulka"])

with zalozka_pdf:
    st.info("Nahrajte PDF (např. ze Sprintu). Data se uloží a přepíší případné ruční záznamy pro daný závod.")
    nazev_zavodu_pdf = st.selectbox("Vyberte závod pro import z PDF:", POVOLENE_ZAVODY, key="pdf_zavod")
    uploaded_file = st.file_uploader("Nahrajte PDF s výsledky", type="pdf")
    
    if uploaded_file is not None and st.button("Zpracovat PDF a uložit"):
        zavodnici = []
        with pdfplumber.open(uploaded_file) as pdf:
            for strana in pdf.pages:
                text = strana.extract_text()
                for radek in text.split('\n'):
                    match = re.search(r"^(\d+)\.\s+(.*?)\s+([A-Z]{3}\d{4})", radek)
                    if match:
                        poradi = int(match.group(1))
                        jmeno = match.group(2).strip()
                        klub = match.group(3)
                        body = ziskej_body_za_umisteni(poradi)
                        
                        zavodnici.append({
                            "Závod": nazev_zavodu_pdf,
                            "Pořadí/Čas": str(poradi),
                            "Jméno": jmeno,
                            "Klub": klub,
                            "Získané body": body
                        })
        if zavodnici:
            df_nove = pd.DataFrame(zavodnici)
            if not df_historie.empty:
                jmena_v_pdf = df_nove['Jméno'].tolist()
                maska_k_smazani = (df_historie['Závod'] == nazev_zavodu_pdf) & (df_historie['Jméno'].isin(jmena_v_pdf))
                df_historie = df_historie[~maska_k_smazani]
                
            df_komplet = pd.concat([df_historie, df_nove], ignore_index=True)
            df_komplet.to_csv(SOUBOR_DATA, index=False)
            st.success(f"Výsledky z PDF pro závod '{nazev_zavodu_pdf}' byly uloženy!")
            st.rerun()
        else:
            st.warning("V PDF se nepodařilo najít žádné platné výsledky.")

with zalozka_rucne:
    if df_historie.empty:
        st.warning("Zatím neznám žádné závodníky. Nahrajte prosím nejprve výsledky prvního závodu v PDF.")
    else:
        st.info("Zde vidíte předepsaná data z databáze. Doplňte chybějící výsledky a uložte vše najednou.")
        
        df_unikatni = df_historie[['Jméno', 'Klub']].drop_duplicates()
        df_pivot = df_historie.drop_duplicates(subset=['Jméno', 'Závod'], keep='last').pivot(index='Jméno', columns='Závod', values='Pořadí/Čas').reset_index()
        df_master = pd.merge(df_unikatni, df_pivot, on='Jméno', how='left')
        
        for zavod in POVOLENE_ZAVODY:
            if zavod not in df_master.columns:
                df_master[zavod] = ""
                
        df_skore_edit = df_historie.groupby('Jméno').apply(spocitej_skore_a_kriteria).reset_index()
        df_master = pd.merge(df_master, df_skore_edit, on='Jméno', how='left')
        df_master['Kategorie'] = df_master['Klub'].apply(urci_kategorii)
        
        # Zde už jsme měli pořadí nastavené správně
        sloupce = ["Jméno", "Klub", "Celkové body"] + POVOLENE_ZAVODY
        df_master.sort_values(['Celkové body', 'Tie1_OB2', 'Tie2_OBmax', 'Tie3_Stredni'], ascending=[False, False, False, False], inplace=True)
        
        df_master_holky = df_master[df_master['Kategorie'] == 'Juniorky'][sloupce].fillna("")
        df_master_kluci = df_master[df_master['Kategorie'] == 'Junioři'][sloupce].fillna("")

        st.subheader("Editace - Dívky (Juniorky)")
        edited_holky = st.data_editor(
            df_master_holky,
            disabled=["Jméno", "Klub", "Celkové body"],
            width="stretch",
            hide_index=True,
            key="edit_holky"
        )
        
        st.subheader("Editace - Chlapci (Junioři)")
        edited_kluci = st.data_editor(
            df_master_kluci,
            disabled=["Jméno", "Klub", "Celkové body"],
            width="stretch",
            hide_index=True,
            key="edit_kluci"
        )
        
        if st.button("Uložit všechny úpravy (pro obě kategorie)"):
            nova_data = []
            edited_komplet = pd.concat([edited_holky, edited_kluci], ignore_index=True)
            
            for index, radek in edited_komplet.iterrows():
                jmeno = radek["Jméno"]
                klub = radek["Klub"]
                
                for zavod in POVOLENE_ZAVODY:
                    hodnota = str(radek.get(zavod, "")).strip()
                    
                    if hodnota.endswith(".0"):
                        hodnota = hodnota[:-2]
                    
                    if hodnota != "" and hodnota != "nan":
                        if zavod == "Dráhový test":
                            body = ziskej_body_za_drahu(hodnota, klub)
                        else:
                            body = ziskej_body_za_umisteni(hodnota)
                            
                        nova_data.append({
                            "Závod": zavod,
                            "Pořadí/Čas": hodnota,
                            "Jméno": jmeno,
                            "Klub": klub,
                            "Získané body": body
                        })
            
            df_nove_komplet = pd.DataFrame(nova_data)
            df_nove_komplet.to_csv(SOUBOR_DATA, index=False)
            st.success("Všechny změny byly úspěšně uloženy a žebříček byl přepočítán!")
            st.rerun()
