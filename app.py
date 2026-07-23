# -*- coding: utf-8 -*-
import streamlit as st
import json
import os
import pandas as pd
import datetime
import shutil
from PIL import Image
import base64
from collections import Counter
import plotly.express as px

# --- CONFIGURATION INITIALE ---
st.set_page_config(layout="wide", page_title="Focal One Planner")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "donnees_atelier.json")

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "techniciens": ["Thomas", "Lucas"], 
            "equipements": [], 
            "absences": [],
            "manquants": [
                {"of": "OF-10023", "article": "Carte mère V2", "quantite": 1},
                {"of": "OF-10023", "article": "Vis M4x10", "quantite": 12},
                {"of": "OF-10024", "article": "Carte mère V2", "quantite": 1},
                {"of": "OF-10025", "article": "Capteur optique", "quantite": 2},
                {"of": "OF-10025", "article": "Vis M4x10", "quantite": 4},
                {"of": "OF-10025", "article": "Connecteur RJ45", "quantite": 3}
            ]
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: 
            data = json.load(f)
            modified = False
            if "absences" not in data:
                data["absences"] = []
                modified = True
            if "manquants" not in data:
                data["manquants"] = [
                    {"of": "OF-10023", "article": "Carte mère V2", "quantite": 1},
                    {"of": "OF-10023", "article": "Vis M4x10", "quantite": 12},
                    {"of": "OF-10024", "article": "Carte mère V2", "quantite": 1},
                    {"of": "OF-10025", "article": "Capteur optique", "quantite": 2},
                    {"of": "OF-10025", "article": "Vis M4x10", "quantite": 4},
                    {"of": "OF-10025", "article": "Connecteur RJ45", "quantite": 3}
                ]
                modified = True
            
            if modified:
                with open(DATA_FILE, "w", encoding="utf-8") as fw:
                    json.dump(data, fw, ensure_ascii=False, indent=4)
            return data
    except: 
        return {"techniciens": ["Thomas", "Lucas"], "equipements": [], "absences": [], "manquants": []}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.data, f, ensure_ascii=False, indent=4)

if "data" not in st.session_state:
    st.session_state.data = load_data()

# --- INTERFACE HAUT DE PAGE ---
try:
    bandeau = Image.open(os.path.join(BASE_DIR, 'fond_bandeau.jpg'))
    st.image(bandeau, use_container_width=True)
except Exception as e:
    pass

st.title("Focal One Planner")

# --- BARRE LATÉRALE ---
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Gestion des données")

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        json_data = f.read()
    st.sidebar.download_button("📥 Télécharger la base JSON", json_data, "donnees_atelier.json", "application/json")

uploaded_file = st.sidebar.file_uploader("📤 Importer une sauvegarde (.json)", type=["json"])
if uploaded_file is not None:
    try:
        bytes_data = uploaded_file.getvalue()
        data_chargee = json.loads(bytes_data.decode("utf-8"))
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_chargee, f, ensure_ascii=False, indent=4)
        st.session_state.data = data_chargee
        st.sidebar.success("Import réussi !")
    except Exception as e:
        st.sidebar.error(f"Erreur : {e}")

# --- NAVIGATION PRINCIPALE (7 ONGLETS) ---
tabs = st.tabs([
    "Dashboard", 
    "Historique", 
    "Planning", 
    "Congés", 
    "Équipe", 
    "Analyse des performances",
    "🔍 Suivi des Manquants"
])

# 0. DASHBOARD
with tabs[0]:
    st.subheader("Vue d'ensemble - Temps Réel")
    equipements = st.session_state.data.get("equipements", [])
    maintenant = pd.to_datetime(datetime.datetime.now())
    aujourdhui = maintenant.date()
    
    en_cours = [e for e in equipements if e.get("statut") not in ["Terminé", "Annulé"]]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("En cours", len(en_cours))
    c2.metric("🛑 Bloquées", len([e for e in en_cours if e.get("statut") == "Bloqué"]))
    c3.metric("⚠️ En retard", len([e for e in en_cours if pd.to_datetime(e.get("fin_prevue")).date() < aujourdhui]))
    c4.metric("Terminées", len([e for e in equipements if e.get("statut") == "Terminé"]))

# 1. HISTORIQUE
with tabs[1]:
    st.subheader("Historique des interventions")
    terminees = [e for e in st.session_state.data["equipements"] if e.get("statut") == "Terminé"]
    if not terminees:
        st.info("Aucune intervention terminée.")
    else:
        for e in terminees:
            st.write(f"✅ **{e['id']}** | Fin : {e.get('fin_reelle', 'N/A')}")

