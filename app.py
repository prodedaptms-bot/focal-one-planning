# -*- coding: utf-8 -*-
import streamlit as st
import json, os
import pandas as pd
import datetime
from PIL import Image
import shutil

# --- CONFIGURATION INITIALE ---
st.set_page_config(layout="wide", page_title="Focal One Planner")

# Suppression de la marge haute par défaut pour coller le bandeau
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# Gestion du dossier de travail (compatible local et Cloud)
BASE_DIR = r"C:\Planning" if os.path.exists(r"C:\Planning") else os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "donnees_atelier.json")

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "techniciens": ["Thomas", "Lucas"], 
            "equipements": [], 
            "absences": [],
            "manquants": []
        }
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: 
            data = json.load(f)
            if "absences" not in data:
                data["absences"] = []
            if "manquants" not in data:
                data["manquants"] = []
            return data
    except: 
        return {"techniciens": ["Thomas", "Lucas"], "equipements": [], "absences": [], "manquants": []}

def save_data():
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f: 
        json.dump(st.session_state.data, f, ensure_ascii=False, indent=4)

if "data" not in st.session_state: st.session_state.data = load_data()

# --- INTERFACE HAUT DE PAGE ---
try:
    bandeau_path = os.path.join(BASE_DIR, 'fond_bandeau.jpg')
    if os.path.exists(bandeau_path):
        bandeau = Image.open(bandeau_path)
        st.image(bandeau, use_container_width=True)
except Exception:
    pass 

st.title("Focal One Planner")

tabs = st.tabs([
    "Dashboard", 
    "Historique", 
    "Planning", 
    "Congés", 
    "Équipe", 
    "Analyse des performances",
    "Analyse des manquants"
])

