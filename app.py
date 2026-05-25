import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

SOUBOR_DATA = "vysledky_jms.csv"

POVOLENE_ZAVODY = [
    "Sprint", 
    "Dráhový test", 
    "Střední trať (krátká)", 
    "Dlouhá trať (klasika)"
]

# --- POMOCNÉ FUNKCE ---
def urci_kategorii(klub):
    vyjimky_holky = ["UOL0740", "SJ10750", "SJI0750"]
    klub_upraveny = str(klub).strip()
    if klub_upraveny in vyjimky_holky:
        return "Juniorky"

    match = re.search(r"\d{4}$", klub_upraveny)
    if match:
        id_cislo = int(match.group(0)[2:4])
        if id_cislo >= 50:
            return "Juniorky"
    return "Junioři"

def ziskej_body_za_umisteni(poradi):
    if pd.isna(poradi) or str(poradi).strip() == "": return 0
    try:
        poradi = int(float(poradi))
    except ValueError:
        return 0
        
    if poradi == 1: return 11
    elif poradi == 2: return 9
    elif poradi == 3: return 7
    elif poradi == 4: return 5
    elif poradi == 5: return 3
    elif poradi == 6: return 2
    elif poradi == 7: return 1
    else: return 0

def ziskej_body_za_drahu(cas_str, klub):
    if not isinstance(cas_str, str) or ":" not in cas_str:
        return 0
    
    casti = cas_str.split(':')
    try:
        sekundy = int(casti[0]) * 60 + int(casti[1])
    except ValueError:
        return 0
        
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
        if radek["Závod"] == "Dráhový test":
            body_draha += body
        else:
            body_ob.append(body)
            if radek["Závod"] == "Střední trať (krátká)":
                body_stredni = body

    body_ob.sort(reverse=True)
    soucet_dvou_ob = sum(body_ob[:2])
    nejlepsi_ob = body_ob[0] if len(body_ob) > 0 else 0
    
    celkove_skore = body_draha + soucet_dvou_ob

    return pd.Series({
        'Celkové body': celkove_skore,
        'Tie1_OB2': soucet_dvou_ob,
        'Tie2_OBmax': nejlepsi_ob,
        'Tie3_Stredni': body_stredni
    })

def format_body(val):
    """Odstraní nevzhledná desetinná místa u celých čísel"""
    if pd.isna(val) or str(val).strip() == "":
        return ""
    try:
        return str(int(float(val)))
    except ValueError:
        return str(val)

def style_dropped_race(row):
    """Pandas Styler: Najde třetí nejhorší OB závod a vizuálně ho přeškrtne."""
    ob_cols = ["Sprint", "Střední trať (krátká)", "Dlouhá trať (klasika)"]
    styles = pd.Series('', index=row.index)
    
    ob_scores = []
    # Posbíráme všechny platné body z OB závodů pro daného závodníka
    for col in ob_cols:
        if col in row.index:
            val = row[col]
            if val != "":
                try:
                    ob_scores.append((col, float(val)))
                except ValueError:
                    pass
    
    # Škrtáme pouze v případě, že běžel všechny 3 OB závody
    if len(ob_scores) == 3:
        # Najdeme závod s nejmenším počtem bodů
        min_col = min(ob_scores, key=lambda x: x[1])[0]
        # Přidáme CSS styl pro přeškrtnutí a zešednutí
        styles[min_col] = 'text-decoration: line-through; color: #a8a8a8;'
        
    return styles

st.title("Nominační žebříček JMS 2026")
st.write("Aplikace automaticky předepisuje již uložená data a škrtá nejhorší závod.")

if os.path.exists(SOUBOR_DATA):
    df_historie = pd.read_csv(SOUBOR_DATA)
    if "Pořadí" in df_historie.columns and "Pořadí/Čas" not in df_historie.columns:
        df_historie.rename(columns={"Pořadí": "Pořadí/Čas"}, inplace=True)
else:
    df_historie = pd.DataFrame(columns=["Závod", "Pořadí/Čas", "Jméno", "Klub", "Získané body"])

# --- ZOBRAZENÍ HLAVNÍCH TABULEK ---
if not df_historie.empty:
    st.header("Aktuální nominační žebříček")
    
    df_skore = df_historie.groupby('Jméno').apply(spocitej_skore_a_kriteria).reset_index()
    df_unikatni = df_historie[['Jméno', 'Klub']].drop_duplicates()
    
    df_pivot_zobr = df_historie.drop_duplicates(subset=['Jméno', 'Závod'], keep='last').pivot(index='Jméno', columns='Závod', values='Získané body').reset_index()
    
    df_zobr = pd.merge(df_unikatni, df_pivot_zobr, on='Jméno', how='left')
    df_zobr = pd.merge(df_zobr, df_skore, on='Jméno', how='left')
    df_zobr['Kategorie'] = df_zobr['Klub'].apply(urci_kategorii)
    
    df_zobr.sort_values(['Celkové body', 'Tie1_OB2', 'Tie2_OBmax', 'Tie3_Stredni'], ascending=[False, False, False, False], inplace=True)
    
    # Formátování čísel (zbavíme se .0)
    for col in POVOLENE_ZAVODY + ['Celkové body']:
        if col in df_zobr.columns:
            df_zobr[col] = df_zobr[col].apply(format_body)
    
    df_juniorky = df_zobr[df_zobr['Kategorie'] == 'Juniorky']
    df_juniori = df_zobr[df_zobr['Kategorie'] == 'Junioři']
    
    sloupce_skryt = ['Kategorie', 'Tie1_OB2', 'Tie2_OBmax', 'Tie3_Stredni']
    
    # Vyčištění tabulek před zobrazením
    df_juniorky_display = df_juniorky.drop(columns=sloupce_skryt).fillna("")
    df_juniori_display = df_juniori.drop(columns=sloupce_skryt).fillna("")
    
    # APLIKACE STYLU: Předáme tabulku do Styleru, který přeškrtne nejhorší závod
    styled_juniorky = df_juniorky_display.style.apply(style_dropped_race, axis=1)
    styled_juniori = df_juniori_display.style.apply(style_dropped_race, axis=1)
    
    sloupec_holky, sloupec_kluci = st.columns(2)
    with sloupec_holky:
        st.subheader("Dívky (Juniorky)")
        st.dataframe(styled_juniorky, width="stretch", hide_index=True)
    with sloupec_kluci:
        st.subheader("Chlapci (Junioři)")
        st.dataframe(styled_juniori, width="stretch", hide_index=True)
    
    st.divider()

st.subheader("Přidat / Upravit výsledky")
zalozka_pdf, zalozka_rucne = st.tabs(["📄 Nahrát z PDF", "✍️ Celková editovatelná tabulka"])

with zalozka_pdf:
    st.info("Nahrajte PDF (např. ze Sprintu). Data se uloží a okamžitě předepíší do tabulky v druhé záložce.")
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
                df_historie = df_historie[df_historie['Závod'] != nazev_zavodu_pdf]
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
                
                for zavod in POVOLENE
