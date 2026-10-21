
        
            
              

import sqlite3
import re
import uuid
import shutil
from pathlib import Path
from urllib.parse import quote

import streamlit as st

# ==========================================
# CONFIGURATION
# ==========================================

DOSSIER = Path(__file__).resolve().parent
DB = DOSSIER / "koro.db"
DOSSIER_PHOTOS = DOSSIER / "photos"
DOSSIER_PHOTOS.mkdir(exist_ok=True)

st.set_page_config(
    page_title="KORO | Marketplace Cameroun",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# DESIGN CSS
# ==========================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .stApp {
        background: #f6f8f7;
        font-family: 'Inter', sans-serif;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: #123c2c;
        font-family: 'Inter', sans-serif;
        letter-spacing: -0.5px;
    }

    .koro-header {
        background: linear-gradient(120deg, #103d2c, #16834f);
        color: white;
        padding: 30px;
        border-radius: 20px;
        margin-bottom: 24px;
    }

    .koro-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .koro-header p {
        color: #e1f5e9;
        font-size: 1rem;
        margin-bottom: 0;
    }

    .section-label {
        color: #16834f;
        font-weight: 700;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: white;
        border: 1px solid #e6ece8;
        border-radius: 16px;
        padding: 12px;
        transition: border-color 0.2s ease;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #16834f;
    }

    div[data-testid="stMetric"] {
        background: white;
        padding: 16px;
        border: 1px solid #e6ece8;
        border-radius: 14px;
    }

    div[data-testid="stMetricLabel"] {
        color: #66756d;
    }

    div[data-testid="stMetricValue"] {
        color: #123c2c;
        font-weight: 800;
    }

    .stButton > button,
    .stFormSubmitButton > button,
    .stLinkButton > a {
        background: #16834f;
        color: white !important;
        border: 0;
        border-radius: 10px;
        font-weight: 700;
        min-height: 42px;
    }

    .stButton > button:hover,
    .stFormSubmitButton > button:hover,
    .stLinkButton > a:hover {
        background: #10663d;
        border-color: #10663d;
        color: white !important;
    }

    div[data-baseweb="tab-list"] {
        gap: 8px;
        background: white;
        padding: 8px;
        border-radius: 12px;
    }

    button[data-baseweb="tab"] {
        border-radius: 9px;
    }

    div[data-baseweb="tab-highlight"] {
        background: #16834f;
    }

    input, textarea {
        border-radius: 10px !important;
    }

    .koro-footer {
        text-align: center;
        color: #738078;
        padding-top: 24px;
        font-size: 0.85rem;
    }

    @media (max-width: 640px) {
        .koro-header {
            padding: 22px 18px;
        }

        .koro-header h1 {
            font-size: 2rem;
        }

        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# BASE DE DONNEES
# ==========================================

def connecter():
    return sqlite3.connect(DB)


def initialiser():
    with connecter() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS annonces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                description TEXT NOT NULL,
                prix INTEGER NOT NULL,
                ville TEXT NOT NULL,
                categorie TEXT NOT NULL,
                contact TEXT DEFAULT ''
            )
        """)

        colonnes = {
            ligne[1]
            for ligne in conn.execute(
                "PRAGMA table_info(annonces)"
            ).fetchall()
        }

        if "photo_path" not in colonnes:
            conn.execute(
                "ALTER TABLE annonces ADD COLUMN photo_path TEXT"
            )

        # Tables ajoutees pour les commandes ; les annonces existantes restent intactes.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS commandes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_nom TEXT NOT NULL,
                client_telephone TEXT NOT NULL,
                client_ville TEXT NOT NULL,
                client_adresse TEXT NOT NULL,
                notes TEXT DEFAULT '',
                total INTEGER NOT NULL,
                statut TEXT NOT NULL DEFAULT 'Nouvelle',
                date_commande TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lignes_commande (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commande_id INTEGER NOT NULL,
                annonce_id INTEGER,
                produit_nom TEXT NOT NULL,
                prix_unitaire INTEGER NOT NULL,
                quantite INTEGER NOT NULL,
                sous_total INTEGER NOT NULL
            )
        """)


def obtenir_annonces():
    with connecter() as conn:
        return conn.execute("""
            SELECT id, nom, description, prix, ville,
                   categorie, contact, photo_path
            FROM annonces
            ORDER BY id DESC
        """).fetchall()


