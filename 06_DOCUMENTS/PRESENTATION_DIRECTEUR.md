# Vision Parking — démonstration Universiapolis

## Objectif

Montrer comment une caméra IP déjà installée peut alimenter un tableau de bord des places de stationnement. OpenCV lit la vidéo ; YOLO repère les véhicules ; des polygones virtuels suivent les places délimitées par les marquages jaunes. Aucun nouveau marquage physique n'est nécessaire.

## Ce qui est présenté

- Dix minutes continues enregistrées par la caméra IP7, environ de **09:44:46 à 09:54:46**, le 28 septembre 2026.
- **18 places** : A01–A06 à gauche, B01–B05 au milieu, C01–C07 à droite. La numérotation va du premier plan vers le fond dans chaque rangée.
- Vert = libre ; rouge = occupée ; jaune = inconnue ; bleu = véhicule détecté dans l'allée suivie.
- A01 est partiellement hors cadre mais suivie avec prudence ; C07 reste « Inconnue » près des bennes. A06 correspond à la voiture bleue, sixième voiture de la rangée gauche, et est suivie. C01 est suivie.
- Les véhicules du fond et ceux sous la caméra ne participent pas à l'état des 18 places et ne reçoivent pas de cadre bleu dans la démo. Un véhicule garé ne conserve pas de cadre bleu.

## Déroulé devant le directeur

1. Dans le dossier `PROJET_PARKING_IP7` sur le Bureau, double-cliquer `OUVRIR_TABLEAU_DE_BORD.cmd`.
2. Ouvrir `http://127.0.0.1:8001` dans le navigateur.
3. Montrer le lien « Plan des zones visibles » et les trois rangées A, B et C du tableau de bord.
4. Lancer la vidéo. La voiture manœuvre en B02 dès environ **03:17** ; la place reste verte pendant le déplacement, puis passe en rouge vers **03:49,5**, huit secondes après sa stabilisation estimée.
5. Montrer A04 verte au départ puis rouge vers **01:48**, après confirmation. Le total reste 18 : libres + occupées + inconnues = 18 à chaque instant.
6. Regarder le plan en haut à droite : c'est un schéma vu de haut sans voitures. Les 18 polygones prennent exactement les états confirmés de la vidéo : vert libre, rouge occupé, jaune inconnu.
7. Lire « Heures de stationnement » : A04 est estimée garée vers **09:46:26** (validée 09:46:34) et B02 vers **09:48:28** (validée 09:48:36). Ces heures proviennent de l'horloge affichée dans la vidéo. A01, A02, A03, A05 et A06 sont déjà occupées à 09:44:46 ; leur arrivée n'est pas filmée.

## Interprétation et limites

La vidéo est enregistrée : le tableau de bord rejoue des résultats calculés, ce n'est pas encore un flux en direct. Pour une nouvelle arrivée, la position de la voiture doit d'abord rester stable environ deux secondes ; le délai de huit secondes commence au début de cette stabilité. Une libération demande huit secondes d'absence de détection. Un délai de libération plus court créait une fausse place libre sur B02 pendant une perte de détection.

Les contours suivent les marquages visibles sur une vue de la caméra. Leurs limites cachées sous les voitures ou les arbres restent à confirmer sur site, notamment à droite. Les résultats sont des estimations à valider avec davantage d'heures, de lumière et de météo. Une caméra déplacée ou remplacée exigera de nouveaux polygones.

La caméra IP7 ne permet pas un comptage fiable des entrées et sorties ; ce comptage demande une analyse séparée de la caméra d'accès. Le passage au direct demandera ensuite l'URL RTSP ou un accès en lecture au NVR.

## Fichiers principaux

| Fichier | Rôle |
|---|---|
| `01_VIDEO_SOURCE/video_ip7_10_minutes.mp4` | Copie de travail H.264 ; original sur `D:` intact |
| `02_POLYGONES/places_18.json` | 18 identifiants, dont A06 sur la sixième voiture à gauche |
| `05_RESULTATS_DEMO/plan_18_places.jpg` | Plan statique des polygones |
| `05_RESULTATS_DEMO/video_annotee.mp4` | Vidéo annotée de dix minutes |
| `05_RESULTATS_DEMO/resultats.json` | États et changements calculés |
| `05_RESULTATS_DEMO/index.html` | Tableau de bord web |

Les enregistrements et résultats restent locaux. Leur diffusion doit être décidée avec le responsable du site.
