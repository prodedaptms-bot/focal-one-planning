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

# Détecte automatiquement le dossier du projet, que ce soit sur ton PC ou sur Streamlit Cloud
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "donnees_atelier.json")

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "techniciens": ["Thomas", "Lucas"], 
            "equipements": [], 
            "absences": [] 
        }
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: 
            data = json.load(f)
            if "absences" not in data:
                data["absences"] = []
            return data
    except: 
        return {"techniciens": ["Thomas", "Lucas"], "equipements": [], "absences": []}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(st.session_state.data, f)

if "data" not in st.session_state: st.session_state.data = load_data()

# --- INTERFACE HAUT DE PAGE ---
try:
    bandeau = Image.open(os.path.join(BASE_DIR, 'fond_bandeau.jpg'))
    st.image(bandeau, use_container_width=True)
except Exception as e:
    st.warning(f"Image de bandeau non trouvée dans {BASE_DIR}")

st.title("Focal One Planner")

tabs = st.tabs(["Dashboard", "Historique", "Planning", "Congés", "Équipe", "Analyse des performances"])

# 0. DASHBOARD
with tabs[0]:
    st.subheader("Vue d'ensemble - Temps Réel")
    
    equipements = st.session_state.data.get("equipements", [])
    maintenant = pd.to_datetime(datetime.datetime.now())
    aujourdhui = maintenant.date()
    
    # ---------------------------------------------------------
    # 1. DÉTECTION DES CONFLITS PLANNING (Même technicien en double)
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # 2. MÉTRIQUES
    # ---------------------------------------------------------
    en_cours = [e for e in equipements if e.get("statut") not in ["Terminé", "Annulé"]]
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("En cours", len(en_cours))
    c2.metric("🛑 Bloquées", len([e for e in en_cours if e.get("statut") == "Bloqué"]))
    c3.metric("⚠️ En retard", len([e for e in en_cours if pd.to_datetime(e.get("fin_prevue")).date() < aujourdhui]))
    c4.metric("Terminées", len([e for e in equipements if e.get("statut") == "Terminé"]))
    
    st.divider()

    # ---------------------------------------------------------
    # 3. SUIVI VISUEL DES MACHINES (Triées chronologiquement par ID)
    # ---------------------------------------------------------
    st.write("### 📅 Suivi Visuel des Machines")
    
    if en_cours:
        en_cours_tries = sorted(en_cours, key=lambda x: str(x.get("id", "")))
        for e in en_cours_tries:
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
            col_p.progress(pourcentage, text=f"Fin prévue: {e.get('fin_prevue')}")
            
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

    # ---------------------------------------------------------
    # 4. TABLEAU RÉCAPITULATIF (Trié chronologiquement par ID)
    # ---------------------------------------------------------
    st.subheader("Détail du Planning")
    
    equipements_actifs_tries = sorted(
        [e for e in st.session_state.data["equipements"] if e.get("statut") in ["Actif", "Bloqué"]],
        key=lambda x: str(x.get("id", ""))
    )
    
    data_to_display = []
    for e in equipements_actifs_tries:
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
        
        st.dataframe(
            df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Jours restants": st.column_config.NumberColumn(format="%d jours")
            }
        )
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger le planning (CSV)", csv, "planning.csv", "text/csv")
    else:
        st.write("Aucune machine en cours de production.")

