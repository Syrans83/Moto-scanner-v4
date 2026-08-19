# Moto Scanner France — V3 Live

## Installation Windows

Décompresse le dossier puis ouvre PowerShell dans celui-ci :

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Ce qui est réellement "live"

La V3 interroge au lancement du scan :
- La Centrale
- ParuVendu
- Zoomcar / Ouest-France Auto

Chaque résultat stocke :
- lien direct vers l'annonce
- prix
- année
- kilométrage
- source
- localisation lorsqu'elle est disponible
- options détectées dans le texte
- première et dernière date de détection
- prix minimum / maximum observé
- historique de prix
- estimation de revente à 2 ans
- score personnalisé

Le score est configurable avec trois poids :
- prix bas
- année récente
- faible kilométrage

## Leboncoin Live

La V3.1 inclut désormais un connecteur Leboncoin limité aux pages publiques de résultats.

Garde-fous :
- une requête par modèle avec pause ;
- pas de connexion à un compte ;
- pas de contournement de CAPTCHA, 403, 429 ou autre protection technique ;
- collecte limitée aux champs nécessaires au comparateur (modèle, année, km, prix, URL, options, localisation lorsqu'elle est visible) ;
- arrêt propre si le site refuse l'accès automatisé.

Le module d'import manuel reste disponible comme solution de secours.

## Persistance

La base et l'état sont conservés après fermeture de l'application :

- `%USERPROFILE%\.moto_scanner_v3\moto_scanner.db`
- `%USERPROFILE%\.moto_scanner_v3\state.json`

Tes modèles, filtres, historique et dernière recherche ne disparaissent donc pas à la fermeture du navigateur.

## Limites

Les sites peuvent modifier leur HTML. Une page `Diagnostic` est incluse pour tester chaque connecteur.
Aucun CAPTCHA, mécanisme anti-bot, connexion privée ou restriction technique n'est contourné.

## Note juridique

L'article L342-3 du Code de la propriété intellectuelle protège l'extraction/réutilisation de parties non substantielles
d'une base mise à disposition du public par une personne qui y a licitement accès. L'article L342-2 permet toutefois
au producteur d'interdire des extractions répétées et systématiques de parties non substantielles lorsqu'elles excèdent
manifestement les conditions d'utilisation normale. Le connecteur est donc volontairement limité en cadence et volume.


## V3.2 — recherche multi-alias + rayon géographique

### Alias de modèle
Chaque modèle dispose de plusieurs graphies reconnues. Exemple MT-07 :
- Yamaha MT-07
- Yamaha MT07
- Yamaha MT 07
- MT-07
- MT07
- MT 07
- variantes A2

Pour Leboncoin, plusieurs requêtes sont lancées avec ces alias puis les annonces sont dédupliquées par URL directe.

### Localisation
La barre latérale comprend maintenant :
- Code postal de départ
- Rayon en kilomètres

Le scanner utilise l'API géographique officielle française pour obtenir les coordonnées du code postal de départ
et des codes postaux présents dans les annonces, puis calcule la distance à vol d'oiseau (Haversine).

Une annonce dont la localisation n'est pas exploitable n'est pas supprimée : sa distance reste vide.
Cela évite de perdre une bonne annonce simplement parce que le site n'a pas affiché le code postal dans la carte.


## V3.3 — correction recherche géographique et modèles

### Modèles
La page "Modèles" ne contient plus aucun filtre d'année, prix ou kilométrage.
Elle sert uniquement à choisir les modèles recherchés.

Les seuls filtres prix / année / kilométrage sont désormais les sliders globaux de la barre latérale.

### Leboncoin
La recherche Leboncoin utilise en priorité une requête structurée avec :
- tous les alias du modèle dans une requête OR ;
- les coordonnées du code postal choisi ;
- le rayon choisi converti en mètres ;
- jusqu'à 3 pages de résultats ;
- déduplication par URL directe.

Exemple pour 75011 / 40 km :
- centre = coordonnées du code postal 75011 ;
- rayon natif = 40 000 mètres.

Le fallback HTML n'élimine plus une annonce si sa localisation est inconnue :
elle n'est rejetée que si sa distance est connue et supérieure au rayon.


## V3.4 — correction année / kilométrage / lieu

- L'année est désormais l'année véhicule/modèle issue en priorité des champs structurés Leboncoin
  (`regdate`, `vehicle_year`, `model_year`, etc.).
- La date de publication ou l'année courante n'est plus utilisée comme année modèle.
- Le kilométrage est lu en priorité depuis les champs structurés de kilométrage.
- En fallback texte, si plusieurs nombres en km existent, le parseur choisit la valeur véhicule plausible
  plutôt qu'une petite distance géographique.
- Les sliders globaux année/km sont appliqués après cette extraction corrigée.
- La colonne `Lieu` contient uniquement le code postal.
- Les colonnes `Vu depuis` et `Dernière vue` ont été retirées du tableau principal.
- L'historique est conservé en base mais les valeurs année/km/lieu sont mises à jour au prochain scan.


## V3.5 — pagination, rayon monotone, multi-sources, coups de cœur

### Rayon monotone
Une recherche à 100 km interroge aussi plusieurs rayons intérieurs (dont 50 km) puis fusionne les URLs.
Ainsi, une annonce trouvée à 50 km ne doit plus disparaître simplement parce que le volume à 100 km
a modifié les premières pages retournées.

### Pagination
- Leboncoin : jusqu'à 5 pages par rayon concentrique.
- La Centrale : plusieurs formes de pagination, jusqu'à 8 pages.
- ParuVendu : jusqu'à 8 pages.
- Zoomcar/Ouest-France Auto : jusqu'à 8 pages.

### Sources
Le tableau indique le nombre d'annonces provenant de chaque source immédiatement au-dessus des résultats.

### Coups de cœur
La première colonne du tableau est une case `❤️`.
Elle est persistée dans SQLite et reste cochée après fermeture/réouverture.


## V3.5.1 — correctif régression "0 résultat"

La V3.5 avait supprimé par erreur le fallback global du connecteur Leboncoin :
une erreur de la bibliothèque structurée pouvait interrompre le connecteur avant le fallback HTML.

Correctifs :
- restauration du fallback HTML Leboncoin ;
- une erreur de recherche structurée n'annule plus tout le scan ;
- sélection de sources vide/obsolète => toutes les sources valides sont réactivées ;
- les annonces déjà trouvées et encore compatibles avec les filtres courants sont conservées ;
- un scan externe temporairement défaillant ne remplace plus la dernière recherche valide par zéro résultat ;
- les erreurs des connecteurs sont distinguées d'un véritable "0 annonce avec ces filtres".


## V3.5.2 — correctif année modèle / kilométrage

Cette version restaure la logique stricte qui fonctionnait en V3.4.

### Année
- priorité absolue aux champs structurés du véhicule ;
- fallback uniquement sur des libellés explicites (`année`, `millésime`, `mise en circulation`, `model_year`, etc.) ;
- si un titre contient plusieurs années ambiguës, l'annonce est rejetée plutôt que mal classée ;
- l'année courante/publication n'est plus utilisée comme année modèle.

### Kilométrage
- priorité aux champs structurés de kilométrage ;
- fallback uniquement sur des valeurs explicitement suivies de `km` ;
- les petites distances géographiques ne sont plus prises pour l'odomètre ;
- si plusieurs valeurs existent, le kilométrage véhicule plausible est privilégié.

### Cache
Au premier lancement de V3.5.2, la dernière liste de résultats est vidée afin de forcer
un nouveau scan avec les parseurs corrigés. La base historique reste présente.
