# ECG Explorer et chaîne ECG

Cette réalisation complémentaire est indépendante de JumpLab Pi. Les deux activités illustrent des chaînes de mesure différentes dans le même cours : signal électrique acquis par un ADC pour l'ECG, images horodatées pour le saut.

Tableau de bord : https://victor-ecg-explorer.hoi987.chatgpt.site/

Le code fourni ici est **ecg_lab_v2.py, version interne 1.2.0**, issu du fichier transmis par le binôme. Les instructions d'utilisation sont dans son en-tête. Il acquiert ou relit un signal horodaté, le filtre, propose des pics R et des candidats P/Q/S/T, puis exporte les données et les figures. Les candidats ne constituent pas des annotations médicalement validées. Une absence de marqueur n'indique pas une absence physiologique.

Le mode `mcp3008` nécessite le matériel et `spidev`. Les modes `demo` et `file` peuvent être utilisés hors Pi avec NumPy, SciPy et Matplotlib. Exemple sans matériel :

```bash
python -m pip install numpy scipy matplotlib
python ecg_lab_v2.py --mode demo --show
```

Ce script est une version historique distincte du code de JumpLab Pi. Il n'a pas fait l'objet d'un nouveau test matériel lors de la préparation du rendu. Les 17 tests JumpLab Pi ne testent pas ce script ECG.

## Provenance et statut

L'archive d'acquisition fournie contient des données en mode MCP3008, 7 997 échantillons sur 9,99853 s, avec 800 Hz demandés et environ 799,718 Hz mesurés. Les métadonnées signalent trois créneaux d'acquisition manqués. Cela documente une acquisition réelle fournie par le binôme ; la date de l'horloge du Pi n'a pas été vérifiée indépendamment. Aucun fichier ECG individuel n'est inclus ici.

Seul le commentaire initial de cette copie publique a été adapté pour retirer une référence nominative à un résultat physiologique individuel. Le code exécutable est inchangé. Le code source du tableau de bord hébergé n'est pas inclus ; son lien et sa fonction sont documentés, sans prétendre fournir un export de cette autre application.

## Photo à ajouter

Ajouter dans `report/figures` une photographie de votre montage ECG prise en séance, légendée avec les éléments réellement visibles. Une capture du tableau de bord peut être ajoutée si les données affichées peuvent être partagées. La photo du montage doit rester présentée comme une illustration de l'activité ECG, et non comme une acquisition de saut.
