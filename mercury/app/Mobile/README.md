# MERCURY Mobile (livrable #63)

Client terrain pour tablette et telephone. L'application mobile ne reimplemente
aucun moteur : elle consomme l'API REST, ce qui garantit que les chiffres
affiches sur le chantier sont exactement ceux du bureau d'etudes.

## Architecture

```
Mobile/
├── shared/api_client.js     client HTTP commun iOS / Android
├── ios/                     enveloppe SwiftUI (WKWebView + API native)
└── android/                 enveloppe Kotlin (WebView + API native)
```

## Ecrans

| Ecran | Role |
|---|---|
| Projets | liste, recherche, ouverture hors ligne du dernier projet |
| Plan | consultation 2D, cotes, surfaces |
| Metre | quantites et devis, partage PDF |
| Jumeau | releves capteurs, alertes en temps reel |
| Realite augmentee | superposition du modele sur la vue camera (livrable #48) |

## Mode hors ligne

Le dernier projet consulte est mis en cache au format JSON. Les mesures
saisies sur le chantier sont accumulees et renvoyees des le retour du reseau.