# 1. HISTORIQUE
with tabs[1]:
    st.subheader("⚠️ Administration")
    
    with st.expander("Gestion de la base (Admin)"):
        mdp = st.text_input("Mot de passe administrateur", type="password", key="mdp_admin")
        
        if st.button("Remise à zéro avec sauvegarde"):
            if mdp == "TonMotDePasse":
                archive_dir = os.path.join(BASE_DIR, "Archives")
                if not os.path.exists(archive_dir):
                    os.makedirs(archive_dir)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(archive_dir, f"backup_{timestamp}.json")
                shutil.copy(DATA_FILE, backup_path)
                
                st.session_state.data = {
                    "techniciens": ["Thomas", "Lucas"], 
                    "equipements": [], 
                    "absences": []
                }
                save_data()
                st.success("Base archivée et réinitialisée avec succès !")
                st.rerun()
            elif mdp:
                st.error("Mot de passe incorrect")

    st.divider()

    st.subheader("Historique des interventions")
    terminees = sorted(
        [e for e in st.session_state.data["equipements"] if e.get("statut") == "Terminé"],
        key=lambda x: str(x.get("id", ""))
    )
    
    if not terminees:
        st.info("Aucune intervention terminée.")
    else:
        for e in terminees:
            date_fin_affiche = e.get("fin_reelle", e.get("fin_prevue", "N/A"))
            st.write(f"✅ **{e['id']}** | Fin réelle : {date_fin_affiche}")

