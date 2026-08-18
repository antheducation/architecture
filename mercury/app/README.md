# MERCURY CAD AI X — PROJET TITAN

Logiciel de **modélisation 3D** et plateforme de conception assistée par
ordinateur : **modélisation solide → plan 2D → IA → BIM → métré →
environnement → jumeau numérique**.

Le noyau géométrique 3D (solides, opérations booléennes, maillages, rendu), les
98 commandes de modélisation, les 29 formats de fichiers, le lecteur de plans,
l'écrivain IFC4 et le moteur génératif sont écrits pour ce projet. Seul FastAPI
est requis pour exposer l'API ; tout le reste tient dans la bibliothèque
standard.

---

## Démarrage

```bash
pip install -r requirements.txt
uvicorn API.main:app --reload --port 8000
```

Interface de modélisation : **`/app`** · Documentation interactive : `/docs`
Sonde de disponibilité : `/health` · Sonde de préparation : `/ready`

```bash
python -m CAD_Core.main demo          # démonstration en ligne de commande
```

```bash
pytest -q                    # suite complète
docker compose up --build    # api + base + interface
```

---

## Ce que fait la plateforme

**Modélise en 3D.** Un noyau de solides facettisés avec opérations booléennes
exactes (arbre BSP), et les outils volumiques attendus d'un logiciel de CAO :
boîte, biseau, cylindre, cône, sphère, tore, pyramide, polysolide, hélice ;
extrusion avec dépouille, révolution, balayage avec torsion, lissage,
appuyer-tirer, épaissir ; raccord et chanfrein d'arêtes, gaine, coupe, section,
dépouille, décalage, séparation, empreinte ; déplacement, rotation, échelle,
alignement, symétrie et réseaux rectangulaire, polaire et sur trajectoire ;
lissage et affinage de maillage. **98 commandes** portant les noms d'AutoCAD,
en français et en anglais, avec leurs alias courts.

**Vérifie.** Chaque solide connaît son volume, son aire, son centre de gravité,
son inertie et son étanchéité. Les volumes produits par les outils sont
contrôlés par les tests contre leurs valeurs analytiques exactes.

**Conçoit.** Donnez un programme — 110 m², trois chambres — et le recuit simulé
explore un arbre de découpe pour trouver la disposition qui satisfait au mieux
les surfaces cibles, les proportions, l'orientation, l'accès au jour, les
adjacences et le regroupement des points d'eau. Le résultat est un projet BIM
complet, pas une image.

**Lit les plans.** Un plan professionnel dessine un mur par deux traits
parallèles : le moteur les apparie, fusionne les axes colinéaires au travers
des baies, puis les prolonge jusqu'aux intersections.

**Extrait les pièces.** Les axes de murs forment un arrangement planaire :
découpe aux intersections, fusion des sommets, élagage des brins pendants,
parcours des demi-arêtes. Aucune heuristique de remplissage.

**Chiffre.** Métré où chaque quantité porte sa formule, devis par lot, planning
avec chemin critique, empreinte carbone A1-A3 avec leviers classés par gain
réel, simulation énergétique sur six climats et quatre niveaux d'isolation.

**Échange.** 29 formats lus ou écrits : DWG, DXF (R12 à 2021), IFC4, STEP
AP203/AP214/AP242, IGES, STL, OBJ, PLY, OFF, glTF 2.0, GLB, 3MF, AMF, COLLADA,
VRML, X3D, 3DS, SVG, PDF vectoriel, PNG, BMP, PPM, TGA, JPEG, nuages de points
XYZ/PTS/CSV/LAS, et un format natif JSON sans perte. Tout est écrit sans
dépendance externe ; seul le DWG passe par un moteur de conversion installé sur
la machine (voir *Limites assumées*).

**Dessine.** Interface web de modélisation à `/app` : ruban construit à partir
du catalogue de commandes, vue 3D WebGL avec orbite, styles visuels, arêtes
vives, grille et axes, palettes de calques et de propriétés, ligne de commande
avec historique, import et export de tous les formats.

**Observe.** Les capteurs sont rattachés aux pièces du modèle : une dérive dans
un grand volume occupé est signalée comme plus grave que la même dans un local
technique.

---

## Architecture

