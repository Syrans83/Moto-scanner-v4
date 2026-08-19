# Moto Scanner V4.1 Mobile

Cette version repart directement du moteur V3.5.2 PC.

Modifications par rapport à V3.5.2 :
- présentation mobile sous forme de cartes ;
- favoris tactiles ;
- ajout libre de modèles non présents dans le catalogue ;
- suggestion du modèle le plus proche ;
- diagnostic par source visible sur mobile ;
- fichiers de déploiement Streamlit Cloud.

La logique de scan, année, kilométrage, filtres et rayon reste celle de la V3.5.2.


## V4.2 — correctif Leboncoin sur hébergement cloud

Ordre des méthodes Leboncoin :
1. client structuré V3.5.2 ;
2. page publique `/recherche` ;
3. pages publiques indexables `/ck/motos/...` correspondant aux alias du modèle ;
4. page filtrée de catégorie constructeur/modèle lorsqu'elle est connue.

Les résultats sont ensuite dédupliqués par URL et soumis aux mêmes filtres globaux
prix / année / kilométrage / code postal / rayon que sur PC.

Le fallback cloud a été ajouté sans modifier les parseurs année/km de la V3.5.2.
