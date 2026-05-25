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

# --- POMOCNÉ FUNKCE PRO VÝPOČET BODŮ ---
def urci_kategorii(klub):
    match = re.search(r"\d{4}$", str(klub).strip())
    if match:
        mesic = int(match.group(0)[2:4])
        if mesic > 50:
            return "Juniorky"
    return "Junioři"

def ziskej_body_za_umisteni(poradi):
    if pd.isna(poradi) or str(poradi).strip() == "": return 0
    try:
        poradi = int(float(poradi)) # Ochrana proti desetinným číslům jako '1.0'
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

st.title("Nominační žebříček JMS 2026")
st.write("Aplikace ukládá průběžné výsledky. Po zavření okna o data nepřijdete.")

# NAČTENÍ HISTORIE
if os.path.exists(SOUBOR_DATA):
    df_historie = pd.read_csv(SOUBOR_DATA)
else:
    df_historie = pd.DataFrame(columns=["Závod", "Pořadí/Čas", "Jméno", "Klub", "Získané body"])

# --- ZOBRAZENÍ TABULEK (HOLKY / KLUCI) ---
if not df_historie.empty:
    st.header("Průběžně uložená data v databázi")
    
    df_historie_zobr = df_historie.copy()
    df_historie_zobr['Kategorie'] = df_historie_zobr['Klub'].apply(urci_kategorii)
    
    df_juniorky = df_historie_zobr[df_historie_zobr['Kategorie'] == 'Juniorky']
    df_juniori = df_historie_zobr[df_historie_zobr['Kategorie'] == 'Junioři']
    
    sloupec_holky, sloupec_kluci = st.columns(2)
    with sloupec_holky:
        st.subheader("Dívky (Juniorky)")
        st.dataframe(df_juniorky.drop(columns=['Kategorie']), use_container_width=True, hide_index=True)
    with sloupec_kluci:
        st.subheader("Chlapci (Junioři)")
        st.dataframe(df_juniori.drop(columns=['Kategorie']), use_container_width=True, hide_index=True)
    
    st.divider()

st.subheader("Přidat / Upravit výsledky")

zalozka_pdf, zalozka_rucne = st.tabs(["📄 Nahrát z PDF", "✍️ Celková editovatelná tabulka"])

# --- ZÁLOŽKA 1: NAHRÁVÁNÍ PDF ---
with zalozka_pdf:
    st.info("Při prvním nahrání PDF (např. Sprint) se závodníci uloží. Ostatní závody pak můžete jen dopsat ve druhé záložce.")
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
            # Pokud už výsledek ze závodu existuje, přepíšeme ho (aby se PDF neduplikovalo)
            if not df_historie.empty:
                df_historie = df_historie[df_historie['Závod'] != nazev_zavodu_pdf]
            df_komplet = pd.concat([df_historie, df_nove], ignore_index=True)
            df_komplet.to_csv(SOUBOR_DATA, index=False)
            st.success(f"Výsledky z PDF pro závod '{nazev_zavodu_pdf}' byly uloženy!")
            st.rerun()
        else:
            st.warning("V PDF se nepodařilo najít žádné platné výsledky.")

# --- ZÁLOŽKA 2: CELKOVÁ EDITOVATELNÁ TABULKA ---
with zalozka_rucne:
    if df_historie.empty:
        st.warning("Zatím neznám žádné závodníky. Nahrajte prosím nejprve výsledky prvního závodu v PDF.")
    else:
        st.info("Zde vidíte všechny závodníky. Doplňte chybějící časy (ve formátu MM:SS) nebo umístění a vše najednou uložte. Jméno a Klub jsou uzamčeny.")
        
        # 1. Extrakce unikátních závodníků
        df_unikatni = df_historie[['Jméno', 'Klub']].drop_duplicates()
        
        # 2. Vytvoření široké (kontingenční) tabulky pro snadnou editaci
        df_pivot = df_historie.pivot_table(index='Jméno', columns='Závod', values='Pořadí/Čas', aggfunc='first').reset_index()
        
        # Spojení jmen+klubů se závody
        df_master = pd.merge(df_unikatni, df_pivot, on='Jméno', how='left')
        
        # Zajištění, že všechny sloupce závodů existují, i když se ještě neběžely
        for zavod in POVOLENE_ZAVODY:
            if zavod not in df_master.columns:
                df_master[zavod] = ""
                
        # Uspořádání sloupců a nahrazení chybějících hodnot (NaN) za prázdný text
        sloupce = ["Jméno", "Klub"] + POVOLENE_ZAVODY
        df_master = df_master[sloupce].fillna("")
        df_master.sort_values("Jméno", inplace=True)

        # 3. Zobrazení editovatelné tabulky
        edited_df = st.data_editor(
            df_master,
            # Zakážeme úpravu těchto dvou sloupců, aby si uživatel nerozbil databázi
            disabled=["Jméno", "Klub"],
            use_container_width=True,
            hide_index=True
        )
        
        # 4. Uložení - rozsekání široké tabulky zpět na dlouhý databázový formát
        if st.button("Uložit všechny úpravy z tabulky"):
            nova_data = []
            
            for index, radek in edited_df.iterrows():
                jmeno = radek["Jméno"]
                klub = radek["Klub"]
                
                # Projdeme všechny 4 možné závody u daného člověka
                for zavod in POVOLENE_ZAVODY:
                    hodnota = str(radek.get(zavod, "")).strip()
                    
                    if hodnota != "" and hodnota != "nan":
                        # Výpočet bodů za daný závod
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
            
            # Kompletní přepsání databáze novými, aktuálními daty z tabulky
            df_nove_komplet = pd.DataFrame(nova_data)
            df_nove_komplet.to_csv(SOUBOR_DATA, index=False)
            st.success("Všechny změny byly úspěšně uloženy!")
            st.rerun()
