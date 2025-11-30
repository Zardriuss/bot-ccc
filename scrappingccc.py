import requests
import json
import os
import sys
from datetime import datetime

# --- CONFIGURATION ---
# Récupère le secret depuis GitHub
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

FICHIER_SAUVEGARDE = "suivi_pop_data.json"

# Ta liste de cartes
MA_LISTE = [
    {"nom": "Nidoking",  "numero": "233", "extension": None}, 
    {"nom": "Kyurem",    "numero": "96",  "extension": "Destinees"},
    {"nom": "Kyogre",    "numero": "104", "extension": None},
    {"nom": "Zekrom",    "numero": "114", "extension": "Noir"},
    {"nom": "Dracaufeu", "numero": "199", "extension": "151"},
]

# --- FONCTIONS ---

def envoyer_notif_discord(titre, message, couleur):
    """
    Couleurs Discord :
    - Rouge (Alerte) : 15548997
    - Vert (RAS)     : 5763719
    """
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ ERREUR : Pas de Webhook Discord configuré dans les Secrets.")
        return

    data = {
        "username": "Professeur Chen",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/5/53/Pok%C3%A9_Ball_icon.svg",
        "embeds": [{
            "title": titre,
            "description": message,
            "color": couleur,
            "footer": {"text": f"Scan Cloud effectué à {datetime.now().strftime('%H:%M')}"}
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"Erreur d'envoi Discord : {e}")

def charger_memoire():
    if os.path.exists(FICHIER_SAUVEGARDE):
        with open(FICHIER_SAUVEGARDE, 'r') as f:
            return json.load(f)
    return {}

def sauvegarder_memoire(data):
    with open(FICHIER_SAUVEGARDE, 'w') as f:
        json.dump(data, f, indent=4)

def get_carte_data(nom_pokemon, numero_cible, extension_filtre):
    base_url = "https://cccgrading.com/api/v2/cards/report"
    # Headers classiques
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/ld+json',
        'Referer': 'https://cccgrading.com/'
    }
    
    # On scanne quelques pages
    for page in range(1, 6):
        try:
            params = {'name': nom_pokemon, 'page': page}
            response = requests.get(base_url, params=params, headers=headers)
            if response.status_code != 200: return None
            
            data = response.json()
            cartes = data.get('hydra:member', [])
            if not cartes: break

            for carte in cartes:
                # Vérif numéro
                num_api = str(carte.get('customExtensionNumber', ''))
                match_numero = (numero_cible == num_api or f"{numero_cible}/" in num_api or num_api.startswith(f"{numero_cible}/"))
                
                if match_numero:
                    # Vérif extension
                    ext_data = carte.get('extension')
                    nom_serie_api = ext_data.get('name', '') if isinstance(ext_data, dict) else str(ext_data)
                    
                    if extension_filtre and extension_filtre.lower() not in nom_serie_api.lower():
                        continue
                    
                    return carte
        except:
            pass
    return None

# --- EXÉCUTION PRINCIPALE ---
if __name__ == "__main__":
    print("--- Démarrage du Scan ---")
    memoire = charger_memoire()
    
    cartes_modifiees = []
    resume_etat = [] # Pour stocker l'état actuel de toutes les cartes
    faut_sauvegarder = False

    for item in MA_LISTE:
        carte_id = f"{item['nom']}_{item['numero']}"
        nouvelle_data = get_carte_data(item['nom'], item['numero'], item['extension'])

        if nouvelle_data:
            total_actuel = nouvelle_data.get('notesTotal', 0)
            
            # 1. Gestion de la mémoire (Première fois ou Mise à jour)
            if carte_id not in memoire:
                memoire[carte_id] = nouvelle_data
                faut_sauvegarder = True
                updates_msg = "Initialisation (1ère fois)"
            else:
                ancienne = memoire[carte_id]
                updates_msg = ""
                
                # Vérif des grades importants
                diffs = []
                cles = ['note10g', 'note10b', 'note10', 'note95', 'note9', 'note8']
                for cle in cles:
                    v_new = nouvelle_data.get(cle, 0) or 0
                    v_old = ancienne.get(cle, 0) or 0
                    if v_new > v_old:
                        diffs.append(f"+{v_new - v_old} ({cle.replace('note', 'Gr')})")
                
                if diffs:
                    updates_msg = ", ".join(diffs)
                    memoire[carte_id] = nouvelle_data
                    faut_sauvegarder = True
                    cartes_modifiees.append(f"**{item['nom']}** : {updates_msg}")

            # 2. On ajoute la carte au résumé global (pour la notif de routine)
            resume_etat.append(f"{item['nom']} : {total_actuel} total")
        
        else:
            resume_etat.append(f"{item['nom']} : ⚠️ Erreur scan")

    # --- ENVOI DES NOTIFICATIONS ---
    
    if cartes_modifiees:
        # CAS 1 : IL Y A DU NOUVEAU !
        titre = "🚨 NOUVELLES POPS DÉTECTÉES !"
        msg = "\n".join(cartes_modifiees)
        couleur = 15548997 # ROUGE
        
        envoyer_notif_discord(titre, msg, couleur)
        print("Notification de changement envoyée.")

    else:
        # CAS 2 : RIEN A SIGNALER (Mais on prévient quand même)
        titre = "✅ Scan terminé : R.A.S"
        # On affiche un joli résumé
        msg = "Aucun changement détecté.\n\n📊 **État actuel :**\n" + "\n".join(resume_etat)
        couleur = 5763719 # VERT
        
        envoyer_notif_discord(titre, msg, couleur)
        print("Notification de routine envoyée.")

    # Sauvegarde finale
    if faut_sauvegarder:
        sauvegarder_memoire(memoire)
        # Hack pour GitHub : on force le fichier à être considéré comme modifié pour le commit
        os.system(f"touch {FICHIER_SAUVEGARDE}")