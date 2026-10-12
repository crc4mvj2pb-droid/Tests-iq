# Démarrage rapide — Virtual Lab Platform v2.8

## Lancer l'application sur Mac

1. Décompresse `virtual_lab_platform_v2_7.zip`.
2. Ouvre Terminal et place-toi dans le dossier décompressé (tu peux taper `cd `, glisser le dossier dans Terminal, puis appuyer sur Entrée).
3. Lance `sh launch_macos_linux.sh`.
4. Ouvre Safari et va sur `http://127.0.0.1:8765`.
5. Pour fermer le logiciel, retourne dans Terminal et fais `Ctrl+C`.

## Faire ton premier circuit calculé

1. Dans la bibliothèque, ouvre **Électricité & électronique**.
2. Ajoute **Source de tension CC**, **Résistance** et **Masse / nœud de référence**.
3. Sélectionne la source dans la paillasse et règle sa tension dans Propriétés, par exemple `9 V`.
4. Sélectionne la résistance et règle sa valeur, par exemple `1000 Ω`.
5. Clique sur la borne `+` de la source, puis sur la borne `A` de la résistance.
6. Clique sur la borne `B` de la résistance, puis sur la borne `GND` de la masse.
7. Clique sur la borne `−` de la source, puis sur la borne `GND` de la masse.
8. Clique sur **Résoudre le circuit CC câblé**.

Pour 9 V et 1000 Ω, le modèle idéal devrait donner environ 9 mA et 81 mW dissipés dans la résistance. Ce résultat est une vérification pédagogique du modèle, pas une mesure réelle.

Tu peux aussi créer chaque liaison via les sélecteurs du panneau Propriétés, utile si les bornes sont difficiles à toucher sur un écran tactile.

## Si le circuit ne se résout pas

- Vérifie que chaque borne requise est reliée.
- Relie le négatif de la source à la masse.
- Vérifie les valeurs de résistance en ohms et la tension en volts.
- Retire les composants non encore pris en charge par ce solveur (par exemple condensateur, bobine, diode ou transistor).

Les connexions sont enregistrées localement via **Enregistrer la paillasse** et incluses dans l'export JSON.