```
Mercury/
├── CAD_Core/          noyau 3D : maths · solides · primitives · modélisation
│                      édition · transformations · maillages · document
│                      accrochages · annotation · vues · rendu · commandes
├── Interop/           DWG · DXF · IFC · STEP · IGES · maillages · images
│                      PDF · SVG · nuages de points · format natif
├── BIM_Engine/        modèle BIM · IFC4 · bibliothèque · collaboration · structure · fluides
├── AI_Engine/         génératif · vision · assistant · maintenance prédictive
├── Estimating/        métré · coûts · devis · optimisation budget
├── Sustainability/    carbone · énergie · certification
├── Construction/      planning · avancement · ressources · sécurité
├── Cloud_Platform/    jumeau numérique · IoT · multi-tenant · territoire
├── Database/          schéma SQL · migrations · dépôt versionné
├── Security/          authentification · chiffrement · contrôle d'accès
├── API/               FastAPI · schémas · dépendances · routes CAO
├── Frontend/          interface CAO WebGL (HTML/CSS/JS, sans compilation)
├── Mobile/            clients iOS et Android
└── tests/             suite de tests
```

**Principes.** Un seul contrat de données (`BuildingProject`) entre tous les
modules : toute brique est remplaçable. Chaque quantité est dérivée de la
géométrie, jamais saisie. À graine fixée, la génération redonne exactement le
même plan. Les modules qui approximent le disent dans leur sortie.

---

## Les 70 livrables

| Groupe | Description | Livré | Esquissé | Documenté |
|---|---|---|---|---|
| CORE | Systeme central : CAO, IA, interface, MVP | 11 | 0 | 0 |
| BIM | Moteur BIM, objets, standards IFC, metiers | 6 | 4 | 0 |
| COLLAB | Collaboration, versions, entreprise | 3 | 1 | 0 |
| CONSTRUCTION | Chantier : planning, suivi, qualite, securite | 2 | 8 | 0 |
| COST | Economie : metres, couts, devis | 3 | 1 | 0 |
| TWIN | Jumeau numerique, IoT, maintenance | 3 | 2 | 0 |
| GREEN | Environnement : carbone, energie, certification | 9 | 2 | 0 |
| CITY | Territoire : village et ville intelligents | 0 | 4 | 0 |
| MOBILE | Terrain : tablette, mobile, realite augmentee | 1 | 1 | 0 |
| BUSINESS | Marche, juridique, investisseurs, lancement | 1 | 1 | 7 |

Registre interrogeable : `GET /api/v1/deliverables` · Détail complet :
`docs/DELIVERABLES.md`

---

## Limites assumées

- Le **DWG** est un format binaire propriétaire non documenté : MERCURY
  l'identifie nativement (version exacte, page de codes, aperçu), mais la
  conversion de sa géométrie passe par un moteur installé sur la machine — ODA
  File Converter, LibreDWG ou `ezdxf[odafc]`. Sans moteur, l'erreur dit
  exactement quoi installer ; le DXF, lui, est lu et écrit nativement dans
  toutes ses versions.
- Les **solides sont facettisés** : un cylindre est un prisme à *n* faces, pas
  une surface analytique. Les volumes convergent vers la valeur exacte quand la
  finesse augmente ; l'écart est mesuré par les tests. Les raccords d'arêtes
  produisent des congés polygonaux, et les coins où trois raccords se
  rejoignent sont formés par l'intersection des surfaces voisines.
- La **lecture STEP et IFC** couvre les représentations facettisées (BREP). Un
  fichier décrivant des surfaces analytiques ou des extrusions paramétriques
  est refusé avec un message qui indique l'option d'export à activer.
- Le **JPEG** est lu et écrit via Pillow s'il est installé ; PNG, BMP, PPM et
  TGA sont écrits nativement.
- La **simulation énergétique** est une méthode statique mensuelle, pas une
  simulation dynamique horaire. Ni inertie, ni scénarios d'occupation, ni
  masques solaires. Ce n'est pas un calcul réglementaire.
- Les **modèles de vision** ont une architecture et une API réelles mais des
  **poids factices** : ils démontrent la chaîne, ils ne reconnaissent pas encore.
- Les modules **structure** et **fluides** sont des prédimensionnements
  d'esquisse, non substituables à des notes de calcul.
- Les groupes **chantier**, **territoire** et **réalité augmentée** sont
  esquissés : les interfaces existent, les moteurs restent à écrire.
