# Référence de l'API — MERCURY CAD AI X

Base : `http://localhost:8000` · Documentation interactive : `/docs`
Format : JSON · Unités : millimètres pour les longueurs, m² pour les surfaces.

---

## Système

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/health` | Sonde de disponibilité. Ne touche pas la base, toujours rapide. |
| GET | `/ready` | Sonde de préparation : vérifie réellement l'accès à la base. |
| GET | `/api/v1/deliverables` | Registre des 70 livrables (filtrable par `groupe`). |
| GET | `/app` | Interface web de modélisation 3D. |

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0","uptime_seconds":12.4}
```

---

## Modélisation 3D

Toutes les routes CAO sont préfixées par `/api/v1/cad`.

### Catalogue

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/api/v1/cad/commands` | Les 98 commandes, filtrables par `groupe`. |
| GET | `/api/v1/cad/capabilities` | Commandes, formats, styles visuels, vues, accrochages. |
| GET | `/api/v1/cad/formats` | Matrice des formats, filtrable par `nature` et `capacite`. |

### Documents

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/cad/documents` | Crée un document (`nom`, `unites`). |
| GET | `/api/v1/cad/documents` | Documents ouverts. |
| GET | `/api/v1/cad/documents/{id}` | État, calques, fenêtre. `?detail=true` pour tout. |
| DELETE | `/api/v1/cad/documents/{id}` | Ferme le document. |
| GET | `/api/v1/cad/documents/{id}/entities` | Objets du document. |
| GET | `/api/v1/cad/documents/{id}/history` | Historique des commandes. |

### Commandes

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/cad/documents/{id}/command` | Exécute une commande. |
| POST | `/api/v1/cad/documents/{id}/script` | Exécute un script de commandes. |

```bash
curl -X POST localhost:8000/api/v1/cad/documents/doc-0001/command \
  -H 'Content-Type: application/json' \
  -d '{"commande":"BOITE","parametres":{"longueur":2000,"largeur":1000,"hauteur":500}}'
```

### Géométrie et rendu

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/api/v1/cad/documents/{id}/mesh` | Triangles, normales, arêtes vives, groupes. `?angle_aretes=0` renvoie toutes les arêtes. |
| GET | `/api/v1/cad/documents/{id}/curves` | Courbes et contours. |
| POST | `/api/v1/cad/documents/{id}/render` | Image PNG (`largeur`, `hauteur`, `style`, `vue`). |

### Fichiers

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/cad/documents/{id}/export` | Exporte dans l'un des 29 formats. |
| POST | `/api/v1/cad/documents/{id}/import` | Importe un fichier et le fusionne. |
| POST | `/api/v1/cad/files/identify` | Reconnaît un fichier à sa signature. |
| POST | `/api/v1/cad/files/open` | Ouvre un fichier dans un nouveau document. |
| POST | `/api/v1/cad/files/convert?cible=step` | Convertit sans ouvrir de document. |

```bash
curl -X POST 'localhost:8000/api/v1/cad/files/convert?cible=stl' \
  -F 'fichier=@plan.dxf' -o piece.stl
```

Le téléversement est plafonné à 64 Mo. Un fichier non reconnu renvoie 400 avec
la liste des extensions acceptées.

---

## Projets

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/projects` | Crée un projet vide. |
| GET | `/api/v1/projects` | Liste les projets. |
| GET | `/api/v1/projects/{id}` | Projet complet, avec l'historique des versions. |
| DELETE | `/api/v1/projects/{id}` | Suppression logique. |

**Erreurs** : `404` projet introuvable, `400` typologie inconnue.

---

## Conception générative

```bash
curl -X POST http://localhost:8000/api/v1/design/generate \
  -H "Content-Type: application/json" \
  -d '{"typologie":"maison","surface":110,"chambres":3,"variantes":3}'
```

Réponse : programme calé, emprise, variantes classées par score croissant.
Le champ `saturation` prévient quand la demande est incohérente (210 m² pour
trois chambres) au lieu de produire des chambres de 40 m².

`graine` fixe le générateur : à valeur égale, le résultat est identique.

---

## Édition

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/projects/{id}/walls` | Ajoute un mur. |
| POST | `/api/v1/projects/{id}/openings` | Pose une porte ou une fenêtre. |
| POST | `/api/v1/projects/{id}/rooms/rebuild` | Recalcule les pièces. |

Une baie qui déborde du mur renvoie `400` avec la longueur disponible.
Si aucun contour n'est fermé, l'état précédent est **conservé** et un
avertissement est renvoyé — le projet n'est jamais vidé silencieusement.

---

## Économie et environnement

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/api/v1/projects/{id}/takeoff` | Métré, chaque ligne avec sa formule. |
| GET | `/api/v1/projects/{id}/estimate` | Devis par lot + planning avec chemin critique. |
| GET | `/api/v1/projects/{id}/carbon` | Empreinte A1-A3, étiquette, leviers classés. |
| GET | `/api/v1/projects/{id}/energy` | Besoins, étiquette, actions prioritaires. |
| GET | `/api/v1/projects/{id}/certification` | Note multicritère et points à gagner. |

Paramètres : `devise`, `coef_region` (chiffrage) · `isolation`, `climat`
(énergie : `ancien`, `renove`, `neuf`, `passif` ; six climats).

---

## Jumeau numérique

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/v1/iot/sensors` | Déclare un capteur, rattaché à une pièce. |
| POST | `/api/v1/iot/readings` | Webhook d'ingestion (lot compatible pont MQTT). |
| GET | `/api/v1/projects/{id}/twin` | État courant et alertes pondérées par le BIM. |

---

## Exports

```bash
curl -X POST http://localhost:8000/api/v1/projects/{id}/export \
  -d '{"format":"ifc"}' > projet.ifc
```

Formats : `ifc` (IFC4 avec quantités), `obj`, `gltf`, `svg`, `json`.

---

## Codes d'erreur

| Code | Signification |
|---|---|
| 400 | Requête invalide — le message indique la contrainte violée. |
| 404 | Ressource introuvable. |
| 422 | Schéma non respecté (validation Pydantic). |
| 503 | Base indisponible (`/ready` uniquement). |
