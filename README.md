# KMD CLIP — service d’import YouTube (prototype)

Ce service reçoit un lien YouTube public, télécharge une version MP4 (vidéo jusqu'à 480p avec audio), puis la transmet au navigateur pour le montage. Limite : 250 Mo par vidéo ; le téléchargement peut être refusé par YouTube ou par le fournisseur d'hébergement. L'utilisateur doit posséder les droits et respecter les conditions applicables.

## Installation locale

Python 3.10+ et Internet. Installer :

```
pip install -r requirements.txt
python server.py
```

L'interface compilée doit se trouver dans le dossier `site` à côté de `server.py`, ou être hébergée séparément. Par défaut le serveur écoute sur le port 8002 ; on peut changer cela avec la variable `PORT`. Les fichiers temporaires sont stockés dans le répertoire temporaire de la machine ; leur suppression est tentée après 15 minutes lors d'une nouvelle requête. Les vidéos transitent par le serveur d'import.

## Cloudflare

Cloudflare Pages/Workers statique ne peut pas exécuter ce serveur Flask/yt-dlp. Il faut un hébergement Python séparé, accessible en HTTPS. Dans la nouvelle interface, renseigner l'adresse HTTPS de ce service d'import. La variable d'environnement `ALLOWED_ORIGINS` définit les origines web autorisées, séparées par des virgules, par défaut l'adresse Cloudflare du site fournie dans cette conversation. Pour utiliser une autre origine, l'ajouter explicitement.

Le prototype ne doit pas être ouvert au public en l'état : il n'a pas d'authentification, de quotas par personne ni de protection anti-abus complète ; les vérifications d'origine ne sont pas une authentification. Installer un contrôle d'accès, une limitation de débit, des limites de ressources et un nettoyage planifié avant tout déploiement. Les copies temporaires peuvent persister en cas d'arrêt inopiné. Des hébergements gratuits peuvent dormir, bloquer YouTube ou imposer des limites et coûts selon l'usage.
