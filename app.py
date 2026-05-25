import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# Název našeho databázového souboru
SOUBOR_DATA = "vysledky_jms.csv"

# Funkce pro přidělení bodů podle pravidel
def ziskej_body_za_umisteni(poradi):
    if poradi == 1: return 11
    elif poradi == 2: return 9
    elif poradi == 3: return 7
    elif poradi == 4: return 5
    elif poradi == 5: return 3
    elif poradi == 6: return 2
    elif poradi == 7: return 1
    else: return 0  # 8. místo a horší je za 0 bodů

st.title("Nominační žebříček JMS 2026")
st.write("Aplikace ukládá průběžné výsledky. Po zavření okna o data nepřijdete.")

# 1. NAČTENÍ HISTORICKÝCH DAT Z CSV
if os.path.exists(SOUBOR_DATA):
    # Pokud soubor existuje, načteme ho
    df_historie = pd.read_csv(SOUBOR_DATA)
else:
    # Pokud neexistuje (první spuštění), vytvoříme prázdnou tabulku s definovanými sloupci
    df_historie = pd.DataFrame(columns=["Závod", "Pořadí", "Jméno", "Klub", "Získané body"])

# Zobrazení aktuálně uložených dat na webu
if not df_historie.empty:
    st.subheader("Průběžně uložená data v databázi")
    st.dataframe(df_historie, use_container_width=True)

# 2. NAHRÁNÍ NOVÝCH VÝSLEDKŮ
st.subheader("Přidat nové výsledky")
nazev_zavodu = st.text_input("Zadejte název závodu (např. Sprint, Krátká trať):")
uploaded_file = st.file_uploader("Nahrajte PDF s výsledky", type="pdf")

# Tlačítko pro spuštění zpracování
if uploaded_file is not None and st.button("Zpracovat a uložit do databáze"):
    if not nazev_zavodu:
        st.error("Prosím, vyplňte nejprve název závodu.")
    else:
        zavodnici = []
        
        # Otevření a čtení PDF pomocí pdfplumber
        with pdfplumber.open(uploaded_file) as pdf:
            for strana in pdf.pages:
                text = strana.extract_text()
                
                # Zpracování textu po řádcích
                for radek in text.split('\n'):
                    match = re.search(r"^(\d+)\.\s+(.*?)\s+([A-Z]{3}\d{4})", radek)
                    
                    if match:
                        poradi = int(match.group(1))
                        jmeno = match.group(2).strip()
                        klub = match.group(3)
                        body = ziskej_body_za_umisteni(poradi)
                        
                        # Uložení závodníka včetně názvu závodu
                        zavodnici.append({
                            "Závod": nazev_zavodu,
                            "Pořadí": poradi,
                            "Jméno": jmeno,
                            "Klub": klub,
                            "Získané body": body
                        })
        
        # 3. ULOŽENÍ NOVÝCH DAT
        if zavodnici:
            df_nove = pd.DataFrame(zavodnici)
            # Spojení starých dat (df_historie) s novými daty (df_nove)
            df_komplet = pd.concat([df_historie, df_nove], ignore_index=True)
            
            # Přepsání CSV souboru kompletními daty
            df_komplet.to_csv(SOUBOR_DATA, index=False)
            
            st.success(f"Výsledky pro závod '{nazev_zavodu}' byly úspěšně uloženy!")
            # Okamžitý restart aplikace pro zobrazení aktualizované tabulky
            st.rerun()
        else:
            st.warning("V PDF se nepodařilo najít žádné platné výsledky.")
