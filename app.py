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
    df_historie = pd.read_csv(SOUBOR_DATA)
else:
    df_historie = pd.DataFrame(columns=["Závod", "Pořadí", "Jméno", "Klub", "Získané body"])

if not df_historie.empty:
    st.subheader("Průběžně uložená data v databázi")
    st.dataframe(df_historie, use_container_width=True)

st.subheader("Přidat nové výsledky")

# 2. ROZDĚLENÍ UI DO ZÁLOŽEK
# Vytvoříme dvě záložky pro různé metody zadávání
zalozka_pdf, zalozka_rucne = st.tabs(["📄 Nahrát z PDF", "✍️ Zadat ručně"])

# --- ZÁLOŽKA 1: NAHRÁVÁNÍ PDF ---
with zalozka_pdf:
    # Přidali jsme parametr 'key', aby se textová pole v různých záložkách nepletla
    nazev_zavodu_pdf = st.text_input("Zadejte název závodu (např. Sprint):", key="pdf_zavod")
    uploaded_file = st.file_uploader("Nahrajte PDF s výsledky", type="pdf")
    
    if uploaded_file is not None and st.button("Zpracovat PDF a uložit"):
        if not nazev_zavodu_pdf:
            st.error("Prosím, vyplňte nejprve název závodu.")
        else:
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
                                "Pořadí": poradi,
                                "Jméno": jmeno,
                                "Klub": klub,
                                "Získané body": body
                            })
            
            if zavodnici:
                df_nove = pd.DataFrame(zavodnici)
                df_komplet = pd.concat([df_historie, df_nove], ignore_index=True)
                df_komplet.to_csv(SOUBOR_DATA, index=False)
                st.success(f"Výsledky z PDF pro závod '{nazev_zavodu_pdf}' byly uloženy!")
                st.rerun()  # Aktualizuje stránku, abychom viděli nová data v tabulce nahoře
            else:
                st.warning("V PDF se nepodařilo najít žádné platné výsledky.")

# --- ZÁLOŽKA 2: RUČNÍ ZADÁVÁNÍ ---
with zalozka_rucne:
    st.info("Zde můžete ručně přidat výsledek jednoho závodníka.")
    
    # Použití st.form zajistí, že se data odešlou až po kliknutí na tlačítko (ne při psaní každého písmene)
    with st.form("rucni_zadani_form"):
        nazev_zavodu_rucne = st.text_input("Název závodu (např. Krátká trať):")
        jmeno_rucne = st.text_input("Jméno a příjmení:")
        klub_rucne = st.text_input("Klub (např. LPU0714):")
        # Výběr pořadí pomocí číselníku (minimum je 1. místo)
        poradi_rucne = st.number_input("Pořadí v závodě:", min_value=1, step=1)
        
        # Speciální tlačítko patřící k formuláři
        odeslat = st.form_submit_button("Uložit ručně zadaný výsledek")
        
        # Logika po kliknutí na tlačítko "Uložit"
        if odeslat:
            # Kontrola, zda uživatel vyplnil textová pole
            if not nazev_zavodu_rucne or not jmeno_rucne or not klub_rucne:
                st.error("Prosím, vyplňte všechna textová pole.")
            else:
                body_rucne = ziskej_body_za_umisteni(poradi_rucne)
                
                # Vytvoříme jednorádkovou tabulku pro zadaného závodníka
                novy_zavodnik = pd.DataFrame([{
                    "Závod": nazev_zavodu_rucne,
                    "Pořadí": poradi_rucne,
                    "Jméno": jmeno_rucne,
                    "Klub": klub_rucne,
                    "Získané body": body_rucne
                }])
                
                # Přidáme závodníka k historii a uložíme
                df_komplet = pd.concat([df_historie, novy_zavodnik], ignore_index=True)
                df_komplet.to_csv(SOUBOR_DATA, index=False)
                st.success(f"Závodník {jmeno_rucne} byl úspěšně přidán do databáze!")
                st.rerun()
