# Guide utilisateur — MERCURY CAD AI X

## 1. Première pièce en 3D, en une minute

```bash
pip install -r requirements.txt
uvicorn API.main:app --port 8000
```

Ouvrez **`http://localhost:8000/app`**. L'interface s'ouvre sur un document
vide avec une boîte de démonstration.

Tapez dans la ligne de commande, en bas :

```
BOITE longueur=4000 largeur=3000 hauteur=2700
CYLINDRE rayon=600 hauteur=3400 origine=5200,1500,0
SPHERE rayon=900 centre=2000,1500,3600
```

Chaque commande apparaît dans le journal, à droite, et l'objet s'affiche dans
la vue. **Clic gauche** fait tourner la vue, **Maj + clic** la déplace, la
**molette** zoome. Les boutons en haut à droite donnent les vues normalisées.

### Percer, raccorder, évider

Sélectionnez deux objets dans la palette **Objets** (clic, puis Maj + clic),
puis cliquez l'outil **soustraction** de l'onglet *Solide* : le second creuse
le premier. Les outils **raccordarete**, **chanfreinarete** et **gaine** de
l'onglet *Modification* travaillent sur l'objet sélectionné.

Tout ce que fait un bouton du ruban peut s'écrire dans la ligne de commande, et
inversement : ce sont les mêmes 98 commandes, décrites dans
`docs/MODELISATION_3D.md`.

### Ouvrir et enregistrer

**Ouvrir** accepte DWG, DXF, IFC, STEP, STL, OBJ, PLY, glTF, 3MF, COLLADA, les
nuages de points et les images. **Exporter** propose les 29 formats.
**Convertir** traduit un fichier d'un format à l'autre sans même l'ouvrir.

> Le DWG demande un moteur de conversion installé sur la machine (ODA File
> Converter, LibreDWG ou `ezdxf[odafc]`). Sans lui, MERCURY identifie quand même
> le fichier, sa version et son aperçu, et le message d'erreur indique quoi
> installer.

---

## 2. Premier plan en trois minutes

```bash
pip install -r requirements.txt
uvicorn API.main:app --port 8000
```

Le moteur génératif s'appelle depuis l'API ou l'assistant : choisissez
« maison » et 110 m². Trois variantes sont calculées en moins d'une seconde ;
la meilleure s'ouvre automatiquement.

## 3. Comprendre le score

Chaque variante porte un score : **plus bas est meilleur**. Il agrège six
termes, visibles dans `detail_score` :

| Terme | Ce qu'il pénalise |
|---|---|
| `surfaces` | écart au programme, sous les minima, au-dessus des maxima d'usage |
| `proportions` | pièces en couloir (élongation excessive) |
| `orientation` | chambres au nord, séjour sans soleil |
| `jour` | pièce de vie sans façade |
| `adjacences` | cuisine loin du séjour |
| `plomberie` | points d'eau dispersés, donc colonnes longues |

Un score de 2 à 5 correspond à un plan exploitable. Au-delà de 8, le programme
est probablement incompatible avec l'emprise.

## 4. Dessiner à la main

```bash
curl -X POST localhost:8000/api/v1/projects -d '{"name":"Mon projet"}'
curl -X POST localhost:8000/api/v1/projects/$ID/walls \
     -d '{"start":[0,0],"end":[10000,0],"thickness":300,"exterior":true}'
```

Tracez les quatre murs de l'enveloppe, puis les refends. Appelez ensuite
`rooms/rebuild` : les pièces apparaissent **si les murs se rejoignent**. Un
contour ouvert de plus de quelques centimètres empêche la détection.

## 5. Poser portes et fenêtres

`offset` est la distance depuis le **début** du mur, en millimètres. Une baie
qui déborde est refusée avec la longueur disponible dans le message.

## 6. Sortir les livrables

| Besoin | Appel |
|---|---|
| Quantités auditables | `GET /takeoff` — chaque ligne porte sa formule |
| Budget et délai | `GET /estimate` — devis par lot, chemin critique |
| Empreinte carbone | `GET /carbon` — leviers classés par gain réel |
| Performance énergétique | `GET /energy?isolation=neuf&climat=oceanique` |
| Maquette pour Revit | `POST /export {"format":"ifc"}` |

## 7. Questions fréquentes

**Aucune pièce n'est détectée.** Les murs ne se referment pas. Vérifiez que les
extrémités coïncident : la tolérance de fusion est de 120 mm.

**Les surfaces sont dix fois trop petites.** Les unités sont des millimètres :
un mur de 10 m se saisit `10000`, pas `10`.

**Le devis paraît bas.** La base de prix est indicative. Remplacez-la par la
vôtre en passant `price_book` à `CostEstimator`.

**L'étiquette énergétique semble optimiste.** La méthode est statique
mensuelle, destinée à l'esquisse. Elle ne remplace pas un calcul réglementaire,
et la sortie le rappelle dans le champ `methode`.
