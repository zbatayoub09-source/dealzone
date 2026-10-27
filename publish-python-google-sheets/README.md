# Publish Python + Google Sheets

Programme local pour lire les nouvelles depuis Google Sheets, choisir une page Facebook dans une liste, puis publier le titre, le texte et l'image. Prévu pour être étendu à Blogger dans la même interface.

## Installation (Windows)
1. Installer Python 3.11 ou 3.12 si possible.
2. Copier `.env.example` vers `.env` et remplir les paramètres. Ne jamais publier `.env`, `credentials.json` ou des tokens sur GitHub.
3. Créer un compte de service Google Cloud, activer Google Sheets API, télécharger le JSON et le placer ici sous le nom `credentials.json`.
4. Partager la feuille Google avec l'adresse e-mail du compte de service.
5. Modifier `SPREADSHEET_ID` et `SHEET_NAME` dans `.env`.
6. Double-cliquer sur `RUN.bat`.

La feuille attend les colonnes A:D : Date, Image URL, Title, Full Article. Le programme ne publie pas automatiquement au démarrage : il faut choisir une page et cliquer sur Publier.

## Facebook
Le token doit être un **Page Access Token** avec les autorisations nécessaires, notamment `pages_show_list`, `pages_read_engagement` et `pages_manage_posts`, selon la configuration Meta et les rôles de la page. La liste affiche uniquement les pages accessibles au token. Le programme vérifie la réponse de l'API et n'indique pas une publication réussie si l'API renvoie une erreur.

## État de publication
Les publications réussies sont enregistrées dans `published_state.json` localement, séparément par page. Ce fichier ne doit pas être envoyé sur GitHub.

## Blogger
Le module Blogger sera ajouté après avoir vérifié le fonctionnement de la lecture Sheets et de la publication Facebook. Ne placez aucun secret ou token dans le dépôt.
