# apktools

Petit utilitaire avec interface graphique (CustomTkinter) pour envoyer un APK
compilé (dossier `build\app\outputs\flutter-apk`) directement vers le téléphone
via `adb push`, sans passer par l'explorateur Windows / MTP.

## Installation

Dépendance : `pip install customtkinter`

`projects.json` contient vos chemins locaux (spécifiques à votre machine) et
n'est donc **pas versionné** (voir `.gitignore`). Avant le premier lancement,
créez le vôtre à partir de l'exemple fourni :

```
copy projects.example.json projects.json
```

(ou laissez-le simplement absent : l'app en crée un vide automatiquement au
premier lancement, et vous pouvez ensuite ajouter des projets via le bouton
"+ Ajouter" dans l'interface.)

## Lancer l'app

```
python apktools.py
```

## Ajouter un projet

Bouton **"+ Ajouter"** en haut de la fenêtre : nom du projet, dossier de build
(bouton "Parcourir..." pour le sélectionner), et dossier de destination sur le
téléphone (pré-rempli automatiquement en `/sdcard/Download/<nom>`, modifiable).
Enregistré directement dans `projects.json`.

On peut aussi éditer `projects.json` à la main (voir `projects.example.json`
pour le format) :

```json
{
  "name": "mon_projet",
  "build_dir": "C:\\chemin\\vers\\build\\app\\outputs\\flutter-apk",
  "device_dest": "/sdcard/Download/mon_projet"
}
```

## Connexion au téléphone : USB vs Wi-Fi

Sur cette machine, le débogage **USB** ne fonctionne pas de façon fiable : Windows
reconnaît bien l'interface "ADB Interface" (pilote WinUsb correct, statut "OK"),
mais `adb devices -l` ne détecte jamais le téléphone, même en ligne de commande
sans passer par l'app. La cause exacte n'a pas été identifiée (possiblement un
antivirus/EDR qui bloque l'accès USB brut, ou une particularité ColorOS/Realme).

**Solution retenue : débogage sans fil (Wireless debugging)**, disponible nativement
sur Android 11+. Il contourne entièrement le problème puisqu'il ne dépend d'aucun
pilote USB Windows.

### Configuration initiale (à faire une fois, ou après reset des autorisations)

1. Téléphone et PC sur le **même réseau Wi-Fi**.
2. Sur le téléphone : Paramètres → Options pour développeurs → **Débogage sans
   fil** → activer.
3. Taper sur le texte "Débogage sans fil" (pas juste le toggle) → **Associer
   l'appareil avec un code d'appairage**. Une adresse `IP:port` et un code à 6
   chiffres s'affichent.
4. Sur le PC :
   ```
   adb pair <ip>:<port_appairage> <code>
   ```
5. Sur l'écran principal "Débogage sans fil", noter la **deuxième** adresse
   `IP:port` (différente du port d'appairage) puis :
   ```
   adb connect <ip>:<port_connexion>
   ```
6. Vérifier :
   ```
   adb devices -l
   ```
   Le téléphone doit apparaître avec l'état `device`.

L'appairage (étape 3-4) reste mémorisé par le téléphone tant que l'autorisation
n'est pas révoquée. Aucune modification du code de l'app n'est nécessaire : elle
liste les appareils via `adb devices -l` quel que soit le format du "serial" (USB
ou `IP:port`).

### À refaire à chaque fois

La connexion (`adb connect`, étape 5) **n'est pas permanente** : elle retombe après
un redémarrage du PC, du téléphone, ou un changement de réseau Wi-Fi. Dans ce cas,
pas besoin de refaire l'appairage complet — relancer simplement :

```
adb connect <ip>:<port_connexion>
```

Le port de connexion peut changer d'une session à l'autre (visible sur l'écran
"Débogage sans fil" du téléphone) ; l'IP reste généralement stable sauf changement
de réseau.

Si l'app n'affiche aucun appareil détecté, c'est généralement parce que cette
étape n'a pas été refaite depuis le dernier redémarrage.
