# Virtual Lab Platform v3.5

## Démarrer
Sur macOS ou Linux :
```bash
python3 app.py
```
Sur Windows :
```powershell
python app.py
```
Puis ouvrir http://127.0.0.1:8765.

## Étape v3.5 — liaison paillasse → moteur cinétique
Le laboratoire permet désormais d’ajouter des espèces cinétiques **abstraites** A, B et C à la paillasse, de renseigner leurs concentrations dans le panneau Propriétés, puis de charger ces concentrations dans le moteur de cinétique chimique RK4. Les paramètres de réaction, la durée, le pas d’intégration et la température restent configurés dans le simulateur.

Le simulateur affiche les courbes et valeurs calculées et permet l’export JSON. Une commande d’annulation interrompt l’attente côté interface ; le serveur local ne garantit pas l’arrêt d’un calcul déjà lancé.

**Limite scientifique :** A, B et C sont des espèces mathématiques génériques, pas des molécules identifiées. La liaison n’infère ni mécanisme réactionnel ni constante cinétique réelle. Il faut des paramètres et un mécanisme documentés pour interpréter une réaction chimique spécifique.
