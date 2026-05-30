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

st.set_page_config(page_title="Nominace JMS 2026", layout="wide")

# ==========================================
# 1. POMOCNÉ FUNKCE PRO VÝPOČTY
# ==========================================

def urci_kategorii(klub):
    vyjimky_holky = ["UOL0740", "SJ10750", "SJI0750"]
    klub_upraveny = str(klub).strip()
    if klub_upraveny in vyjimky_holky:
        return "Juniorky"
    match = re.search(r"\d{4}$", klub_upraveny)
    if match and int(match.group(0)[2:4]) >= 50:
        return "Juniorky"
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
        if radek["Závod"] == "Dráhový test":
            body_draha += body
        else:
            body_ob.append(body)
            if radek["Závod"] == "Střední trať (krátká)":
                body_stredni = body
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

# ==========================================
# 2. FUNKCE PRO ZPRACOVÁNÍ TABULEK (DRY)
# ==========================================

def zobraz_zebricek(df_dlouhy):
    """Zobrazí finální obarvený žebříček z předaných dat."""
    if df_dlouhy.empty:
        st.info("Zatím nejsou uloženy žádné výsledky.")
        return

    df_skore = df_dlouhy.groupby('Jméno').apply(spocitej_skore_a_kriteria).reset_index()
    df_unikatni = df_dlouhy[['Jméno', 'Klub']].drop_duplicates()
    df_pivot_zobr = df_dlouhy.drop_duplicates(subset=['Jméno', 'Závod'], keep='last').pivot(index='Jméno', columns='Závod', values='Získané body').reset_index()
    
    df_zobr = pd.merge(df_unikatni, df_pivot_zobr, on='Jméno', how='left')
    df_zobr = pd.merge(df_zobr, df_skore, on='Jméno', how='left')
    df_zobr['Kategorie'] = df_zobr['Klub'].apply(urci_kategorii)
    df_zobr.sort_values(['Celkové body', 'Tie1_OB2', 'Tie2_OBmax', 'Tie3_Stredni'], ascending=[False, False, False, False], inplace=True)
    
    for zavod in POVOLENE_ZAVODY:
        if zavod not in df_zobr.columns: df_zobr[zavod] = ""
            
    for col in POVOLENE_ZAVODY + ['Celkové body']:
        if col in df_zobr.columns: df_zobr[col] = df_zobr[col].apply(format_body)
    
    df_juniorky = df_zobr[df_zobr['Kategorie'] == 'Juniorky'].copy()
    df_juniori = df_zobr[df_zobr['Kategorie'] == 'Junioři'].copy()
    
    if not df_juniorky.empty:
        df_juniorky = df_juniorky.reset_index(drop=True)
        df_juniorky.insert(0, 'Pořadí', range(1, len(df_juniorky) + 1))
        df_juniorky['Pořadí'] = df_juniorky['Pořadí'].astype(str) + "."

    if not df_juniori.empty:
        df_juniori = df_juniori.reset_index(drop=True)
        df_juniori.insert(0, 'Pořadí', range(1, len(df_juniori) + 1))
        df_juniori['Pořadí'] = df_juniori['Pořadí'].astype(str) + "."
    
    pozadovane_sloupce = ['Pořadí', 'Jméno', 'Klub', 'Celkové body'] + POVOLENE_ZAVODY
    sloupce_k_zobrazeni = [col for col in pozadovane_sloupce if col in df_juniorky.columns]
    
    styled_juniorky = df_juniorky[sloupce_k_zobrazeni].fillna("").style.apply(style_table, axis=1) if not df_juniorky.empty else pd.DataFrame()
    styled_juniori = df_juniori[sloupce_k_zobrazeni].fillna("").style.apply(style_table, axis=1) if not df_juniori.empty else pd.DataFrame()
    
    sloupec_holky, sloupec_kluci = st.columns(2)
    with sloupec_holky:
        st.subheader("Dívky (Juniorky)")
        if not styled_juniorky.data.empty: st.dataframe(styled_juniorky, width="stretch", hide_index=True)
        else: st.write("Žádná data.")
    with sloupec_kluci:
        st.subheader("Chlapci (Junioři)")
        if not styled_juniori.data.empty: st.dataframe(styled_juniori, width="stretch", hide_index=True)
        else: st.write("Žádná data.")

