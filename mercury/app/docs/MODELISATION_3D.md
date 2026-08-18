# Modélisation 3D — commandes et formats

MERCURY CAD AI X expose un noyau de modélisation solide complet. Ce document
est **généré depuis le code** : il liste exactement ce que le logiciel sait
faire, commande par commande et format par format.

Toute commande s'appelle de trois façons, avec le même résultat :

```bash
# ligne de commande de l'interface
BOITE longueur=2000 largeur=1000 hauteur=500
```

```python
from CAD_Core.commands import CommandInterpreter
cli = CommandInterpreter()
cli.execute("BOITE longueur=2000 largeur=1000 hauteur=500")
```

```bash
curl -X POST localhost:8000/api/v1/cad/documents/doc-0001/command \
  -H 'Content-Type: application/json' \
  -d '{"commande":"BOITE","parametres":{"longueur":2000}}'
```

---

## Les 98 commandes

### Solides primitifs

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `BISEAU` | `WEDGE` | — | Demi-boite coupee en diagonale : rampe, pente |
| `BOITE` | `BOX` | `B` | Pave droit defini par ses trois dimensions |
| `CONE` | `CONE` | — | Cone plein ou tronque |
| `CYLINDRE` | `CYLINDER` | `CYL` | Cylindre droit ou tronconique |
| `POLYSOLIDE` | `POLYSOLID` | `PSOLIDE` | Mur d'epaisseur constante suivant une polyligne |
| `PYRAMIDE` | `PYRAMID` | `PYR` | Pyramide de 3 a 32 cotes, pleine ou tronquee |
| `SPHERE` | `SPHERE` | — | Sphere |
| `TORE` | `TORUS` | — | Tore |

### Solides issus d'un profil

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `APPUYERTIRER` | `PRESSPULL` | `APT` | Pousse ou tire une zone fermee |
| `BALAYAGE` | `SWEEP` | — | Deplace un profil le long d'une trajectoire |
| `EPAISSIR` | `THICKEN` | — | Donne une epaisseur a une surface |
| `EXTRUSION` | `EXTRUDE` | `EXT` | Extrude un contour ferme en volume |
| `LISSAGE` | `LOFT` | — | Relie plusieurs sections par une peau continue |
| `REVOLUTION` | `REVOLVE` | `REV` | Fait tourner un profil autour d'un axe |

### Opérations booléennes

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `INTERFERENCE` | `INTERFERE` | `INTERF` | Detecte les collisions entre solides |
| `INTERSECTION` | `INTERSECT` | `IN` | Ne garde que la matiere commune |
| `SOUSTRACTION` | `SUBTRACT` | `SU` | Retire des solides d'un solide de base |
| `UNION` | `UNION` | `UNI` | Fusionne plusieurs solides |

### Édition de solides

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `CHANFREINARETE` | `CHAMFEREDGE` | `CHA` | Coupe les aretes vives a plat |
| `CONVENSOLIDE` | `CONVTOSOLID` | — | Ferme une surface pour en faire un solide |
| `CONVENSURFACE` | `CONVTOSURFACE` | — | Transforme un solide en surface |
| `COUPE` | `SLICE` | `SL` | Tranche un solide par un plan |
| `DECALAGE` | `OFFSET` | `DE` | Decale les faces d'un solide |
| `DEPOUILLE` | `TAPER` | — | Incline la matiere d'un cote d'un plan |
| `EMPREINTE` | `IMPRINT` | — | Imprime les aretes d'un solide sur un autre |
| `GAINE` | `SHELL` | — | Evide un solide en laissant une paroi |
| `RACCORDARETE` | `FILLETEDGE` | `RACC` | Arrondit les aretes vives d'un solide |
| `SECTION` | `SECTION` | — | Contour de l'intersection avec un plan |
| `SEPARER` | `SEPARATE` | — | Eclate un solide en volumes disjoints |
| `VERIFSOLIDE` | `SOLIDCHECK` | — | Controle l'etancheite d'un solide |
| `XARETES` | `XEDGES` | — | Extrait le filaire d'un solide |

### Déplacements et réseaux

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `ALIGNER3D` | `3DALIGN` | `AL` | Aligne la selection sur des points cibles |
| `COPIER` | `COPY` | `CO` | Copie la selection |
| `DEPLACER3D` | `3DMOVE` | `DEPLACER`, `M` | Deplace la selection |
| `ECHELLE` | `3DSCALE` | `SC` | Met la selection a l'echelle |
| `EFFACER` | `ERASE` | `E`, `SUPPRIMER` | Efface la selection |
| `MIROIR3D` | `MIRROR3D` | `MI3` | Symetrie par rapport a un plan |
| `RESEAU3D` | `3DARRAY` | `RESEAU` | Reseau rectangulaire en trois dimensions |
| `RESEAUCHEMIN` | `ARRAYPATH` | `RESC` | Reseau le long d'une trajectoire |
| `RESEAUPOLAIRE` | `ARRAYPOLAR` | `RESP` | Reseau autour d'un axe |
| `ROTATION3D` | `3DROTATE` | `RO3` | Tourne la selection autour d'un axe |

