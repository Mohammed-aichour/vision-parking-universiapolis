# Démonstration privée sur Vercel

Ce dossier contient la version web pré-calculée du parking IP7 : page de connexion, tableau de bord, vidéo annotée et résultats. YOLO et OpenCV ont servi à préparer la vidéo ; ils ne tournent pas sur Vercel.

## Accès publié

- Adresse active : `https://universiapolis-parking-ai.vercel.app/`
- Identifiant : configurable dans les variables d'environnement
- Mot de passe : défini via le hachage PARKING_PASSWORD_HASH (voir ci-dessous)
- Projet Vercel : `universiapolis-parking-ai`

## Protection des données

`private_assets/` contient la vidéo, le plan, les images et le JSON. Il ne porte pas le nom `public`, car Vercel publierait ce dossier sans passer par la connexion. `app.py` exige une session valide pour chaque fichier. La vidéo est livrée par morceaux de 2 Mio afin de respecter la limite de réponse des fonctions Vercel.

Le mot de passe en clair reste dans `_ACCES_PRIVE`, hors de ce dossier déployable. Son empreinte `PARKING_PASSWORD_HASH` et la clé de session `SECRET_KEY` doivent être définies comme variables d'environnement **Production** dans le projet Vercel. Ne jamais écrire ces valeurs dans `vercel.json` ou dans le code.

## Publier sans dépôt Git

1. Se connecter à un compte Vercel et installer le CLI officiel : `npm install -g vercel`.
2. Depuis ce dossier, créer/lier le projet avec le nom **`universiapolis-parking-ai`** : `vercel link --yes --project universiapolis-parking-ai`.
3. Définir les variables d'environnement `SECRET_KEY` et `PARKING_PASSWORD_HASH` pour **Production**. La valeur de `PARKING_PASSWORD_HASH` figure dans le fichier privé. Générer une clé de session longue et aléatoire.
4. Déployer : `vercel --prod`.
5. Tester en fenêtre privée que `/video_annotee.mp4` et `/resultats.json` sont refusés avant connexion ; puis tester connexion, lecture vidéo, recherche dans la vidéo, plan et déconnexion.

Un compte Vercel est indispensable. Selon les conditions Vercel actuelles, l'offre gratuite Hobby est réservée à un usage personnel non commercial ; si le projet est exploité dans un cadre commercial, il faut choisir une offre admissible.

## Actualiser après une nouvelle analyse

Depuis ce dossier :

```powershell
python prepare_assets.py "..\05_RESULTATS_DEMO"
```

Relancer ensuite `vercel --prod`. Le script remplace les cinq résultats protégés et retire le lien de téléchargement direct de la vidéo ; la lecture reste disponible dans le tableau de bord.

## Vérification locale

Depuis le dossier principal du projet, double-cliquer `OUVRIR_DEMO_PROTEGEE.cmd`. La page sera accessible sur ce PC à `http://127.0.0.1:8010/`. Cette adresse locale n'est pas le lien Vercel.