# 2. PLANNING
with tabs[2]:
    st.subheader("Planification et Suivi")
    with st.form("ajout_machine", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        nom = c1.text_input("Nom de la machine (ou OF)")
        tech = c2.selectbox("Technicien", st.session_state.data["techniciens"])
        date_debut = c3.date_input("Date de début")
        duree = c3.number_input("Durée (jours)", min_value=1, value=14)
        if st.form_submit_button("Ajouter à la production"):
            st.session_state.data["equipements"].append({
                "id": nom, "tech": tech, "statut": "Actif",
                "debut": str(date_debut),
                "fin_prevue": str(date_debut + datetime.timedelta(days=int(duree))),
                "duree_jours": int(duree)
            })
            save_data()
            st.success("Ajouté !")
            st.rerun()

# 3. CONGÉS
with tabs[3]:
    st.subheader("Gestion des absences")
    if "absences" not in st.session_state.data:
        st.session_state.data["absences"] = []
    with st.form("ajout_absence", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tech = col1.selectbox("Technicien", st.session_state.data["techniciens"])
        date_deb = col2.date_input("Date de début")
        date_fin = col2.date_input("Date de fin")
        if st.form_submit_button("Enregistrer absence"):
            st.session_state.data["absences"].append({"tech": tech, "debut": str(date_deb), "fin": str(date_fin)})
            save_data()
            st.rerun()

# 4. ÉQUIPE
with tabs[4]:
    st.subheader("Gestion des Techniciens")
    for i, t in enumerate(list(st.session_state.data["techniciens"])):
        col1, col2 = st.columns([3, 1])
        col1.write(t)
        if col2.button("Suppr", key=f"del_tech_{i}"):
            st.session_state.data["techniciens"].remove(t)
            save_data()
            st.rerun()
    new_t = st.text_input("Ajouter technicien")
    if st.button("Ajouter") and new_t:
        st.session_state.data["techniciens"].append(new_t)
        save_data()
        st.rerun()

# 5. ANALYSE DES PERFORMANCES
with tabs[5]:
    st.subheader("Pilotage et Performance de l'Atelier")
    st.info("Retrouvez ici les indicateurs globaux de production, lead times et causes de blocage.")

# 6. SUIVI DES MANQUANTS (NOUVEL ONGLET DÉDIÉ)
with tabs[6]:
    st.subheader("📦 Téléversement & Suivi des Pièces Manquantes par OF")
    
    with st.container():
        st.markdown("### 📤 Importer le fichier de manquants")
        uploaded_manquants = st.file_uploader("Sélectionner un fichier (CSV ou Excel)", type=["csv", "xlsx", "xls"], key="file_manquants_tab6")
        
        if uploaded_manquants is not None:
            try:
                if uploaded_manquants.name.endswith('.csv'):
                    df_m = pd.read_csv(uploaded_manquants)
                else:
                    df_m = pd.read_excel(uploaded_manquants)
                
                df_m.columns = [str(c).strip().lower() for c in df_m.columns]
                st.session_state.data["manquants"] = df_m.to_dict(orient="records")
                save_data()
                st.success(f"Fichier de manquants importé avec succès ({len(df_m)} lignes) !")
                st.rerun()
            except Exception as ex:
                st.error(f"Erreur de lecture du fichier : {ex}")

    st.divider()

    manquants_data = st.session_state.data.get("manquants", [])
    
    if manquants_data:
        df_manq = pd.DataFrame(manquants_data)
        
        cols_lower = df_manq.columns.tolist()
        col_of = next((c for c in cols_lower if 'of' in c or 'machine' in c or 'ordre' in c), cols_lower[0])
        col_article = next((c for c in cols_lower if 'article' in c or 'designation' in c or 'piece' in c), cols_lower[1] if len(cols_lower)>1 else cols_lower[0])
        
        total_lignes_manquants = len(df_manq)
        nb_of_concernes = df_manq[col_of].nunique() if col_of in df_manq.columns else 1
        moyenne_manquants_par_of = total_lignes_manquants / nb_of_concernes if nb_of_concernes > 0 else 0
        
        st.markdown("### 📊 Indicateurs clés")
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Total lignes manquants", total_lignes_manquants)
        c_m2.metric("OF impactés", nb_of_concernes)
        c_m3.metric("Moy. manquants / OF", f"{moyenne_manquants_par_of:.1f}")
        
        st.divider()
        
        st.markdown("### 🏆 Top 3 des pièces / articles manquants")
        if col_article in df_manq.columns:
            top_articles = df_manq[col_article].value_counts().head(3)
            col_podium_m = st.columns(3)
            medailles = ["🥇", "🥈", "🥉"]
            for i, (article, count) in enumerate(top_articles.items()):
                with col_podium_m[i]:
                    st.markdown(f"<div style='text-align: center; font-size: 22px;'>{medailles[i]}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align: center; font-size: 14px; font-weight: bold;'>{article}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align: center; color: #ff4b4b; font-size: 16px;'>{count} fois</div>", unsafe_allow_html=True)
        
        st.divider()
        st.markdown("### 📋 Détail complet des manquants chargés")
        st.dataframe(df_manq, use_container_width=True, hide_index=True)
    else:
        st.info("💡 Aucun fichier de manquants chargé pour le moment. Utilise l'outil d'import ci-dessus.")