### Surfaces

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `SURFPLAN` | `PLANESURF` | — | Surface pleine sur un contour ferme |
| `SURFREGLE` | `RULESURF` | — | Surface tendue entre deux courbes |

### Maillages

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `AFFINERMAILLE` | `MESHREFINE` | — | Subdivise sans deformer |
| `LISSERMAILLE` | `MESHSMOOTH` | — | Lisse un maillage par subdivision |
| `SOUDER` | `WELD` | — | Fusionne les sommets et repare le maillage |
| `TRIANGULER` | `TRIANGULATE` | — | Convertit toutes les faces en triangles |

### Courbes

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `HELICE` | `HELIX` | — | Helice : ressort, rampe, escalier helicoidal |

### Dessin 2D

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `ARC` | `ARC` | `A` | Arc de cercle |
| `CERCLE` | `CIRCLE` | `C` | Cercle |
| `ELLIPSE` | `ELLIPSE` | `EL` | Ellipse |
| `LIGNE` | `LINE` | `L` | Segment de droite |
| `POINT` | `POINT` | `PO` | Point isole |
| `POLYGONE` | `POLYGON` | `POL` | Polygone regulier |
| `POLYLIGNE` | `PLINE` | `PL` | Polyligne ouverte ou fermee |
| `RECTANG` | `RECTANGLE` | `REC` | Rectangle |
| `SPLINE` | `SPLINE` | `SPL` | Courbe passant par des points |

### Annotation et cotation

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `COTALI` | `DIMALIGNED` | — | Cote alignee sur le segment |
| `COTANG` | `DIMANGULAR` | — | Cote angulaire |
| `COTDIA` | `DIMDIAMETER` | — | Cote de diametre |
| `COTLIN` | `DIMLINEAR` | `COTL` | Cote lineaire |
| `COTRAYON` | `DIMRADIUS` | — | Cote de rayon |
| `HACHURES` | `HATCH` | `H` | Remplit un contour ferme |
| `LIGNEDEREPERE` | `MLEADER` | `REPERE` | Fleche de renvoi avec texte |
| `NUAGEREV` | `REVCLOUD` | — | Nuage de revision |
| `TABLEAU` | `TABLE` | — | Nomenclature ou legende |
| `TEXTMULT` | `MTEXT` | `T`, `TEXTE` | Texte multiligne |

### Mesures

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `MESURER` | `MEASUREGEOM` | `MES` | Distance, aire, volume, angle |
| `PROPMECA` | `MASSPROP` | — | Volume, masse, inertie et centre de gravite |

### Organisation du dessin

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `ANNULER` | `UNDO` | `U` | Annule la derniere action |
| `BLOC` | `BLOCK` | `B_` | Enregistre une selection comme bloc |
| `CALQUE` | `LAYER` | `LA` | Cree ou active un calque |
| `DECOMPOSER` | `EXPLODE` | `X` | Detache les objets de leur bloc |
| `ETAT` | `STATUS` | — | Fiche du document |
| `INSERER` | `INSERT` | `I` | Insere une occurrence de bloc |
| `LISTE` | `LIST` | `LI` | Detail des objets selectionnes |
| `PRESENTATION` | `LAYOUT` | — | Ajoute un espace papier |
| `PURGER` | `PURGE` | — | Supprime les calques et blocs inutilises |
| `RETABLIR` | `REDO` | — | Retablit l'action annulee |
| `SCU` | `UCS` | — | Definit le systeme de coordonnees utilisateur |
| `SELECTIONNER` | `SELECT` | `SEL` | Selectionne des objets |

### Aides au dessin

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `ACCROBJ` | `OSNAP` | `OS` | Regle les accrochages aux objets |
| `ACCROCHER` | `SNAPPOINT` | — | Renvoie le point accroche le plus proche du curseur |
| `ORTHO` | `ORTHO` | — | Active ou desactive le mode ortho |
| `RESOL` | `SNAP` | — | Accrochage a la grille |

### Vues et rendu

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `MASQUE` | `HIDE` | — | Filaire sans les aretes cachees, en vectoriel |
| `ORBITE3D` | `3DORBIT` | `ORB` | Fait tourner la vue |
| `PAN` | `PAN` | `P` | Deplace la vue |
| `PLANDECOUPE` | `SECTIONPLANE` | — | Ajoute un plan de coupe a la vue |
| `RENDU` | `RENDER` | `RR` | Calcule une image du modele |
| `STYLESVISUELS` | `VSCURRENT` | `SV` | Change le style visuel |
| `VUE` | `VIEW` | `V` | Enregistre une vue nommee |
| `VUEPOINT` | `VPOINT` | `VP` | Vue normalisee : dessus, face, isometrique... |
| `ZOOM` | `ZOOM` | `Z` | Zoom avant, arriere ou etendu |

### Fichiers

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `EXPORTER` | `EXPORT` | `EXP` | Exporte le document dans un format d'echange |
| `FORMATS` | `FILEFORMATS` | — | Liste les formats lus et ecrits |
| `IMPORTER` | `IMPORT` | `IMP` | Importe un fichier et le fusionne au document |

