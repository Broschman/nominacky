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
def ziskej_body_za_umisteni(poradi):
    if pd.isna(poradi): return 0
    try:
        poradi = int(poradi)
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
        
    je_zena = False
    match = re.search(r"\d{4}$", str(klub).strip())
    if match:
        mesic = int(match.group(0)[2:4])
        if mesic > 50:
            je_zena = True

    if je_zena: 
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

# 1. NAČTENÍ HISTORIE A VYTVOŘENÍ SLOVNÍKU ZÁVODNÍKŮ
if os.path.exists(SOUBOR_DATA):
    df_historie = pd.read_csv(SOUBOR_DATA)
else:
    df_historie = pd.DataFrame(columns=["Závod", "Pořadí/Čas", "Jméno", "Klub", "Získané body"])

# Extrakce unikátních závodníků (Mapování: Jméno -> Klub)
slovnik_zavodniku = {}
if not df_historie.empty:
    for index, radek in df_historie.iterrows():
        # Uložíme si jméno a k němu odpovídající klub
        slovnik_zavodniku[radek["Jméno"]] = radek["Klub"]

# Seznam jmen pro rolovací nabídku
seznam_jmen = list(slovnik_zavodniku.keys())
# Seřadíme jména podle abecedy pro lepší přehlednost
seznam_jmen.sort()

if not df_historie.empty:
    st.subheader("Průběžně uložená data v databázi")
    st.dataframe(df_historie, use_container_width=True)

st.subheader("Přidat nové výsledky")

zalozka_pdf, zalozka_rucne = st.tabs(["📄 Nahrát z PDF", "✍️ Hromadné zadání (jako Excel)"])

# --- ZÁLOŽKA 1: NAHRÁVÁNÍ PDF ---
with zalozka_pdf:
    st.info("Při prvním nahrání PDF (např. Sprint) se závodníci automaticky uloží a budou k dispozici pro ruční zadávání v druhé záložce.")
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
            df_komplet = pd.concat([df_historie, df_nove], ignore_index=True)
            df_komplet.to_csv(SOUBOR_DATA, index=False)
            st.success(f"Výsledky z PDF pro závod '{nazev_zavodu_pdf}' byly uloženy!")
            st.rerun()
        else:
            st.warning("V PDF se nepodařilo najít žádné platné výsledky.")

# --- ZÁLOŽKA 2: RUČNÍ (HROMADNÉ) ZADÁVÁNÍ ---
with zalozka_rucne:
    if not seznam_jmen:
        st.warning("Zatím neznám žádné závodníky. Nahrajte prosím nejprve výsledky prvního závodu v PDF, abych si zapamatoval jména a kluby.")
    else:
        st.info("Vyberte jméno ze seznamu. Klub bude přidělen automaticky na pozadí podle naší databáze!")
        
        nazev_zavodu_rucne = st.selectbox("Vyberte závod pro ruční zadání:", POVOLENE_ZAVODY, key="rucne_zavod")
        
        # Ostranili jsme sloupec "Klub", uživatel ho nemusí zadávat
        if nazev_zavodu_rucne == "Dráhový test":
            df_template = pd.DataFrame(columns=["Jméno", "Čas (MM:SS)"])
        else:
            df_template = pd.DataFrame(columns=["Jméno", "Pořadí"])

        # 2. NASTAVENÍ SLOUPCE "Jméno" JAKO VÝBĚROVÉHO SEZNAMU (Selectbox)
        konfigurace_sloupcu = {
            "Jméno": st.column_config.SelectboxColumn(
                "Jméno závodníka",
                help="Vyberte jméno z nabídky",
                width="medium",
                options=seznam_jmen,
                required=True
            )
        }

        edited_df = st.data_editor(
            df_template, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config=konfigurace_sloupcu
        )
        
        if st.button("Uložit všechny výsledky z tabulky"):
            edited_df.dropna(how='all', inplace=True)
            
            if edited_df.empty:
                st.warning("Tabulka je prázdná, není co uložit.")
            else:
                zavodnici_rucne = []
                for index, radek in edited_df.iterrows():
                    jmeno = radek.get("Jméno", "")
                    
                    if pd.notna(jmeno) and jmeno != "":
                        # 3. AUTOMATICKÉ DOPLNĚNÍ KLUBU Z NAŠEHO SLOVNÍKU
                        klub = slovnik_zavodniku.get(jmeno, "Neznámý")
                        
                        if nazev_zavodu_rucne == "Dráhový test":
                            cas_str = str(radek.get("Čas (MM:SS)", ""))
                            body = ziskej_body_za_drahu(cas_str, klub)
                            hodnota_zaznamu = cas_str
                        else:
                            poradi = radek.get("Pořadí")
                            body = ziskej_body_za_umisteni(poradi)
                            hodnota_zaznamu = str(poradi)

                        zavodnici_rucne.append({
                            "Závod": nazev_zavodu_rucne,
                            "Pořadí/Čas": hodnota_zaznamu,
                            "Jméno": jmeno,
                            "Klub": klub,
                            "Získané body": body
                        })
                
                if zavodnici_rucne:
                    df_nove = pd.DataFrame(zavodnici_rucne)
                    df_komplet = pd.concat([df_historie, df_nove], ignore_index=True)
                    df_komplet.to_csv(SOUBOR_DATA, index=False)
                    st.success(f"Všechny výsledky pro '{nazev_zavodu_rucne}' byly úspěšně uloženy!")
                    st.rerun()