# 2. PLANNING (Gestion & Modification)
with tabs[2]:
    st.subheader("Planification et Suivi")
    
    # Fonction utilitaire locale pour calculer une date en sautant weekends et congés
    def calculer_fin_avec_contraintes(date_debut_cal, duree_jours, tech_cible, equipements_actuels, absences_actuelles, ignore_eq_id=None):
        current_date = date_debut_cal
        
        def est_disponible(d_test):
            if d_test.weekday() >= 5: return False
            for abs_item in absences_actuelles:
                if abs_item["tech"] == tech_cible:
                    d_deb_abs = datetime.datetime.strptime(abs_item["debut"], '%Y-%m-%d').date()
                    d_fin_abs = datetime.datetime.strptime(abs_item["fin"], '%Y-%m-%d').date()
                    if d_deb_abs <= d_test <= d_fin_abs:
                        return False
            for e_item in equipements_actuels:
                if e_item.get("tech") == tech_cible and e_item.get("statut") in ["Actif", "Bloqué"]:
                    if ignore_eq_id and e_item.get("id") == ignore_eq_id:
                        continue
                    d_deb_eq = datetime.datetime.strptime(e_item["debut"], '%Y-%m-%d').date()
                    d_fin_eq = datetime.datetime.strptime(e_item["fin_prevue"], '%Y-%m-%d').date()
                    if d_deb_eq <= d_test <= d_fin_eq:
                        return False
            return True

        while not est_disponible(current_date):
            current_date += datetime.timedelta(days=1)
            
        date_reelle_debut = current_date
        jours_restants = int(duree_jours)
        date_actuelle = date_reelle_debut
        
        while jours_restants > 0:
            if est_disponible(date_actuelle):
                jours_restants -= 1
            if jours_restants > 0:
                date_actuelle += datetime.timedelta(days=1)
                
        return date_reelle_debut, date_actuelle

    with st.form("ajout_machine", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        nom = c1.text_input("Nom de la machine")
        tech = c2.selectbox("Technicien", st.session_state.data["techniciens"])
        date_debut = c3.date_input("Date de début")
        duree = c3.number_input("Durée prévue (jours)", min_value=1, value=14)
        
        if st.form_submit_button("Ajouter à la production"):
            absences = st.session_state.data.get("absences", [])
            equipements = st.session_state.data.get("equipements", [])
            
            d_reelle, d_fin = calculer_fin_avec_contraintes(date_debut, int(duree), tech, equipements, absences)
            
            st.session_state.data["equipements"].append({
                "id": nom, 
                "tech": tech, 
                "statut": "Actif",
                "debut": str(d_reelle),
                "fin_prevue": str(d_fin),
                "duree_jours": int(duree)
            })
            save_data()
            st.success(f"Planifié : {d_reelle} au {d_fin}")
            st.rerun()

    st.subheader("Modifier / Ajuster une machine")

    machines_actives_tries = sorted(
        [e for e in st.session_state.data["equipements"] if e.get("statut") in ["Actif", "Bloqué"]],
        key=lambda x: str(x.get("id", ""))
    )
    machine_id = st.selectbox("Choisir une machine", [e['id'] for e in machines_actives_tries])

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
            
            d_deb = datetime.datetime.strptime(machine_concernee["debut"], '%Y-%m-%d').date()
            d_fin = nouvelle_fin
            temp_d = d_deb
            nouvelle_duree = 0
            while temp_d <= d_fin:
                if temp_d.weekday() < 5:
                    nouvelle_duree += 1
                temp_d += datetime.timedelta(days=1)
            machine_concernee["duree_jours"] = max(1, nouvelle_duree)
            
            save_data()
            st.success(f"La machine {machine_id} a été mise à jour avec succès !")
            st.rerun()

    st.divider()

    # --- SECTION REPLANIFICATION EN CASCADE ---
    st.subheader("🔄 Replanification en cascade par Technicien")
    st.markdown("Si une machine a été prolongée, décalée ou que des congés ont été ajoutés, ce bouton permet de réajuster automatiquement toutes les machines suivantes de ce technicien.")
    
    col_tech_casc, col_btn_casc = st.columns([2, 1])
    tech_a_replanifier = col_tech_casc.selectbox("Technicien concerné", st.session_state.data["techniciens"], key="tech_cascade")
    
    if col_btn_casc.button("⚡ Lancer la cascade"):
        machines_tech = sorted(
            [e for e in st.session_state.data["equipements"] if e.get("tech") == tech_a_replanifier and e.get("statut") in ["Actif", "Bloqué"]],
            key=lambda x: x["debut"]
        )
        
        if len(machines_tech) > 0:
            absences = st.session_state.data.get("absences", [])
            equipements = st.session_state.data.get("equipements", [])
            modifications_faites = 0
            
            derniere_fin_connue = None
            for i, machine in enumerate(machines_tech):
                duree_ouvree = machine.get("duree_jours", 14)
                d_deb_orig = datetime.datetime.strptime(machine["debut"], '%Y-%m-%d').date()
                
                if i == 0:
                    nouveau_deb, nouvelle_fin = calculer_fin_avec_contraintes(d_deb_orig, duree_ouvree, tech_a_replanifier, equipements, absences, ignore_eq_id=machine["id"])
                else:
                    prochain_jour_possible = derniere_fin_connue + datetime.timedelta(days=1)
                    nouveau_deb, nouvelle_fin = calculer_fin_avec_contraintes(prochain_jour_possible, duree_ouvree, tech_a_replanifier, equipements, absences, ignore_eq_id=machine["id"])
                
                if machine["debut"] != str(nouveau_deb) or machine["fin_prevue"] != str(nouvelle_fin):
                    machine["debut"] = str(nouveau_deb)
                    machine["fin_prevue"] = str(nouvelle_fin)
                    modifications_faites += 1
                
                derniere_fin_connue = datetime.datetime.strptime(machine["fin_prevue"], '%Y-%m-%d').date()
            
            save_data()
            if modifications_faites > 0:
                st.success(f"Cascade exécutée ! {modifications_faites} machine(s) replanifiée(s) proprement.")
                st.rerun()
            else:
                st.info("Le planning est déjà parfaitement aligné.")
        else:
            st.info("Pas assez de machines en cours pour ce technicien pour faire une cascade.")
    st.divider()
    
    # Affichage des machines actives/bloquées triées chronologiquement par ID
    equipements_tries = sorted(
        enumerate(st.session_state.data["equipements"]), 
        key=lambda x: str(x[1].get("id", ""))
    )

    for i, e in equipements_tries:
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
                            e["statut"] = "Bloqué"
                            e["cause_arret"] = cause
                            save_data(); st.rerun()
                        else:
                            st.error("Veuillez saisir une raison.")
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
                e["statut"] = "Terminé"
                e["fin_reelle"] = str(datetime.date.today())
                save_data(); st.rerun()

            if cols[4].button("🗑️", key=f"del_{unique_key}", help="Supprimer cette machine"):
                del st.session_state.data["equipements"][i]
                save_data()
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
            if date_fin >= date_deb:
                st.session_state.data["absences"].append({
                    "tech": tech, 
                    "debut": str(date_deb),
                    "fin": str(date_fin)
                })
                save_data()
                st.success("Absence enregistrée !")
                st.rerun()
            else:
                st.error("La date de fin doit être après la date de début.")

    st.divider()
    for i, abs in enumerate(st.session_state.data["absences"]):
        col1, col2 = st.columns([3, 1])
        col1.write(f"📅 **{abs['tech']}** : du {abs['debut']} au {abs['fin']}")
        if col2.button("Suppr", key=f"del_abs_{i}"):
            st.session_state.data["absences"].pop(i)
            save_data()
            st.rerun()

# 4. ÉQUIPE
with tabs[4]:
    for i, t in enumerate(list(st.session_state.data["techniciens"])):
        col1, col2 = st.columns([3, 1])
        col1.write(t)
        if col2.button("Suppr", key=f"del_{i}"):
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
    from collections import Counter
    
    equipements = st.session_state.data.get("equipements", [])
    terminees = [e for e in equipements if e.get("statut") == "Terminé" and e.get("fin_reelle")]
    
    if not terminees:
        st.info("Terminez quelques interventions pour voir apparaître les indicateurs.")
    else:
        ecarts = []
        lead_times = []
        respectes = 0
        
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
        libelle_ecart = "Avance moy." if moyen_ecart >= 0 else "Retard moy."
        valeur_affichee = moyen_ecart if moyen_ecart >= 0 else -moyen_ecart
        col2.metric(libelle_ecart, f"{valeur_affichee:.1f} j")
        
        col3.metric("Lead Time moy.", f"{sum(lead_times)/len(lead_times):.1f} j")
        col4.metric("Interventions", len(terminees))
        
        st.divider()

        df = pd.DataFrame({
            "Machine": [e["id"] for e in terminees],
            "Écart (j) (+ avance / - retard)": ecarts,
            "Lead Time (j)": lead_times
        }).set_index("Machine")

        c1, c2 = st.columns(2)
        with c1:
            st.write("### Écarts (Avance vs Retard en jours)")
            couleur_ecart = "#00cc96" if moyen_ecart >= 0 else "#ff4b4b"
            st.bar_chart(df["Écart (j) (+ avance / - retard)"], color=couleur_ecart)
        with c2:
            st.write("### Lead Time par machine")
            st.bar_chart(df["Lead Time (j)"], color="#3385ff")

        st.divider()

        c_stop, c_retard = st.columns(2)
        
        with c_stop:
            st.write("### 🛑 Top 3 Blocages (Arrêts de production)")
            bloquees = [e for e in equipements if e.get("cause_arret")]
            if bloquees:
                causes = Counter([e["cause_arret"] for e in bloquees]).most_common(3)
                col_podium = st.columns(3)
                medailles = ["🥇", "🥈", "🥉"]
                for i, (cause, count) in enumerate(causes):
                    with col_podium[i]:
                        st.markdown(f"<div style='text-align: center; font-size: 20px;'>{medailles[i]}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align: center; font-size: 12px; font-weight: bold;'>{cause}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align: center; color: #ffa500;'>{count}x</div>", unsafe_allow_html=True)
            else:
                st.write("Aucun blocage enregistré.")

        with c_retard:
            st.write("### ⏱️ Top 3 Retards (Finitions)")
            retards = [e for e in terminees if e.get("commentaire_retard")]
            if retards:
                causes = Counter([e["commentaire_retard"] for e in retards]).most_common(3)
                col_podium = st.columns(3)
                medailles = ["🥇", "🥈", "🥉"]
                for i, (cause, count) in enumerate(causes):
                    with col_podium[i]:
                        st.markdown(f"<div style='text-align: center; font-size: 12px; font-weight: bold;'>{cause}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align: center; color: #ff4b4b;'>{count}x</div>", unsafe_allow_html=True)
            else:
                st.write("Aucun retard enregistré.")