### Général

| Commande | AutoCAD | Alias | Rôle |
|---|---|---|---|
| `AIDE` | `HELP` | `?` | Aide sur une commande ou catalogue complet |

---

## Les 29 formats de fichiers

| Format | Extensions | Catégorie | Lecture | Écriture | Remarque |
|---|---|---|---|---|---|
| AutoCAD DWG | `.dwg` | CAO | oui | oui | Identification, version et apercu en natif ; la geometrie passe par un moteur de conversion installe sur la machine. |
| AutoCAD DXF (R12 a 2021) | `.dxf` | CAO | oui | oui | Lecture et ecriture natives, toutes versions. |
| IFC 4 (BIM) | `.ifc` | BIM | oui | oui | Echange BIM normalise ISO 16739. |
| STEP AP203/AP214/AP242 | `.step` `.stp` | Mecanique | oui | oui | BREP facettise, lu par tous les CAO. |
| IGES 5.3 | `.iges` `.igs` | Mecanique | — | oui | Surfaces planes, entite 106. |
| STL | `.stl` | Impression 3D | oui | oui | ASCII et binaire, detection automatique. |
| Wavefront OBJ | `.obj` | 3D | oui | oui | Materiaux exportes dans un fichier .mtl associe. |
| Bibliotheque de materiaux OBJ | `.mtl` | 3D | — | oui |  |
| Stanford PLY | `.ply` | 3D | oui | oui | ASCII et binaire. |
| Object File Format | `.off` | 3D | oui | oui |  |
| glTF 2.0 | `.gltf` | 3D web | oui | oui |  |
| glTF binaire | `.glb` | 3D web | oui | oui |  |
| 3D Manufacturing Format | `.3mf` | Impression 3D | oui | oui |  |
| Additive Manufacturing Format | `.amf` | Impression 3D | — | oui |  |
| COLLADA | `.dae` | 3D | oui | oui |  |
| VRML 2.0 | `.wrl` `.vrml` | 3D | — | oui |  |
| X3D | `.x3d` | 3D | — | oui |  |
| Autodesk 3D Studio | `.3ds` | 3D | — | oui | Limite du format : 65 535 sommets par objet. |
| SVG | `.svg` | Vectoriel | oui | oui | Export de plans et import de traces. |
| PDF vectoriel | `.pdf` | Document | — | oui | Planches multipages avec cartouche. |
| PNG | `.png` | Image | oui | oui |  |
| Windows Bitmap | `.bmp` | Image | oui | oui |  |
| Portable Pixmap | `.ppm` | Image | oui | oui |  |
| Targa | `.tga` | Image | — | oui |  |
| JPEG | `.jpg` `.jpeg` | Image | oui | oui | Lecture et ecriture via Pillow. |
| Nuage de points XYZ / PTS | `.xyz` `.pts` `.asc` | Releve | oui | oui |  |
| Points CSV | `.csv` | Releve | oui | oui |  |
| LiDAR LAS | `.las` | Releve | oui | oui | LAS 1.0 a 1.4, formats de point 0 a 5. |
| Modele MERCURY (JSON) | `.json` | Natif | oui | oui | Format natif : tout le document, sans perte. |

---

## Vérification des volumes

Les outils volumiques sont contrôlés contre leurs valeurs analytiques :

| Outil | Cas testé | Écart admis |
|---|---|---|
| Boîte, biseau, pyramide | volume exact | 0 |
| Cylindre, cône | π r² h et π r² h ⁄ 3 | 0,1 % à 180 facettes |
| Sphère | 4⁄3 π r³ | 0,5 % à 64×32 facettes |
| Tore | 2 π² R r² | 1 % à 64×32 facettes |
| Extrusion, extrusion percée | section × hauteur | exact |
| Extrusion avec dépouille | tronc de pyramide | exact |
| Révolution totale et partielle | π (R²−r²) h | 0,3 % |
| Balayage droit | π r² L | 0,3 % |
| Lissage | h⁄3 (A₁+A₂+√A₁A₂) | exact |
| Union, soustraction, intersection | volumes combinés | 10⁻⁶ |
| Gaine | a³ − (a−2e)³ | 10⁻⁶ |
| Décalage | (a±2d)³ | 10⁻⁶ |
| Raccord de toutes les arêtes | somme de Minkowski | 1 % |

Chaque solide produit est en outre vérifié **étanche** : toute arête est
partagée par exactement deux faces, et le volume signé est positif.

---

## Styles visuels

`filaire_2d`, `filaire_3d`, `cache`, `réaliste`, `conceptuel`,
`ombre_avec_aretes`, `nuances_de_gris`, `esquisse`, `rayons_x`.

## Vues normalisées

`dessus`, `dessous`, `face`, `arriere`, `gauche`, `droite`,
`iso_sud_ouest`, `iso_sud_est`, `iso_nord_est`, `iso_nord_ouest`.

## Accrochages aux objets (OSMODE)

`extremite`, `milieu`, `centre`, `noeud`, `quadrant`, `intersection`,
`insertion`, `perpendiculaire`, `tangente`, `proche`, `parallele`.
