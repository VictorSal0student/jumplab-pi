# Utiliser JumpLab Pi sans Raspberry Pi

Le Raspberry Pi est nécessaire pour tester l'adaptateur de caméra prévu, mais pas pour importer une vidéo et utiliser l'annotation manuelle. Aucun compte ou service distant n'est nécessaire au fonctionnement de l'application installée.

## Pourquoi le lien ne répondait pas

`127.0.0.1` est l'adresse de votre propre ordinateur. Elle ne désigne ni le serveur de ChatGPT, ni GitHub, ni un Raspberry Pi distant. Le message « connexion refusée » signifie généralement qu'aucun serveur n'écoute à cet endroit. Télécharger le ZIP puis ouvrir l'adresse ne démarre pas le programme.

## Windows

1. Extraire entièrement le ZIP. Ne pas lancer le programme depuis l'archive compressée.
2. Installer Python depuis https://www.python.org/downloads/windows/ si nécessaire. Ouvrir un nouveau terminal et vérifier `py -3 --version` ou `python --version`.
3. Installer une distribution Windows de FFmpeg proposée par https://ffmpeg.org/download.html. Le dossier `bin` contenant **ffmpeg.exe et ffprobe.exe** doit se trouver dans le PATH Windows. Fermer puis rouvrir le terminal après modification du PATH.
4. Vérifier dans le terminal :

   ```powershell
   ffmpeg -version
   ffprobe -version
   ```

5. Double-cliquer sur `START_WINDOWS.bat`. Si une dépendance manque, la fenêtre explique laquelle. Sinon le navigateur s'ouvre et la fenêtre du serveur doit rester ouverte.
6. Choisir **Open synthetic demo**. Aucun branchement caméra n'est requis. Le bouton Record reste indisponible en mode import.

Lancement manuel équivalent, depuis le dossier contenant le README technique de l'application :

```powershell
cd jumplab-pi
py -3 -m jumplab.server
```

Attendre l'affichage de `http://127.0.0.1:8765`, puis ouvrir cette adresse dans le navigateur. Si `py` est introuvable mais `python --version` fonctionne, remplacer `py -3` par `python`. Arrêter le serveur avec Ctrl+C.

## Linux ou macOS

Installer Python 3.9 ou plus récent et FFmpeg avec FFprobe. Depuis `jumplab-pi`, lancer `python3 -m jumplab.server`, puis ouvrir l'adresse locale. Les tests disponibles ont été exécutés sous Linux ; aucun test sur votre Windows/macOS n'est revendiqué.

## Sans installation

Le rapport PDF et les captures du dossier `jumplab-pi/docs/screenshots` permettent de consulter le travail. Ils ne remplacent pas l'application interactive. GitHub Pages ne lance pas ce backend Python : publier le dépôt ne rend donc pas l'adresse locale accessible aux autres.

Les vidéos de téléphone peuvent être importées, mais les ralentis et exports vidéo peuvent avoir une base de temps différente du temps réel. Ne pas calculer une hauteur exploitable sans vérifier ce point et la visibilité des contacts.