def priprav_siroke_tabulky(df_dlouhy):
    """Převede dlouhá data na široká (pro editaci)."""
    sloupce_vystup = ["Jméno", "Klub", "Celkové body"] + POVOLENE_ZAVODY
    if df_dlouhy.empty:
        prazdne = pd.DataFrame(columns=sloupce_vystup)
        return prazdne, prazdne
        
    df_unikatni = df_dlouhy[['Jméno', 'Klub']].drop_duplicates()
    df_pivot = df_dlouhy.drop_duplicates(subset=['Jméno', 'Závod'], keep='last').pivot(index='Jméno', columns='Závod', values='Pořadí/Čas').reset_index()
    df_master = pd.merge(df_unikatni, df_pivot, on='Jméno', how='left')
    
    for zavod in POVOLENE_ZAVODY:
        if zavod not in df_master.columns: df_master[zavod] = ""
            
    df_skore = df_dlouhy.groupby('Jméno').apply(spocitej_skore_a_kriteria).reset_index()
    df_master = pd.merge(df_master, df_skore, on='Jméno', how='left')
    df_master['Kategorie'] = df_master['Klub'].apply(urci_kategorii)
    df_master.sort_values(['Celkové body', 'Tie1_OB2', 'Tie2_OBmax', 'Tie3_Stredni'], ascending=[False, False, False, False], inplace=True)
    
    df_holky = df_master[df_master['Kategorie'] == 'Juniorky'][sloupce_vystup].fillna("")
    df_kluci = df_master[df_master['Kategorie'] == 'Junioři'][sloupce_vystup].fillna("")
    return df_holky, df_kluci

def vytvor_dlouhy_format(edited_komplet):
    """Převede širokou editovanou tabulku zpět na dlouhá databázová data a spočítá body."""
    nova_data = []
    for index, radek in edited_komplet.iterrows():
        jmeno = radek.get("Jméno", "")
        klub = radek.get("Klub", "")
        if not jmeno: continue
        
        for zavod in POVOLENE_ZAVODY:
            hodnota = str(radek.get(zavod, "")).strip()
            if hodnota.endswith(".0"): hodnota = hodnota[:-2]
            
            if hodnota != "" and hodnota != "nan":
                if zavod == "Dráhový test": body = ziskej_body_za_drahu(hodnota, klub)
                else: body = ziskej_body_za_umisteni(hodnota)
                    
                nova_data.append({
                    "Závod": zavod, "Pořadí/Čas": hodnota,
                    "Jméno": jmeno, "Klub": klub, "Získané body": body
                })
    return pd.DataFrame(nova_data)

# ==========================================
# 3. HLAVNÍ CHOD APLIKACE
# ==========================================

st.title("Nominační žebříček JMS 2026")

# Načtení OFICIÁLNÍCH dat
if os.path.exists(SOUBOR_DATA):
    df_historie = pd.read_csv(SOUBOR_DATA)
    if "Pořadí" in df_historie.columns and "Pořadí/Čas" not in df_historie.columns:
        df_historie.rename(columns={"Pořadí": "Pořadí/Čas"}, inplace=True)
else:
    df_historie = pd.DataFrame(columns=["Závod", "Pořadí/Čas", "Jméno", "Klub", "Získané body"])

# Vytvoření tří záložek
zalozka_oficialni, zalozka_piskoviste, zalozka_admin = st.tabs([
    "🏆 Oficiální žebříček", 
    "🧪 Pískoviště (Co kdyby...)", 
    "⚙️ Administrace dat"
])

# --- ZÁLOŽKA 1: OFICIÁLNÍ ŽEBŘÍČEK (Pouze pro čtení) ---
with zalozka_oficialni:
    st.write("Toto je oficiální žebříček potvrzený trenérem. Vidí ho všichni stejně.")
    zobraz_zebricek(df_historie)

# --- ZÁLOŽKA 2: PÍSKOVIŠTĚ (Real-time simulace) ---
with zalozka_piskoviste:
    st.info("💡 **Tady si můžeš zkoušet cokoliv!** Uprav si časy a pořadí přímo v tabulce. Žebříček se okamžitě přepočítá podle tvých dat. Tvé úpravy nikdo jiný neuvidí a ostrá data zůstanou v bezpečí.")
    
    df_h_sim, df_k_sim = priprav_siroke_tabulky(df_historie)
    
    st.write("### Uprav výsledky pro simulaci:")
    edited_h_sim = st.data_editor(df_h_sim, disabled=["Jméno", "Klub", "Celkové body"], width="stretch", hide_index=True, key="sim_h")
    edited_k_sim = st.data_editor(df_k_sim, disabled=["Jméno", "Klub", "Celkové body"], width="stretch", hide_index=True, key="sim_k")
    
    # Okamžitý real-time výpočet simulace!
    df_simulace_komplet = vytvor_dlouhy_format(pd.concat([edited_h_sim, edited_k_sim], ignore_index=True))
    
    st.divider()
    st.header("✨ Tvůj nasimulovaný žebříček")
    zobraz_zebricek(df_simulace_komplet)