# 0. DASHBOARD
with tabs[0]:
    st.subheader("Vue d'ensemble - Temps Réel")
    
    equipements = st.session_state.data.get("equipements", [])
    maintenant = pd.to_datetime(datetime.datetime.now())
    aujourdhui = maintenant.date()
    
    conflits = []
    equipements_actifs = [e for e in equipements if e.get("statut") in ["Actif", "Bloqué"]]

    for i, m1 in enumerate(equipements_actifs):
        for m2 in equipements_actifs[i+1:]:
            if m1.get("tech") == m2.get("tech") and m1.get("tech"):
                try:
                    debut1 = pd.to_datetime(m1.get("debut")).date()
                    fin1 = pd.to_datetime(m1.get("fin_prevue")).date()
                    debut2 = pd.to_datetime(m2.get("debut")).date()
                    fin2 = pd.to_datetime(m2.get("fin_prevue")).date()
                    
                    if max(debut1, debut2) <= min(fin1, fin2):
                        conflits.append(f"⚠️ **{m1.get('tech')}** est assigné simultanément sur **{m1.get('id')}** et **{m2.get('id')}**")
                except:
                    pass

    if conflits:
        st.warning("### Conflits de planning détectés :")
        for c in conflits:
            st.markdown(c)
        st.info("💡 Pense à ajuster la date de fin ou à replanifier en cascade dans l'onglet Planning.")
        st.divider()

    en_cours = [e for e in equipements if e.get("statut") not in ["Terminé", "Annulé"]]
    # Tri chronologique des machines en cours par date de début
    en_cours = sorted(en_cours, key=lambda x: x.get("debut", ""))
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("En cours", len(en_cours))
    c2.metric("🛑 Bloquées", len([e for e in en_cours if e.get("statut") == "Bloqué"]))
    c3.metric("⚠️ En retard", len([e for e in en_cours if pd.to_datetime(e.get("fin_prevue")).date() < aujourdhui]))
    c4.metric("Terminées", len([e for e in equipements if e.get("statut") == "Terminé"]))
    
    st.divider()

    # --- SECTION GANTT DIRECTEMENT VISIBLE SUR LE DASHBOARD ---
    st.subheader("📊 Planning de Gantt de la production")
    if en_cours:
        data_gantt = []
        for e in en_cours:
            data_gantt.append({
                "Task": e.get("id"),
                "Start": e.get("debut"),
                "Finish": e.get("fin_prevue"),
                "Technicien": e.get("tech", "Non assigné"),
                "Statut": e.get("statut")
            })
        df_gantt = pd.DataFrame(data_gantt)
        try:
            import plotly.express as px
            fig = px.timeline(
                df_gantt, 
                x_start="Start", 
                x_end="Finish", 
                y="Task", 
                color="Technicien",
                hover_data=["Statut"]
            )
            fig.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as ex:
            st.info("Module Plotly non disponible, affichage du tableau de Gantt brut :")
            st.dataframe(df_gantt, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune donnée à afficher dans le Gantt (pas de machine en cours).")

    st.divider()

    st.write("### 📅 Suivi Visuel des Machines (Tri chronologique)")
    
    if en_cours:
        for e in en_cours:
            debut = pd.to_datetime(e["debut"])
            fin = pd.to_datetime(e["fin_prevue"])
            duree_totale = (fin - debut).total_seconds()
            duree_passee = (maintenant - debut).total_seconds()
            pourcentage = min(max(0, (duree_passee / duree_totale)), 1) if duree_totale > 0 else 0
            
            est_bloque = e.get("statut") == "Bloqué"
            commentaire = e.get('commentaire_retard')
            a_commentaire_retard = commentaire and commentaire.strip() != ""
            
            est_retard_reel = fin.date() < aujourdhui
            est_en_alerte = est_retard_reel or a_commentaire_retard
            est_alerte_proche = aujourdhui <= fin.date() <= (aujourdhui + datetime.timedelta(days=3))
            
            if est_bloque:
                style_m = ":red[**🛑 " + e['id'] + "**]"
                couleur_tech = ":red[" + str(e.get('tech', 'Non assigné')) + "]"
            elif est_en_alerte:
                style_m = ":orange[**⚠️ " + e['id'] + " (RETARD)**]"
                couleur_tech = ":orange[" + str(e.get('tech', 'Non assigné')) + "]"
            elif est_alerte_proche:
                style_m = ":violet[**⏳ " + e['id'] + " (PROCHE)**]"
                couleur_tech = ":violet[" + str(e.get('tech', 'Non assigné')) + "]"
            else:
                style_m = ":green[**✅ " + e['id'] + "**]"
                couleur_tech = str(e.get('tech', 'Non assigné'))
            
            col_m, col_t, col_p = st.columns([1, 1, 3])
            col_m.markdown(style_m)
            col_t.caption(f"Tech: {couleur_tech}")
            col_p.progress(pourcentage, text=f"Début: {e.get('debut')} ➔ Fin prévue: {e.get('fin_prevue')}")
            
            if commentaire and commentaire.strip():
                if est_bloque:
                    st.error(f"🛑 Blocage {e['id']}: {commentaire}")
                elif est_retard_reel:
                    st.warning(f"⚠️ Retard {e['id']}: {commentaire}")
                elif est_alerte_proche:
                    st.info(f"⏳ Alerte {e['id']}: {commentaire}")
            
            st.divider()
    else:
        st.info("Aucune intervention en cours.")

    st.subheader("Détail du Planning")
    data_to_display = []
    # Tri chronologique pour le tableau également
    equipements_tries = sorted(st.session_state.data["equipements"], key=lambda x: x.get("debut", ""))
    for e in equipements_tries:
        if e.get("statut") in ["Actif", "Bloqué"]:
            date_fin = datetime.datetime.strptime(e.get("fin_prevue"), '%Y-%m-%d').date()
            delta = (date_fin - aujourdhui).days
            jours_restants = max(0, delta)
            
            data_to_display.append({
                "Machine": e.get("id"),
                "Statut": e.get("statut"),
                "Technicien": e.get("tech"),
                "Début": e.get("debut"),
                "Fin prévue": e.get("fin_prevue"),
                "Jours restants": jours_restants,
                "Info Arrêt/Retard": e.get("cause_arret") or e.get("commentaire_retard") or "-"
            })
    
    if data_to_display:
        df = pd.DataFrame(data_to_display)
        st.dataframe(df, use_container_width=True, hide_index=True, column_config={"Jours restants": st.column_config.NumberColumn(format="%d jours")})
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger le planning (CSV)", csv, "planning.csv", "text/csv")
    else:
        st.write("Aucune machine en cours de production.")

# 1. HISTORIQUE & ADMINISTRATION (Sauvegarde, Import & RAZ)
with tabs[1]:
    st.subheader("⚠️ Administration & Sauvegarde de la Base")
    
    col_dl, col_up = st.columns(2)
    with col_dl:
        json_data = json.dumps(st.session_state.data, ensure_ascii=False, indent=4)
        st.download_button(
            label="💾 Télécharger la sauvegarde complète (JSON)",
            data=json_data,
            file_name=f"sauvegarde_atelier_{datetime.date.today().strftime('%Y%m%d')}.json",
            mime="application/json"
        )
    with col_up:
        uploaded_backup = st.file_uploader("Restaurer une sauvegarde (JSON)", type=["json"])
        if uploaded_backup is not None:
            try:
                restored_data = json.load(uploaded_backup)
                st.session_state.data = restored_data
                save_data()
                st.success("Base de données restaurée avec succès !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la restauration : {e}")

    st.divider()

    with st.expander("Gestion avancée / Remise à zéro"):
        mdp = st.text_input("Mot de passe administrateur", type="password", key="mdp_admin")
        if st.button("Remise à zéro avec sauvegarde automatique"):
            if mdp == "TonMotDePasse":
                archive_dir = os.path.join(BASE_DIR, "Archives")
                if not os.path.exists(archive_dir): os.makedirs(archive_dir)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(archive_dir, f"backup_{timestamp}.json")
                if os.path.exists(DATA_FILE): shutil.copy(DATA_FILE, backup_path)
                
                st.session_state.data = {"techniciens": ["Thomas", "Lucas"], "equipements": [], "absences": [], "manquants": []}
                save_data()
                st.success("Base archivée et réinitialisée avec succès !")
                st.rerun()
            elif mdp:
                st.error("Mot de passe incorrect")

    st.divider()
    st.subheader("Historique des interventions terminées")
    terminees = [e for e in st.session_state.data["equipements"] if e.get("statut"] == "Terminé"]
    if not terminees:
        st.info("Aucune intervention terminée.")
    else:
        for e in terminees:
            date_fin_affiche = e.get("fin_reelle", e.get("fin_prevue", "N/A"))
            st.write(f"✅ **{e['id']}** | Technicien : {e.get('tech')} | Fin réelle : {date_fin_affiche}")

# 2. PLANNING
with tabs[2]:
    st.subheader("Planification et Suivi")
    with st.form("ajout_machine", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        nom = c1.text_input("Nom de la machine")
        tech = c2.selectbox("Technicien", st.session_state.data["techniciens"])
        date_debut = c3.date_input("Date de début")
        duree = c3.number_input("Durée prévue (jours)", min_value=1, value=5)
        
        if st.form_submit_button("Ajouter à la production"):
            absences = st.session_state.data.get("absences", [])
            equipements = st.session_state.data.get("equipements", [])
            
            def est_disponible(date_test, tech_cible):
                if date_test.weekday() >= 5: return False
                for abs in absences:
                    if abs["tech"] == tech_cible:
                        if datetime.datetime.strptime(abs["debut"], '%Y-%m-%d').date() <= date_test <= datetime.datetime.strptime(abs["fin"], '%Y-%m-%d').date():
                            return False
                for e in equipements:
                    if e.get("tech") == tech_cible and e.get("statut"] == "Actif":
                        d_debut = datetime.datetime.strptime(e["debut"], '%Y-%m-%d').date()
                        d_fin = datetime.datetime.strptime(e["fin_prevue"], '%Y-%m-%d').date()
                        if d_debut <= date_test <= d_fin: return False
                return True

            date_reelle_debut = date_debut
            while not est_disponible(date_reelle_debut, tech):
                date_reelle_debut += datetime.timedelta(days=1)

            date_actuelle = date_reelle_debut
            jours_restants = int(duree)
            while jours_restants > 0:
                if est_disponible(date_actuelle, tech):
                    jours_restants -= 1
                if jours_restants > 0:
                    date_actuelle += datetime.timedelta(days=1)
            
            st.session_state.data["equipements"].append({
                "id": nom, "tech": tech, "statut": "Actif",
                "debut": str(date_reelle_debut), "fin_prevue": str(date_actuelle)
            })
            save_data()
            st.success(f"Planifié : {date_reelle_debut} au {date_actuelle}")
            st.rerun()

    st.subheader("Modifier / Ajuster une machine")
    machines_actives_list = [e['id'] for e in st.session_state.data["equipements"] if e.get("statut") in ["Actif", "Bloqué"]]
    if machines_actives_list:
        machine_id = st.selectbox("Choisir une machine", machines_actives_list)
        machine_concernee = next((e for e in st.session_state.data["equipements"] if e['id'] == machine_id), None)

        if machine_concernee:
            nouveau_statut = st.selectbox("Statut", ["Actif", "Bloqué", "Terminé"], index=["Actif", "Bloqué", "Terminé"].index(machine_concernee.get("statut", "Actif")))
            date_fin_actuelle = datetime.datetime.strptime(machine_concernee.get('fin_prevue'), '%Y-%m-%d').date()
            nouvelle_fin = st.date_input("Ajuster la date de fin prévue", value=date_fin_actuelle)
            commentaire = st.text_input("Motif du décalage / Commentaire", value=machine_concernee.get("commentaire_retard", ""))
            
            if st.button("Enregistrer les modifications"):
                machine_concernee["statut"] = nouveau_statut
                machine_concernee["fin_prevue"] = nouvelle_fin.strftime('%Y-%m-%d')
                machine_concernee["commentaire_retard"] = commentaire
                save_data()
                st.success(f"La machine {machine_id} a été mise à jour avec succès !")
                st.rerun()
    else:
        st.info("Aucune machine active à modifier.")

    st.divider()

    st.subheader("🔄 Replanification en cascade par Technicien")
    col_tech_casc, col_btn_casc = st.columns([2, 1])
    tech_a_replanifier = col_tech_casc.selectbox("Technicien concerné", st.session_state.data["techniciens"], key="tech_cascade")
    
    if col_btn_casc.button("⚡ Lancer la cascade"):
        machines_tech = sorted(
            [e for e in st.session_state.data["equipements"] if e.get("tech") == tech_a_replanifier and e.get("statut") in ["Actif", "Bloqué"]],
            key=lambda x: x["debut"]
        )
        if len(machines_tech) > 1:
            modifications_faites = 0
            for i in range(len(machines_tech) - 1):
                machine_actuelle = machines_tech[i]
                machine_suivante = machines_tech[i+1]
                
                fin_actuelle = datetime.datetime.strptime(machine_actuelle["fin_prevue"], '%Y-%m-%d').date()
                debut_suivant = datetime.datetime.strptime(machine_suivante["debut"], '%Y-%m-%d').date()
                d_fin_suiv = datetime.datetime.strptime(machine_suivante["fin_prevue"], '%Y-%m-%d').date()
                duree_suivante = max(1, (d_fin_suiv - debut_suivant).days)
                
                nouveau_debut = fin_actuelle + datetime.timedelta(days=1)
                while nouveau_debut.weekday() >= 5: nouveau_debut += datetime.timedelta(days=1)
                
                if debut_suivant != nouveau_debut:
                    nouvelle_fin = nouveau_debut
                    jours_a_ajouter = duree_suivante
                    while jours_a_ajouter > 0:
                        nouvelle_fin += datetime.timedelta(days=1)
                        if nouvelle_fin.weekday() < 5: jours_a_ajouter -= 1
                            
                    for e in st.session_state.data["equipements"]:
                        if e["id"] == machine_suivante["id"] and e.get("tech") == tech_a_replanifier:
                            e["debut"] = str(nouveau_debut)
                            e["fin_prevue"] = str(nouvelle_fin)
                            modifications_faites += 1
                            
            save_data()
            if modifications_faites > 0:
                st.success(f"Cascade exécutée ! {modifications_faites} machine(s) replanifiée(s).")
                st.rerun()
            else:
                st.info("Le planning est déjà parfaitement aligné.")
        else:
            st.info("Pas assez de machines en cours pour ce technicien.")
    st.divider()
    
    equipements_actives_triees = sorted(
        [e for e in st.session_state.data["equipements"] if e.get("statut") in ["Actif", "Bloqué"]],
        key=lambda x: x.get("debut", "")
    )
    
    for i, e in enumerate(st.session_state.data["equipements"]):
        if e.get("statut") in ["Actif", "Bloqué"]:
            m_id = e.get("id", "sans_nom")
            unique_key = f"{m_id}_{i}"
            cols = st.columns([2, 1, 1, 1, 0.5]) 
            cols[0].write(f"**{m_id}** ({e.get('statut')})")
            cols[0].caption(f"Tech: {e.get('tech')} | {e.get('debut')} ➔ {e.get('fin_prevue')}")
            
            if e["statut"] == "Actif":
                with cols[1].popover("🛑 STOP"):
                    cause = st.text_input("Raison de l'arrêt", key=f"cause_{unique_key}")
                    if st.button("Confirmer arrêt", key=f"stop_{unique_key}"):
                        if cause:
                            e["statut"] = "Bloqué"; e["cause_arret"] = cause
                            save_data(); st.rerun()
                        else: st.error("Veuillez saisir une raison.")
            else:
                if cols[1].button("▶️ Reprise", key=f"rep_{unique_key}"):
                    e["statut"] = "Actif"; e.pop("cause_arret", None); save_data(); st.rerun()
            
            with cols[2].popover("⏱️ Retard"):
                nb_jours = st.number_input("Jours de report", min_value=1, value=1, key=f"duree_{unique_key}")
                raison_retard = st.text_input("Raison du retard", key=f"raison_{unique_key}")
                if st.button("Confirmer retard", key=f"retard_{unique_key}"):
                    date_actuelle = datetime.datetime.strptime(e["fin_prevue"], '%Y-%m-%d').date()
                    e["fin_prevue"] = str(date_actuelle + datetime.timedelta(days=nb_jours))
                    e["commentaire_retard"] = raison_retard
                    save_data(); st.rerun()
            
            if cols[3].button("✅", key=f"term_{unique_key}", help="Marquer comme terminé"):
                e["statut"] = "Terminé"; e["fin_reelle"] = str(datetime.date.today())
                save_data(); st.rerun()

            if cols[4].button("🗑️", key=f"del_{unique_key}", help="Supprimer"):
                del st.session_state.data["equipements"][i]
                save_data(); st.rerun()

# 3. CONGÉS
with tabs[3]:
    st.subheader("Gestion des absences")
    if "absences" not in st.session_state.data: st.session_state.data["absences"] = []
    
    with st.form("ajout_absence", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tech = col1.selectbox("Technicien", st.session_state.data["techniciens"])
        date_deb = col2.date_input("Date de début")
        date_fin = col2.date_input("Date de fin")
        
        if st.form_submit_button("Enregistrer absence"):
            if date_fin >= date_deb:
                st.session_state.data["absences"].append({"tech": tech, "debut": str(date_deb), "fin": str(date_fin)})
                save_data(); st.success("Absence enregistrée !"); st.rerun()
            else: st.error("La date de fin doit être après la date de début.")

    st.divider()
    for i, abs in enumerate(st.session_state.data["absences"]):
        col1, col2 = st.columns([3, 1])
        col1.write(f"📅 **{abs['tech']}** : du {abs['debut']} au {abs['fin']}")
        if col2.button("Suppr", key=f"del_abs_{i}"):
            st.session_state.data["absences"].pop(i); save_data(); st.rerun()

# 4. ÉQUIPE
with tabs[4]:
    st.subheader("Gestion de l'équipe technique")
    for i, t in enumerate(list(st.session_state.data["techniciens"])):
        col1, col2 = st.columns([3, 1])
        col1.write(t)
        if col2.button("Suppr", key=f"del_tech_{i}"):
            st.session_state.data["techniciens"].remove(t)
            save_data(); st.rerun()
    
    new_t = st.text_input("Ajouter technicien")
    if st.button("Ajouter"):
        if new_t:
            st.session_state.data["techniciens"].append(new_t)
            save_data(); st.rerun()

# 5. ANALYSE DES PERFORMANCES
with tabs[5]:
    st.subheader("Pilotage et Performance Globale")
    
    equipements = st.session_state.data.get("equipements", [])
    terminees = [e for e in equipements if e.get("statut"] == "Terminé" and e.get("fin_reelle")]
    
    if not terminees:
        st.info("Terminez quelques interventions pour voir apparaître les indicateurs.")
    else:
        ecarts, lead_times, respectes = [], [], 0
        for e in terminees:
            d_debut = datetime.datetime.strptime(e["debut"], '%Y-%m-%d').date()
            d_reelle = datetime.datetime.strptime(e["fin_reelle"], '%Y-%m-%d').date()
            d_prevue = datetime.datetime.strptime(e["fin_prevue"], '%Y-%m-%d').date()
            
            lead_times.append((d_reelle - d_debut).days + 1)
            diff = (d_prevue - d_reelle).days
            ecarts.append(diff)
            if diff >= 0: respectes += 1
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Respect délais global", f"{(respectes / len(terminees)) * 100:.0f}%")
        moyen_ecart = sum(ecarts)/len(ecarts)
        col2.metric("Avance/Retard moy.", f"{moyen_ecart:.1f} j")
        col3.metric("Lead Time moy.", f"{sum(lead_times)/len(lead_times):.1f} j")
        col4.metric("Interventions", len(terminees))
        
        st.divider()
        df = pd.DataFrame({"Machine": [e["id"] for e in terminees], "Écart (j)": ecarts, "Lead Time (j)": lead_times}).set_index("Machine")
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Écarts (Avance vs Retard en jours)")
            st.bar_chart(df["Écart (j)"], color="#00cc96" if moyen_ecart >= 0 else "#ff4b4b")
        with c2:
            st.write("### Lead Time par machine")
            st.bar_chart(df["Lead Time (j)"], color="#3385ff")

# 6. ANALYSE DES MANQUANTS (ONGLET 7)
with tabs[6]:
    st.subheader("📦 Analyse des Manquants par OF")
    
    col_upload, col_raz = st.columns([3, 1])
    
    uploaded_file = col_upload.file_uploader("Importer le fichier des manquants (CSV ou Excel)", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_manquants_upl = pd.read_csv(uploaded_file)
            else:
                df_manquants_upl = pd.read_excel(uploaded_file)
            
            donnees_existantes = st.session_state.data.get("manquants", [])
            
            if donnees_existantes:
                df_existant = pd.DataFrame(donnees_existantes)
                df_cumule = pd.concat([df_existant, df_manquants_upl], ignore_index=True)
                df_cumule = df_cumule.drop_duplicates()
            else:
                df_cumule = df_manquants_upl
                
            st.session_state.data["manquants"] = df_cumule.to_dict(orient="records")
            save_data()
            st.success("Fichier importé et cumulé avec succès !")
            st.rerun()
        except Exception as ex:
            st.error(f"Erreur lors de la lecture du fichier : {ex}")

    if col_raz.button("🗑️ Remise à zéro manquants", help="Effacer toutes les données de manquants"):
        st.session_state.data["manquants"] = []
        save_data()
        st.success("Données des manquants réinitialisées.")
        st.rerun()

    st.divider()

    manquants_data = st.session_state.data.get("manquants", [])

    if not manquants_data:
        st.info("Aucun manquant enregistré. Importez un ou plusieurs fichiers pour commencer le cumul.")
    else:
        df_manq = pd.DataFrame(manquants_data)
        
        col_article = next((c for c in df_manq.columns if 'article' in c.lower() and 'désignation' not in c.lower() and 'designation' not in c.lower()), df_manq.columns[2] if len(df_manq.columns) > 2 else df_manq.columns[0])
        col_designation = next((c for c in df_manq.columns if 'désignation' in c.lower() or 'designation' in c.lower() or 'libelle' in c.lower()), df_manq.columns[3] if len(df_manq.columns) > 3 else col_article)
        col_of = next((c for c in df_manq.columns if any(k in c.lower() for k in ["ordre", "of", "code"])), df_manq.columns[1] if len(df_manq.columns) > 1 else df_manq.columns[0])
        col_qte = next((c for c in df_manq.columns if any(k in c.lower() for k in ["manquant", "qte", "quantite", "qty"])), df_manq.columns[-1])

        df_manq[col_qte] = pd.to_numeric(df_manq[col_qte], errors='coerce').fillna(0)

        if col_of in df_manq.columns:
            total_of_count = df_manq[col_of].nunique()
            moyenne_par_of = len(df_manq) / total_of_count if total_of_count > 0 else 0
        else:
            total_of_count = 1
            moyenne_par_of = len(df_manq)

        top_3 = (
            df_manq.groupby([col_article, col_designation])
            .size()
            .reset_index(name='Occurrences')
            .nlargest(3, 'Occurrences')
        )

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Nombre d'OF analysés (Cumul)", f"{total_of_count}")
        kpi2.metric("Lignes de manquants / OF (Moy)", f"{moyenne_par_of:.2f}")
        kpi3.metric("Références uniques en manquant", f"{df_manq[col_article].nunique()}")

        st.markdown("### 🏆 Top 3 des Articles les plus bloquants (sur le cumul des OF)")
        if not top_3.empty:
            cols_podium = st.columns(3)
            medailles = ["🥇", "🥈", "🥉"]
            for idx, row in top_3.reset_index(drop=True).iterrows():
                if idx < 3:
                    with cols_podium[idx]:
                        st.markdown(f"<div style='text-align: center; font-size: 20px;'>{medailles[idx]}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align: center; font-size: 13px; font-weight: bold;'>Réf: {row[col_article]}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align: center; font-size: 12px; color: #555;'>{row[col_designation]}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align: center; color: #ff4b4b; font-size: 16px; font-weight: bold;'>Présent {row['Occurrences']} fois</div>", unsafe_allow_html=True)
        
        st.divider()
        st.markdown(f"### 📋 Tableau Global Consolidé ({len(df_manq)} lignes de manquants)")
        st.dataframe(df_manq, use_container_width=True, hide_index=True)
