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
    # Převod pořadí na body podle nominačních kritérií OB
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
    # 1. Převod času na sekundy (např. z "10:45" na 645 sekund)
    if not isinstance(cas_str, str) or ":" not in cas_str:
        return 0
    
    casti = cas_str.split(':')
    try:
        sekundy = int(casti[0]) * 60 + int(casti[1])
    except ValueError:
        return 0
        
    # 2. Zjištění pohlaví z registračního čísla (např. VRL0852 -> 52 znamená žena)
    je_zena = False
    match = re.search(r"\d{4}$", str(klub).strip())
    if match:
        mesic = int(match.group(0)[2:4])
        if mesic > 50:
            je_zena = True

    # 3. Bodovací tabulky z PDF kritérií
    if je_zena: # Kategorie D (do 10:45 = 7b atd.)
        if sekundy <= 645: return 7       # do 10:45
        elif sekundy <= 655: return 6     # 10:46 - 10:55
        elif sekundy <= 665: return 5     # 10:56 - 11:05
        elif sekundy <= 675: return 4     # 11:06 - 11:15
        elif sekundy <= 685: return 3     # 11:16 - 11:25
        elif sekundy <= 695: return 2     # 11:26 - 11:35
        elif sekundy <= 705: return 1     # 11:36 - 11:45
        else: return 0
    else: # Kategorie H (do 8:55 = 7b atd.)
        if sekundy <= 535: return 7       # do 8:55
        elif sekundy <= 545: return 6     # 8:56 - 9:05
        elif sekundy <= 555: return 5     # 9:06 - 9:15
        elif sekundy <= 565: return 4     # 9:16 - 9:25
        elif sekundy <= 575: return 3     # 9:26 - 9:35
        elif sekundy <= 585: return 2     # 9:36 - 9:45
        elif sekundy <= 595: return 1     # 9:46 - 9:55
        else: return 0

st.title("Nominační žebříček JMS 2026")
st.write("Aplikace ukládá průběžné výsledky. Po zavření okna o data nepřijdete.")

# NAČTENÍ HISTORIE
if os.path.exists(SOUBOR_DATA):
    df_historie = pd.read_csv(SOUBOR_DATA)
else:
    df_historie = pd.DataFrame(columns=["Závod", "Pořadí/Čas", "Jméno", "Klub", "Získané body"])

if not df_historie.empty:
    st.subheader("Průběžně uložená data v databázi")
    st.dataframe(df_historie, use_container_width=True)

st.subheader("Přidat nové výsledky")

# Přejmenovali jsme záložku, aby bylo jasné, k čemu slouží
zalozka_pdf, zalozka_rucne = st.tabs(["📄 Nahrát z PDF", "✍️ Hromadné zadání (jako Excel)"])

# --- ZÁLOŽKA 1: NAHRÁVÁNÍ PDF ---
with zalozka_pdf:
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
                        
                        # PDF používáme primárně pro OB, takže počítáme body za umístění
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
    st.info("Vyberte závod a vložte výsledky přímo do tabulky. Můžete přidat libovolný počet řádků kliknutím pod tabulku.")
    
    nazev_zavodu_rucne = st.selectbox("Vyberte závod pro ruční zadání:", POVOLENE_ZAVODY, key="rucne_zavod")
    
    # Připravíme správný formát prázdné tabulky podle vybraného závodu
    if nazev_zavodu_rucne == "Dráhový test":
        df_template = pd.DataFrame(columns=["Čas (MM:SS)", "Jméno", "Klub"])
        st.warning("Nezapomeňte zadávat klub s plným registračním číslem (např. VRL0852), aplikace z něj pozná, jestli jde o kategorii D nebo H!")
    else:
        df_template = pd.DataFrame(columns=["Pořadí", "Jméno", "Klub"])

    # Klíčový prvek: data_editor (hromadné zadávání)
    edited_df = st.data_editor(df_template, num_rows="dynamic", use_container_width=True)
    
    if st.button("Uložit všechny výsledky z tabulky"):
        # Odstraníme z tabulky prázdné řádky, které uživatel nechal nevyplněné
        edited_df.dropna(how='all', inplace=True)
        
        if edited_df.empty:
            st.warning("Tabulka je prázdná, není co uložit.")
        else:
            zavodnici_rucne = []
            # Projdeme tabulku řádek po řádku a vypočítáme body
            for index, radek in edited_df.iterrows():
                jmeno = radek.get("Jméno", "")
                klub = radek.get("Klub", "")
                
                # Zpracování podle toho, o jaký závod jde
                if nazev_zavodu_rucne == "Dráhový test":
                    cas_str = str(radek.get("Čas (MM:SS)", ""))
                    body = ziskej_body_za_drahu(cas_str, klub)
                    hodnota_zaznamu = cas_str
                else:
                    poradi = radek.get("Pořadí")
                    body = ziskej_body_za_umisteni(poradi)
                    hodnota_zaznamu = str(poradi)

                # Přidáme do seznamu pouze řádky s vyplněným jménem
                if pd.notna(jmeno) and jmeno != "":
                    zavodnici_rucne.append({
                        "Závod": nazev_zavodu_rucne,
                        "Pořadí/Čas": hodnota_zaznamu,
                        "Jméno": jmeno,
                        "Klub": klub,
                        "Získané body": body
                    })
            
            # Uložení kompletního seznamu
            if zavodnici_rucne:
                df_nove = pd.DataFrame(zavodnici_rucne)
                df_komplet = pd.concat([df_historie, df_nove], ignore_index=True)
                df_komplet.to_csv(SOUBOR_DATA, index=False)
                st.success(f"Všechny výsledky pro '{nazev_zavodu_rucne}' byly úspěšně uloženy!")
                st.rerun()