# --- ZÁLOŽKA 3: ADMINISTRACE (Pod heslem) ---
with zalozka_admin:
    st.warning("Tato sekce slouží pouze trenérům pro nahrávání a ostré úpravy oficiálních dat.")
    heslo = st.text_input("Zadejte trenérské heslo:", type="password")
    
    # Heslo je nastaveno na 'trener'
    if heslo == "trener":
        st.success("Administrace odemčena.")
        
        st.subheader("1. Nahrát výsledky z PDF")
        nazev_zavodu_pdf = st.selectbox("Vyberte závod pro import:", POVOLENE_ZAVODY, key="pdf_zavod")
        uploaded_file = st.file_uploader("Nahrajte PDF s výsledky", type="pdf")
        
        if uploaded_file is not None and st.button("Zpracovat PDF a uložit do ostrých dat"):
            zavodnici = []
            zname_kluby = {r['Jméno']: r['Klub'] for _, r in df_historie.iterrows()} if not df_historie.empty else {}
            
            with pdfplumber.open(uploaded_file) as pdf:
                text_celeho_pdf = "".join([strana.extract_text() or "" for strana in pdf.pages])
                obsahuje_body_v_textu = bool(re.search(r"\d+\s*b\.", text_celeho_pdf))
                
                for strana in pdf.pages:
                    text = strana.extract_text(layout=True)
                    if not text: continue
                    
                    for radek in text.split('\n'):
                        if nazev_zavodu_pdf == "Dráhový test":
                            for match in re.finditer(r"([^\d\n]{5,}?)\s+(\d{1,2}:\d{2})\s+(\d+)", radek):
                                jmeno = re.sub(r"\s+", " ", match.group(1).strip())
                                cas_str = match.group(2)
                                body = int(match.group(3))
                                klub = zname_kluby.get(jmeno, "Neznámý")
                                
                                if jmeno.lower() not in ["juniorky", "junioři", "čas", "body"]:
                                    zavodnici.append({"Závod": nazev_zavodu_pdf, "Pořadí/Čas": cas_str, "Jméno": jmeno, "Klub": klub, "Získané body": body})
                        else:
                            klub_match = re.search(r"([A-Z]{3}\d{4})", radek)
                            if klub_match:
                                klub = klub_match.group(1)
                                poradi_match = re.search(r"(?:^|\s)(\d+)\.", radek)
                                poradi = int(poradi_match.group(1)) if poradi_match else ""
                                
                                if obsahuje_body_v_textu:
                                    body_match = re.search(r"(\d+)\s*b\.", radek)
                                    body = int(body_match.group(1)) if body_match else 0
                                else:
                                    body = ziskej_body_za_umisteni(poradi)
                                
                                ciste = re.sub(r"([A-Z]{3}\d{4})|\d+\s*b\.|(?i)\b(disk|dns)\b|[\d\+\.:]+", "", radek)
                                jmeno = re.sub(r"\s+", " ", ciste).strip()
                                
                                if jmeno:
                                    zavodnici.append({"Závod": nazev_zavodu_pdf, "Pořadí/Čas": str(poradi), "Jméno": jmeno, "Klub": klub, "Získané body": body})
            
            if zavodnici:
                df_nove = pd.DataFrame(zavodnici)
                if not df_historie.empty:
                    jmena_v_pdf = df_nove['Jméno'].tolist()
                    maska = (df_historie['Závod'] == nazev_zavodu_pdf) & (df_historie['Jméno'].isin(jmena_v_pdf))
                    df_historie = df_historie[~maska]
                df_komplet = pd.concat([df_historie, df_nove], ignore_index=True)
                df_komplet.to_csv(SOUBOR_DATA, index=False)
                st.success(f"Výsledky z PDF pro závod '{nazev_zavodu_pdf}' byly uloženy!")
                st.rerun()
            else:
                st.warning("V PDF se nepodařilo najít žádné platné výsledky.")

        st.divider()
        st.subheader("2. Ruční oprava ostrých dat")
        st.info("Zde můžete ručně přepsat oficiální výsledky. Pozor, po uložení tyto změny uvidí všichni.")
        
        df_h_admin, df_k_admin = priprav_siroke_tabulky(df_historie)
        edited_h_admin = st.data_editor(df_h_admin, disabled=["Jméno", "Klub", "Celkové body"], width="stretch", hide_index=True, key="admin_h")
        edited_k_admin = st.data_editor(df_k_admin, disabled=["Jméno", "Klub", "Celkové body"], width="stretch", hide_index=True, key="admin_k")
        
        if st.button("Uložit změny do OFICIÁLNÍ DATABÁZE"):
            df_ostre_nove = vytvor_dlouhy_format(pd.concat([edited_h_admin, edited_k_admin], ignore_index=True))
            df_ostre_nove.to_csv(SOUBOR_DATA, index=False)
            st.success("Oficiální data byla úspěšně přepsána!")
            st.rerun()
    elif heslo != "":
        st.error("Špatné heslo.")
