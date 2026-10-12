# Démarrage rapide — Virtual Lab Platform v3.8

## Lancer correctement l'application

1. Décompressez `virtual_lab_platform_v3_8.zip`.
2. Ouvrez un terminal dans le dossier `virtual_lab_platform_v3_8`.
3. Sous Windows, exécutez `python app.py`. Sous macOS/Linux, exécutez `python3 app.py`.
4. Ouvrez **http://127.0.0.1:8765** dans votre navigateur.
5. Vérifiez l'indicateur de connexion dans l'en-tête. S'il indique que l'API locale est indisponible, vérifiez que le terminal affiche que le serveur est démarré.

**Important :** ne double-cliquez pas sur `static/index.html`. La page doit être servie par `app.py` pour que les appels aux simulateurs et aux outils de recherche puissent fonctionner.

## Bibliothèque et paillasse

- Choisissez une catégorie, par exemple **Électricité & électronique**, puis cliquez sur **Ajouter** sur une fiche.
- Sélectionnez l'objet dans la paillasse pour modifier ses paramètres.
- Cliquez sur **Enregistrer la paillasse** pour conserver l'état dans le navigateur courant.
- Cliquez sur **Restaurer la sauvegarde** pour revenir explicitement à la dernière sauvegarde. La restauration peut remplacer le travail en cours après confirmation.
- Utilisez **Exporter en JSON** pour créer une copie portable.

## Instruments virtuels

Dans **Instruments virtuels et incertitudes**, choisissez un instrument, saisissez une valeur théorique et cliquez sur **Simuler une mesure**. Les résultats sont simulés, pas expérimentaux; les incertitudes du catalogue sont illustratives et non certifiées par des fabricants.
