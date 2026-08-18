# MERCURY CAD AI X — PROJET TITAN

Logiciel de modélisation 3D et plateforme CAO/BIM assistée par IA, livré sous
deux formes équivalentes :

| Chemin | Contenu |
|---|---|
| `build_mercury_titan.py` | Générateur autonome : une exécution écrit tout le projet puis le valide. |
| `app/` | Le projet déjà généré, prêt à lancer. |

Les deux sont identiques au bit près : `build_mercury_titan.py` est reconstruit
depuis `app/`, de sorte que le générateur et le code ne peuvent pas diverger.

---

## Lancer l'application

```bash
cd app
pip install -r requirements.txt
uvicorn API.main:app --port 8000
```

Puis ouvrez **http://localhost:8000/app** — l'interface de modélisation 3D.
Documentation interactive de l'API : `/docs`.

```bash
python -m CAD_Core.main demo      # démonstration en ligne de commande
pytest -q                         # 262 tests
```

## Régénérer depuis le générateur

```bash
python build_mercury_titan.py --dir Mercury
```

Le script écrit les 121 fichiers, compile chaque module, exécute la suite de
tests, mesure la couverture, démarre l'API et interroge ses sondes. Il n'annonce
un succès que si tout passe réellement ; toute étape non exécutée est signalée
et le projet n'est alors **pas** déclaré validé.

Options : `--force` (écrase la cible), `--no-verify` (génère sans valider),
`--allow-skip` (tolère l'absence de pytest ou FastAPI, sans annoncer de succès).

---

## Ce que contient l'application

**Noyau de modélisation 3D** — solides facettisés, opérations booléennes exactes
par arbre BSP, propriétés mécaniques, contrôle d'étanchéité.

**98 commandes** portant les noms d'AutoCAD, en français et en anglais, avec
leurs alias : boîte, biseau, cylindre, cône, sphère, tore, pyramide, polysolide,
hélice, extrusion (avec dépouille, direction ou trajectoire), révolution,
balayage (avec torsion et mise à l'échelle), lissage, appuyer-tirer, épaissir,
union, soustraction, intersection, interférence, raccord et chanfrein d'arêtes,
gaine, coupe, section, dépouille, décalage, séparation, empreinte, extraction
d'arêtes, vérification, propriétés mécaniques, déplacement, rotation, échelle,
alignement, symétrie, réseaux rectangulaire/polaire/sur trajectoire, lissage et
affinage de maillage, dessin 2D, cotation, hachures, tableaux, calques, blocs,
SCU, présentations, accrochages, vues normalisées, styles visuels, rendu,
lignes cachées, import et export.

**29 formats de fichiers** — DWG, DXF (R12 à 2021), IFC4, STEP AP203/214/242,
IGES, STL, OBJ, PLY, OFF, glTF 2.0, GLB, 3MF, AMF, COLLADA, VRML, X3D, 3DS, SVG,
PDF vectoriel, PNG, BMP, PPM, TGA, JPEG, nuages de points XYZ/PTS/CSV/LAS, plus
un format natif JSON sans perte.

**Interface web** — ruban construit depuis le catalogue de commandes, vue 3D
WebGL, palettes de calques et de propriétés, ligne de commande avec historique,
ouverture et export de tous les formats.

**Plateforme CAO/BIM** — conception générative, lecture de plans, modèle BIM et
IFC4, métré, devis, planning, carbone, énergie, certification, jumeau numérique
et IoT, sécurité et contrôle d'accès.

Détail complet : `app/docs/MODELISATION_3D.md` (commandes et formats),
`app/docs/API_REFERENCE.md`, `app/docs/USER_GUIDE.md`, `app/README.md`.

---

## Limites assumées

- Le **DWG** est un format binaire propriétaire non documenté. MERCURY
  l'identifie nativement — version exacte, page de codes, aperçu — mais la
  conversion de sa géométrie passe par un moteur installé sur la machine : ODA
  File Converter, LibreDWG ou `ezdxf[odafc]`. Sans moteur, le message d'erreur
  indique quoi installer ; le DXF, lui, est lu et écrit nativement dans toutes
  ses versions, et c'est le format d'échange qu'attend AutoCAD.
- Les **solides sont facettisés** : un cylindre est un prisme à *n* faces. Les
  volumes convergent vers la valeur exacte quand la finesse augmente, et l'écart
  est mesuré par les tests.
- La **lecture STEP et IFC** couvre les représentations facettisées (BREP) ; un
  fichier en surfaces analytiques est refusé avec l'option d'export à activer.
- Le **JPEG** est lu et écrit via Pillow s'il est installé ; PNG, BMP, PPM et
  TGA le sont nativement.
- Les autres limites du volet BIM/IA sont listées dans `app/README.md`.