def ajouter_annonce(
    nom, description, prix, ville,
    categorie, contact, photo_path
):
    with connecter() as conn:
        conn.execute("""
            INSERT INTO annonces
            (nom, description, prix, ville,
             categorie, contact, photo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            nom, description, prix, ville,
            categorie, contact, photo_path
        ))


def obtenir_annonce_par_id(identifiant):
    with connecter() as conn:
        return conn.execute("""
            SELECT id, nom, description, prix, ville,
                   categorie, contact, photo_path
            FROM annonces
            WHERE id = ?
        """, (identifiant,)).fetchone()


def enregistrer_commande(client_nom, telephone, ville, adresse, notes, articles, total):
    with connecter() as conn:
        curseur = conn.execute("""
            INSERT INTO commandes
            (client_nom, client_telephone, client_ville,
             client_adresse, notes, total)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (client_nom, telephone, ville, adresse, notes, total))
        commande_id = curseur.lastrowid

        for article, quantite in articles:
            conn.execute("""
                INSERT INTO lignes_commande
                (commande_id, annonce_id, produit_nom,
                 prix_unitaire, quantite, sous_total)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                commande_id, article[0], article[1],
                int(article[3]), quantite, int(article[3]) * quantite
            ))
    return commande_id


initialiser()

if "panier" not in st.session_state:
    st.session_state["panier"] = {}
if "commande_confirmee" not in st.session_state:
    st.session_state["commande_confirmee"] = None


# ==========================================
# COMPOSANTS D'INTERFACE
# ==========================================

def afficher_annonce(a, contexte):
    identifiant, nom, description, prix, ville, categorie, contact, photo = a

    with st.container(border=True):
        if photo:
            chemin = DOSSIER / photo
        else:
            chemin = None

        if chemin and chemin.is_file():
            st.image(str(chemin), use_container_width=True)
        else:
            st.markdown("### 🛍️")

        st.caption(f"{categorie} · {ville}")
        st.subheader(nom)
        st.markdown(
            f"<h3 style='color:#16834f'>{prix:,.0f} FCFA</h3>",
            unsafe_allow_html=True
        )

        st.write(description)

        numero = re.sub(r"\D", "", contact or "")

        if numero.startswith("00"):
            numero = numero[2:]

        if numero and len(numero) >= 9:
            message = quote(
                f"Bonjour ! Je suis intéressé(e) par "
                f"votre annonce « {nom} » sur KORO."
            )

            lien = f"https://wa.me/{numero}?text={message}"

            st.link_button(
                "💬 Contacter sur WhatsApp",
                lien,
                use_container_width=True
            )
        else:
            st.caption("Contact vendeur non disponible.")

        if st.button(
            "🛒 Ajouter au panier",
            key=f"ajouter_panier_{contexte}_{identifiant}",
            use_container_width=True
        ):
            panier = st.session_state["panier"]
            cle = str(identifiant)
            panier[cle] = panier.get(cle, 0) + 1
            st.session_state["panier"] = panier
            st.toast(f"{nom} ajouté au panier !")
            st.rerun()


# ==========================================
# EN-TETE
# ==========================================

st.markdown("""
<div class="koro-header">
    <h1>🟢 KORO</h1>
    <p>Les opportunités à portée de main.</p>
    <p>Découvre, achète et vends au Cameroun 🇨🇲</p>
</div>
""", unsafe_allow_html=True)

annonces = obtenir_annonces()

# Navigation par onglets
accueil, explorer, publier, panier_tab = st.tabs([
    "🏠 Accueil",
    "🔎 Explorer",
    "➕ Publier une annonce",
    "🛒 Panier"
])


# ==========================================
# ACCUEIL
# ==========================================

with accueil:
    st.markdown(
        '<p class="section-label">TON ESPACE KORO</p>',
        unsafe_allow_html=True
    )
    st.header("Bienvenue sur KORO 👋")
    st.write(
        "Trouve des produits et des services, "
        "ou partage tes propres annonces."
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Annonces", len(annonces))
    col2.metric(
        "Villes",
        len(set(a[4] for a in annonces))
    )
    col3.metric(
        "Catégories",
        len(set(a[5] for a in annonces))
    )

    st.divider()
    st.subheader("✨ Les dernières annonces")

    if not annonces:
        st.info(
            "La marketplace est prête ! "
            "Publie la première annonce pour commencer."
        )
    else:
        colonnes = st.columns(3)

        for i, annonce in enumerate(annonces[:6]):
            with colonnes[i % 3]:
                afficher_annonce(annonce, "accueil")


# ==========================================
# EXPLORER
# ==========================================

with explorer:
    st.markdown(
        '<p class="section-label">MARKETPLACE</p>',
        unsafe_allow_html=True
    )
    st.header("Trouve ce qu'il te faut")

    recherche = st.text_input(
        "🔍 Recherche",
        placeholder="Ex. téléphone, chaussures, graphiste..."
    )

    villes = ["Toutes"] + sorted(set(a[4] for a in annonces))
    categories = ["Toutes"] + sorted(set(a[5] for a in annonces))

    col1, col2 = st.columns(2)

    with col1:
        ville = st.selectbox("📍 Ville", villes)

    with col2:
        categorie = st.selectbox("🏷️ Catégorie", categories)

    resultats = [
        a for a in annonces
        if recherche.lower() in (
            a[1] + " " + a[2] + " " + a[5]
        ).lower()
        and (ville == "Toutes" or a[4] == ville)
        and (categorie == "Toutes" or a[5] == categorie)
    ]

    st.write(f"**{len(resultats)} résultat(s)**")

    if not resultats:
        st.info("Aucune annonce correspondante.")
    else:
        colonnes = st.columns(3)

        for i, annonce in enumerate(resultats):
            with colonnes[i % 3]:
                afficher_annonce(annonce, "explorer")


# ==========================================
# PUBLIER
# ==========================================

with publier:
    st.markdown(
        '<p class="section-label">ESPACE VENDEUR</p>',
        unsafe_allow_html=True
    )
    st.header("Publie ton annonce")
    st.write(
        "Présente ton produit clairement pour aider "
        "les acheteurs à le découvrir."
    )

    with st.form("formulaire_annonce", clear_on_submit=True):
        nom = st.text_input(
            "Nom du produit ou service",
            placeholder="Ex. Téléphone Samsung"
        )

        description = st.text_area(
            "Description",
            placeholder="Décris ton produit, son état et ses caractéristiques..."
        )

        col1, col2 = st.columns(2)

        with col1:
            prix = st.number_input(
                "Prix en FCFA",
                min_value=0,
                step=500
            )

            ville = st.selectbox(
                "Ville",
                [
                    "Yaoundé", "Douala", "Bafoussam",
                    "Garoua", "Bamenda", "Autre"
                ]
            )

        with col2:
            categorie = st.selectbox(
                "Catégorie",
                [
                    "Électronique", "Vêtements",
                    "Alimentation", "Services",
                    "Informatique", "Maison", "Autre"
                ]
            )

            contact = st.text_input(
                "WhatsApp avec indicatif pays",
                placeholder="2376XXXXXXXX"
            )

        fichier = st.file_uploader(
            "📷 Photo du produit",
            type=["jpg", "jpeg", "png", "webp"]
        )

        if fichier:
            st.image(
                fichier,
                caption="Aperçu de ta photo",
                use_container_width=True
            )

        envoyer = st.form_submit_button(
            "Publier mon annonce",
            use_container_width=True
        )

    if envoyer:
        if not nom.strip() or not description.strip():
            st.error("Le nom et la description sont obligatoires.")

        elif contact.strip() and len(
            re.sub(r"\D", "", contact)
        ) < 9:
            st.error("Vérifie le numéro WhatsApp.")

        else:
            chemin_photo = None

            if fichier:
                extension = Path(fichier.name).suffix.lower()
                nom_photo = f"{uuid.uuid4().hex}{extension}"
                destination = DOSSIER_PHOTOS / nom_photo

                with open(destination, "wb") as sortie:
                    shutil.copyfileobj(fichier, sortie)

                chemin_photo = str(
                    Path("photos") / nom_photo
                )

            ajouter_annonce(
                nom.strip(),
                description.strip(),
                int(prix),
                ville,
                categorie,
                contact.strip(),
                chemin_photo
            )

            st.success("Ton annonce a été publiée !")
            st.rerun()


# ==========================================
# PANIER ET COMMANDES
# ==========================================

with panier_tab:
    st.markdown(
        '<p class="section-label">FINALISER UN ACHAT</p>',
        unsafe_allow_html=True
    )
    st.header("🛒 Ton panier")

    if st.session_state["commande_confirmee"]:
        st.success(
            f"Commande n° {st.session_state['commande_confirmee']} enregistrée "
            "sur cet ordinateur. Le vendeur doit encore confirmer la disponibilité."
        )
        if st.button("Masquer ce message", key="masquer_confirmation"):
            st.session_state["commande_confirmee"] = None
            st.rerun()

    panier = st.session_state["panier"]
    panier_valide = {}
    for cle, quantite in panier.items():
        article = obtenir_annonce_par_id(int(cle))
        if article:
            panier_valide[cle] = quantite
    st.session_state["panier"] = panier_valide
    panier = st.session_state["panier"]

    if not panier:
        st.info("Ton panier est vide. Va dans Explorer et clique sur « Ajouter au panier ».")
    else:
        articles = []
        total = 0

        for cle, quantite_actuelle in list(panier.items()):
            article = obtenir_annonce_par_id(int(cle))
            if not article:
                continue

            identifiant, nom, description, prix, ville_article, categorie, contact, photo = article
            col_produit, col_quantite, col_retirer = st.columns([5, 2, 1])

            with col_produit:
                st.markdown(f"**{nom}**")
                st.caption(f"{ville_article} · {categorie}")
                st.write(f"{int(prix):,.0f} FCFA l'unité".replace(",", " "))
                if photo:
                    chemin = DOSSIER / photo
                    if chemin.is_file():
                        st.image(str(chemin), width=110)

            with col_quantite:
                quantite = st.number_input(
                    "Quantité",
                    min_value=1,
                    max_value=99,
                    value=int(quantite_actuelle),
                    step=1,
                    key=f"quantite_panier_{identifiant}"
                )
                st.session_state["panier"][cle] = int(quantite)

            with col_retirer:
                st.write("")
                if st.button("🗑️", key=f"retirer_panier_{identifiant}", help="Retirer ce produit"):
                    st.session_state["panier"].pop(cle, None)
                    st.rerun()

            quantite_finale = int(st.session_state["panier"].get(cle, 1))
            articles.append((article, quantite_finale))
            total += int(prix) * quantite_finale
            st.divider()

        st.markdown(
            f"<h3 style='color:#16834f'>Total : {total:,.0f} FCFA</h3>",
            unsafe_allow_html=True
        )
        st.caption("Le total est indicatif : confirme le prix et la disponibilité avec le vendeur.")

        st.subheader("📦 Informations pour la commande")
        with st.form("formulaire_commande", clear_on_submit=False):
            client_nom = st.text_input("Ton nom complet")
            telephone = st.text_input(
                "Ton numéro de téléphone / WhatsApp",
                placeholder="Ex. 2376XXXXXXXX"
            )
            villes_livraison = [
                "Yaoundé", "Douala", "Bafoussam", "Garoua",
                "Bamenda", "Maroua", "Autre"
            ]
            ville_client = st.selectbox("Ville de livraison ou de retrait", villes_livraison)
            adresse = st.text_input(
                "Quartier ou point de rencontre",
                placeholder="Ex. Ngoa-Ekellé, près de..."
            )
            notes = st.text_area("Précisions (facultatif)", placeholder="Couleur, taille, moment souhaité...")
            valider_commande = st.form_submit_button(
                "✅ Envoyer ma commande",
                use_container_width=True
            )

        if valider_commande:
            chiffres = re.sub(r"\D", "", telephone)
            if not client_nom.strip() or not chiffres or not ville_client or not adresse.strip():
                st.error("Remplis ton nom, ton téléphone, ta ville et le quartier ou point de rencontre.")
            elif len(chiffres) < 9:
                st.error("Vérifie ton numéro de téléphone.")
            elif not articles:
                st.error("Ton panier est vide.")
            else:
                numero_commande = enregistrer_commande(
                    client_nom.strip(), telephone.strip(), ville_client,
                    adresse.strip(), notes.strip(), articles, total
                )
                st.session_state["panier"] = {}
                st.session_state["commande_confirmee"] = numero_commande
                st.rerun()

    st.divider()
    st.subheader("ℹ️ Comment les commandes fonctionnent")
    st.write(
        "Cette version enregistre les commandes dans la base de données locale de KORO. "
        "Elle ne déclenche pas encore de paiement en ligne et n'envoie pas automatiquement "
        "la commande au vendeur. Tant que KORO n'est pas hébergé avec une base de données "
        "partagée, les commandes restent sur cet ordinateur."
    )


# ==========================================
# PIED DE PAGE
# ==========================================

st.markdown("""
<div class="koro-footer">
    <strong>KORO 🇨🇲</strong><br>
    Les opportunités à portée de main.<br>
    Prototype en développement.
</div>
""", unsafe_allow_html=True)
