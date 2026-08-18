"""Interpreteur de commandes compatible AutoCAD.

C'est la ligne de commande du logiciel : elle accepte les noms francais et
anglais, les alias courts habituels (L, C, EXT, UNI, SU, IN, FI, CHA, RE3),
et pilote un `CadDocument`. L'interface graphique, l'API REST et les scripts
passent tous par ce meme point d'entree, ce qui garantit qu'une commande se
comporte partout de la meme facon.

    interpreteur = CommandInterpreter(document)
    interpreteur.execute("BOITE longueur=1000 largeur=500 hauteur=300")
    interpreteur.execute("UNION", handles=["101", "102"])
"""
from __future__ import annotations

import math
import shlex
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import annotate, mesh_tools, modeling, primitives, solid_edit, transform3d
from .document import CadDocument, Entity
from .math3d import BBox3, Mat4, ORIGIN, Plane, Vec3, X_AXIS, Y_AXIS, Z_AXIS
from .profiles import Curve, Profile
from .render_engine import Renderer3D
from .snapping import SnapEngine
from .solid import Solid, interfere, intersect_all, subtract_all, union_all
from .view3d import Camera, STANDARD_VIEWS, VISUAL_STYLES, Viewport


class CommandError(ValueError):
    """Commande inconnue, parametre invalide ou selection inadequate."""


@dataclass
class Command:
    """Fiche d'une commande : nom, alias, groupe, parametres, aide."""

    name: str
    handler: Callable
    group: str = "general"
    english: str = ""
    aliases: Tuple[str, ...] = ()
    summary: str = ""
    parameters: Dict[str, str] = field(default_factory=dict)
    modifies: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "anglais": self.english,
                "alias": list(self.aliases), "groupe": self.group,
                "resume": self.summary, "parametres": self.parameters,
                "modifie": self.modifies}


REGISTRY: Dict[str, Command] = {}
LOOKUP: Dict[str, str] = {}


def command(name: str, group: str = "general", english: str = "",
            aliases: Sequence[str] = (), summary: str = "",
            parameters: Optional[Dict[str, str]] = None,
            modifies: bool = True):
    """Enregistre une commande et tous ses noms d'appel."""
    def decorator(handler: Callable) -> Callable:
        entry = Command(name, handler, group, english, tuple(aliases), summary,
                        dict(parameters or {}), modifies)
        REGISTRY[name] = entry
        for label in (name, english, *aliases):
            if label:
                LOOKUP[label.upper()] = name
        return handler
    return decorator


class CommandInterpreter:
    """Execute les commandes sur un document."""

    def __init__(self, document: Optional[CadDocument] = None) -> None:
        self.document = document or CadDocument()
        self.snap = SnapEngine()
        self.viewport = Viewport()
        self.renderer = Renderer3D()
        self.history: List[Dict[str, Any]] = []
        self.annotations: List[Dict[str, Any]] = []

    # -- resolution --------------------------------------------------------
    @staticmethod
    def resolve(name: str) -> Command:
        key = LOOKUP.get((name or "").strip().upper())
        if key is None:
            suggestions = sorted(
                label for label in LOOKUP
                if label.startswith((name or "")[:3].upper()))[:6]
            raise CommandError(
                "commande inconnue : %r%s" % (
                    name,
                    " — vouliez-vous dire %s ?" % ", ".join(suggestions)
                    if suggestions else ""))
        return REGISTRY[key]

    @staticmethod
    def parse(line: str) -> Tuple[str, Dict[str, Any]]:
        """Decoupe « BOITE longueur=1000 origine=0,0,0 » en nom et parametres."""
        tokens = shlex.split(line or "")
        if not tokens:
            raise CommandError("ligne de commande vide")
        name = tokens[0]
        arguments: Dict[str, Any] = {}
        positional: List[str] = []
        for token in tokens[1:]:
            if "=" in token:
                key, _, value = token.partition("=")
                arguments[key.strip()] = _convert(value)
            else:
                positional.append(token)
        if positional:
            arguments["_positionnels"] = [_convert(v) for v in positional]
        return name, arguments

    def execute(self, line: str, **overrides) -> Dict[str, Any]:
        """Execute une ligne de commande ou un nom de commande."""
        if " " in (line or "").strip() or "=" in (line or ""):
            name, arguments = self.parse(line)
        else:
            name, arguments = (line or "").strip(), {}
        arguments.update(overrides)
        arguments.pop("_positionnels", None)
        entry = self.resolve(name)
        if entry.modifies:
            self.document.snapshot()
        try:
            result = entry.handler(self, **arguments)
        except CommandError:
            raise
        except TypeError as error:
            raise CommandError("parametres invalides pour %s : %s"
                               % (entry.name, error))
        except (ValueError, KeyError) as error:
            raise CommandError("%s : %s" % (entry.name, error))
        record = {"commande": entry.name, "parametres": _summarise(arguments),
                  "resultat": result}
        self.history.append(record)
        return {"commande": entry.name, "groupe": entry.group, **(result or {})}

    def run_script(self, text: str) -> List[Dict[str, Any]]:
        """Execute un script de commandes (equivalent d'un fichier .scr)."""
        out: List[Dict[str, Any]] = []
        for raw in (text or "").splitlines():
            line = raw.split(";")[0].strip()
            if not line:
                continue
            out.append(self.execute(line))
        return out

    # -- utilitaires de selection -----------------------------------------
    def targets(self, handles: Optional[Sequence[str]] = None) -> List[Entity]:
        chosen = list(handles) if handles else list(self.document.selection)
        if not chosen:
            raise CommandError(
                "aucun objet selectionne : indiquez handles=[...] ou lancez "
                "d'abord SELECTIONNER")
        entities = []
        for handle in chosen:
            if handle not in self.document.entities:
                raise CommandError("objet inconnu : %s" % handle)
            entities.append(self.document.entities[handle])
        return entities

    def solids(self, handles: Optional[Sequence[str]] = None) -> List[Solid]:
        out = [e.geometry for e in self.targets(handles)
               if isinstance(e.geometry, Solid)]
        if not out:
            raise CommandError("la selection ne contient aucun solide")
        return out

    def add(self, geometry, name: str = "", layer: Optional[str] = None
            ) -> Dict[str, Any]:
        entity = self.document.add(geometry, layer=layer, name=name)
        return {"handle": entity.handle, "objet": entity.to_dict()}

    def catalog(self, group: Optional[str] = None) -> List[Dict[str, Any]]:
        """Catalogue complet des commandes, pour le ruban et l'aide."""
        return [entry.to_dict() for entry in REGISTRY.values()
                if not group or entry.group == group]

    def groups(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for entry in REGISTRY.values():
            counts[entry.group] = counts.get(entry.group, 0) + 1
        return counts


def _convert(value: str):
    """Convertit un argument texte : nombre, booleen, liste ou point."""
    text = (value or "").strip()
    lowered = text.lower()
    if lowered in ("vrai", "true", "oui", "on"):
        return True
    if lowered in ("faux", "false", "non", "off"):
        return False
    if "," in text:
        parts = [p for p in text.split(",") if p != ""]
        converted = [_convert(p) for p in parts]
        return converted
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _summarise(arguments: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in arguments.items():
        if isinstance(value, (list, tuple)) and len(value) > 8:
            out[key] = "%d valeurs" % len(value)
        else:
            out[key] = value
    return out


def _profile(source, elevation: float = 0.0) -> Profile:
    """Accepte un Profile, une liste de points ou un handle d'objet."""
    if isinstance(source, Profile):
        return source
    if isinstance(source, Curve):
        return Profile(list(source.points))
    if isinstance(source, (list, tuple)) and source:
        if isinstance(source[0], (list, tuple)):
            return Profile.from_2d(source, elevation)
        flat = list(source)
        points = [flat[i:i + 3] for i in range(0, len(flat) - 2, 3)]
        return Profile.from_2d(points, elevation)
    raise CommandError("profil illisible : fournissez une liste de points")


# ===========================================================================
# Creation de solides primitifs
# ===========================================================================
@command("BOITE", "solides_primitifs", "BOX", ("B",),
         "Pave droit defini par ses trois dimensions",
         {"longueur": "mm", "largeur": "mm", "hauteur": "mm",
          "origine": "x,y,z", "centre": "vrai pour centrer sur l'origine"})
def _box(self, longueur=1000.0, largeur=1000.0, hauteur=1000.0,
         origine=(0, 0, 0), centre=False, materiau="default", calque=None):
    return self.add(primitives.box(longueur, largeur, hauteur, origine, centre,
                                   materiau), "boite", calque)


@command("BISEAU", "solides_primitifs", "WEDGE", (),
         "Demi-boite coupee en diagonale : rampe, pente",
         {"longueur": "mm", "largeur": "mm", "hauteur": "mm"})
def _wedge(self, longueur=1000.0, largeur=1000.0, hauteur=1000.0,
           origine=(0, 0, 0), materiau="default", calque=None):
    return self.add(primitives.wedge(longueur, largeur, hauteur, origine,
                                     materiau), "biseau", calque)


@command("CYLINDRE", "solides_primitifs", "CYLINDER", ("CYL",),
         "Cylindre droit ou tronconique",
         {"rayon": "mm", "hauteur": "mm", "segments": "facettes",
          "rayon_superieur": "mm, pour un tronc de cone"})
def _cylinder(self, rayon=500.0, hauteur=1000.0, origine=(0, 0, 0), segments=48,
              rayon_superieur=None, axe=(0, 0, 1), materiau="default",
              calque=None):
    return self.add(primitives.cylinder(rayon, hauteur, origine, segments,
                                        rayon_superieur, axe, materiau),
                    "cylindre", calque)


@command("CONE", "solides_primitifs", "CONE", (),
         "Cone plein ou tronque", {"rayon": "mm", "hauteur": "mm"})
def _cone(self, rayon=500.0, hauteur=1000.0, origine=(0, 0, 0), segments=48,
          rayon_superieur=0.0, materiau="default", calque=None):
    return self.add(primitives.cone(rayon, hauteur, origine, segments,
                                    rayon_superieur, (0, 0, 1), materiau),
                    "cone", calque)


@command("SPHERE", "solides_primitifs", "SPHERE", (),
         "Sphere", {"rayon": "mm", "centre": "x,y,z"})
def _sphere(self, rayon=500.0, centre=(0, 0, 0), segments=48, anneaux=None,
            materiau="default", calque=None):
    return self.add(primitives.sphere(rayon, centre, segments, anneaux,
                                      materiau), "sphere", calque)


@command("TORE", "solides_primitifs", "TORUS", (),
         "Tore", {"rayon": "mm", "rayon_tube": "mm"})
def _torus(self, rayon=500.0, rayon_tube=100.0, centre=(0, 0, 0), segments=48,
           segments_tube=24, materiau="default", calque=None):
    return self.add(primitives.torus(rayon, rayon_tube, centre, segments,
                                     segments_tube, materiau), "tore", calque)


@command("PYRAMIDE", "solides_primitifs", "PYRAMID", ("PYR",),
         "Pyramide de 3 a 32 cotes, pleine ou tronquee",
         {"rayon": "mm", "hauteur": "mm", "cotes": "nombre de cotes"})
def _pyramid(self, rayon=500.0, hauteur=1000.0, cotes=4, origine=(0, 0, 0),
             rayon_superieur=0.0, materiau="default", calque=None):
    return self.add(primitives.pyramid(rayon, hauteur, cotes, origine,
                                       rayon_superieur, True, materiau),
                    "pyramide", calque)


@command("POLYSOLIDE", "solides_primitifs", "POLYSOLID", ("PSOLIDE",),
         "Mur d'epaisseur constante suivant une polyligne",
         {"points": "liste de points", "largeur": "mm", "hauteur": "mm",
          "justification": "gauche, centre ou droite"})
def _polysolid(self, points=None, largeur=200.0, hauteur=2500.0, ferme=False,
               justification="centre", materiau="default", calque=None):
    if not points:
        raise CommandError("POLYSOLIDE : fournissez points=[[x,y,z], ...]")
    return self.add(primitives.polysolid(points, largeur, hauteur, ferme,
                                         justification, 0.0, materiau),
                    "polysolide", calque)


@command("HELICE", "courbes", "HELIX", (),
         "Helice : ressort, rampe, escalier helicoidal",
         {"rayon": "mm", "hauteur": "mm", "tours": "nombre de tours"})
def _helix(self, centre=(0, 0, 0), rayon=100.0, rayon_superieur=None,
           hauteur=200.0, tours=3.0, horaire=False, calque=None):
    return self.add(Curve.helix(centre, rayon, rayon_superieur, hauteur, tours,
                                horaire), "helice", calque)


# ===========================================================================
# Solides issus d'un profil
# ===========================================================================
@command("EXTRUSION", "solides_profil", "EXTRUDE", ("EXT",),
         "Extrude un contour ferme en volume",
         {"profil": "liste de points", "hauteur": "mm",
          "depouille": "angle en degres", "direction": "vecteur complet"})
def _extrude(self, profil=None, hauteur=1000.0, depouille=0.0, direction=None,
             trajectoire=None, materiau="default", calque=None, handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    path = None
    if trajectoire:
        path = trajectoire if isinstance(trajectoire, Curve) else \
            Curve.polyline(trajectoire)
    return self.add(modeling.extrude(_profile(profil), hauteur, direction,
                                     depouille, path, materiau), "extrusion",
                    calque)


@command("REVOLUTION", "solides_profil", "REVOLVE", ("REV",),
         "Fait tourner un profil autour d'un axe",
         {"profil": "liste de points", "axe": "vecteur", "angle": "degres"})
def _revolve(self, profil=None, point_axe=(0, 0, 0), axe=(0, 0, 1), angle=360.0,
             segments=48, materiau="default", calque=None, handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    return self.add(modeling.revolve(_profile(profil), point_axe, axe,
                                     math.radians(angle), segments, materiau),
                    "revolution", calque)


@command("BALAYAGE", "solides_profil", "SWEEP", (),
         "Deplace un profil le long d'une trajectoire",
         {"profil": "liste de points", "trajectoire": "liste de points",
          "torsion": "degres", "echelle": "facteur final"})
def _sweep(self, profil=None, trajectoire=None, torsion=0.0, echelle=1.0,
           materiau="default", calque=None, handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    if trajectoire is None:
        raise CommandError("BALAYAGE : trajectoire manquante")
    path = trajectoire if isinstance(trajectoire, Curve) else \
        Curve.polyline(trajectoire)
    return self.add(modeling.sweep(_profile(profil), path, torsion, echelle,
                                   True, materiau), "balayage", calque)


@command("LISSAGE", "solides_profil", "LOFT", (),
         "Relie plusieurs sections par une peau continue",
         {"sections": "liste de contours", "regle": "vrai pour des faces reglees"})
def _loft(self, sections=None, regle=True, ferme=False, materiau="default",
          calque=None, handles=None):
    profiles: List[Profile] = []
    if sections:
        profiles = [_profile(section) for section in sections]
    elif handles:
        profiles = [_profile(entity.geometry) for entity in self.targets(handles)]
    if len(profiles) < 2:
        raise CommandError("LISSAGE : au moins deux sections")
    return self.add(modeling.loft(profiles, regle, ferme, 0, materiau),
                    "lissage", calque)


@command("APPUYERTIRER", "solides_profil", "PRESSPULL", ("APT",),
         "Pousse ou tire une zone fermee", {"profil": "contour",
                                            "distance": "mm, negatif = percer"})
def _presspull(self, profil=None, distance=500.0, materiau="default",
               calque=None, handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    return self.add(modeling.presspull(_profile(profil), distance, materiau),
                    "appuyer_tirer", calque)


@command("EPAISSIR", "solides_profil", "THICKEN", (),
         "Donne une epaisseur a une surface", {"epaisseur": "mm"})
def _thicken(self, epaisseur=100.0, handles=None, calque=None):
    surfaces = self.solids(handles)
    polygons = [p for surface in surfaces for p in surface.polygons]
    return self.add(modeling.thicken(polygons, epaisseur), "epaissi", calque)


@command("SURFPLAN", "surfaces", "PLANESURF", (),
         "Surface pleine sur un contour ferme", {"profil": "contour"})
def _planar(self, profil=None, calque=None, handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    return self.add(modeling.planar_surface(_profile(profil)), "surface",
                    calque)


@command("SURFREGLE", "surfaces", "RULESURF", (),
         "Surface tendue entre deux courbes", {"handles": "deux courbes"})
def _ruled(self, handles=None, calque=None):
    entities = self.targets(handles)
    curves = [e.geometry for e in entities if isinstance(e.geometry, Curve)]
    if len(curves) < 2:
        raise CommandError("SURFREGLE : deux courbes sont necessaires")
    return self.add(modeling.ruled_surface(curves[0], curves[1]), "surface",
                    calque)


# ===========================================================================
# Operations booleennes
# ===========================================================================
@command("UNION", "booleens", "UNION", ("UNI",),
         "Fusionne plusieurs solides", {"handles": "objets a fusionner"})
def _union(self, handles=None, calque=None):
    solids = self.solids(handles)
    result = union_all(solids, "union")
    self.document.remove([e.handle for e in self.targets(handles)])
    return self.add(result, "union", calque)


@command("SOUSTRACTION", "booleens", "SUBTRACT", ("SU",),
         "Retire des solides d'un solide de base",
         {"base": "handle du solide conserve", "outils": "handles retires"})
def _subtract(self, base=None, outils=None, handles=None, calque=None):
    if base is None or not outils:
        chosen = handles or self.document.selection
        if len(chosen) < 2:
            raise CommandError(
                "SOUSTRACTION : indiquez base=<handle> et outils=[handles], "
                "ou selectionnez au moins deux solides")
        base, outils = chosen[0], list(chosen[1:])
    outils = [outils] if isinstance(outils, str) else list(outils)
    result = subtract_all(self.solids([base])[0], self.solids(outils),
                          "soustraction")
    self.document.remove([base] + outils)
    return self.add(result, "soustraction", calque)


@command("INTERSECTION", "booleens", "INTERSECT", ("IN",),
         "Ne garde que la matiere commune", {"handles": "objets a croiser"})
def _intersect(self, handles=None, calque=None):
    solids = self.solids(handles)
    result = intersect_all(solids, "intersection")
    self.document.remove([e.handle for e in self.targets(handles)])
    return self.add(result, "intersection", calque)


@command("INTERFERENCE", "booleens", "INTERFERE", ("INTERF",),
         "Detecte les collisions entre solides", {"handles": "objets testes"},
         modifies=False)
def _interfere(self, handles=None):
    report = interfere(self.solids(handles))
    return {"collisions": report["collisions"],
            "details": [{k: v for k, v in item.items() if k != "solide"}
                        for item in report["details"]]}


# ===========================================================================
# Edition de solides
# ===========================================================================
@command("RACCORDARETE", "edition_solides", "FILLETEDGE", ("RACC",),
         "Arrondit les aretes vives d'un solide",
         {"rayon": "mm", "segments": "facettes de l'arrondi"})
def _fillet(self, rayon=20.0, segments=10, handles=None, toutes=True,
            arete=None):
    entity = self.targets(handles)[0]
    solid = entity.geometry
    if not isinstance(solid, Solid):
        raise CommandError("RACCORDARETE : l'objet n'est pas un solide")
    if arete and not toutes:
        result = solid_edit.fillet_edge(solid, (arete[0], arete[1]), rayon,
                                       segments)
    else:
        result = solid_edit.fillet_all_edges(solid, rayon, segments)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "volume_mm3": round(result.volume, 3),
            "faces": len(result.polygons)}


@command("CHANFREINARETE", "edition_solides", "CHAMFEREDGE", ("CHA",),
         "Coupe les aretes vives a plat", {"distance": "mm"})
def _chamfer(self, distance=20.0, handles=None, toutes=True, arete=None):
    entity = self.targets(handles)[0]
    solid = entity.geometry
    if not isinstance(solid, Solid):
        raise CommandError("CHANFREINARETE : l'objet n'est pas un solide")
    if arete and not toutes:
        result = solid_edit.chamfer_edge(solid, (arete[0], arete[1]), distance)
    else:
        result = solid_edit.chamfer_all_edges(solid, distance)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "volume_mm3": round(result.volume, 3),
            "faces": len(result.polygons)}


@command("GAINE", "edition_solides", "SHELL", (),
         "Evide un solide en laissant une paroi",
         {"epaisseur": "mm", "faces_ouvertes": "indices de faces a retirer"})
def _shell(self, epaisseur=20.0, faces_ouvertes=None, handles=None):
    entity = self.targets(handles)[0]
    faces = faces_ouvertes
    if isinstance(faces, int):
        faces = [faces]
    result = solid_edit.shell(entity.geometry, epaisseur, faces)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "volume_mm3": round(result.volume, 3)}


@command("COUPE", "edition_solides", "SLICE", ("SL",),
         "Tranche un solide par un plan",
         {"point": "point du plan", "normale": "normale du plan",
          "conserver": "positif, negatif ou les_deux"})
def _slice(self, point=(0, 0, 0), normale=(0, 0, 1), conserver="les_deux",
           handles=None, calque=None):
    entity = self.targets(handles)[0]
    plane = Plane.from_point_normal(point, normale)
    pieces = solid_edit.slice_solid(entity.geometry, plane, conserver)
    self.document.remove([entity.handle])
    created = [self.add(piece, piece.name, calque)["handle"]
               for piece in pieces if piece.polygons]
    return {"morceaux": len(created), "handles": created,
            "volumes_mm3": [round(p.volume, 3) for p in pieces]}


@command("SECTION", "edition_solides", "SECTION", (),
         "Contour de l'intersection avec un plan",
         {"point": "point du plan", "normale": "normale"}, modifies=False)
def _section(self, point=(0, 0, 0), normale=(0, 0, 1), handles=None):
    entity = self.targets(handles)[0]
    plane = Plane.from_point_normal(point, normale)
    view = solid_edit.section_plane_view(entity.geometry, plane)
    return {"contours": view["contours"], "aire_mm2": view["aire_mm2"],
            "perimetre_mm": view["perimetre_mm"], "boucles": view["boucles"]}


@command("DEPOUILLE", "edition_solides", "TAPER", (),
         "Incline la matiere d'un cote d'un plan", {"angle": "degres"})
def _taper(self, angle=5.0, point=(0, 0, 0), normale=(0, 0, 1), handles=None):
    entity = self.targets(handles)[0]
    result = solid_edit.taper_faces(entity.geometry,
                                    Plane.from_point_normal(point, normale),
                                    angle)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "volume_mm3": round(result.volume, 3)}


@command("DECALAGE", "edition_solides", "OFFSET", ("DE",),
         "Decale les faces d'un solide", {"distance": "mm, negatif = retrait"})
def _offset(self, distance=10.0, handles=None, calque=None):
    entity = self.targets(handles)[0]
    result = solid_edit.offset_solid(entity.geometry, distance)
    return self.add(result, "decalage", calque)


@command("SEPARER", "edition_solides", "SEPARATE", (),
         "Eclate un solide en volumes disjoints", {})
def _separate(self, handles=None, calque=None):
    entity = self.targets(handles)[0]
    pieces = entity.geometry.separate()
    if len(pieces) <= 1:
        return {"morceaux": 1, "message": "le solide est d'un seul tenant"}
    self.document.remove([entity.handle])
    created = [self.add(piece, piece.name, calque)["handle"] for piece in pieces]
    return {"morceaux": len(created), "handles": created}


@command("EMPREINTE", "edition_solides", "IMPRINT", (),
         "Imprime les aretes d'un solide sur un autre",
         {"base": "handle receveur", "outil": "handle imprime"})
def _imprint(self, base=None, outil=None, handles=None):
    chosen = handles or self.document.selection
    if base is None or outil is None:
        if len(chosen) < 2:
            raise CommandError("EMPREINTE : indiquez base= et outil=")
        base, outil = chosen[0], chosen[1]
    result = solid_edit.imprint(self.solids([base])[0], self.solids([outil])[0])
    self.document.replace(base, result)
    return {"handle": base, "faces": len(result.polygons)}


@command("XARETES", "edition_solides", "XEDGES", (),
         "Extrait le filaire d'un solide", {}, modifies=True)
def _xedges(self, handles=None, calque="ARETES"):
    entity = self.targets(handles)[0]
    curves = solid_edit.extract_edges(entity.geometry)
    created = [self.document.add(curve, layer=calque).handle for curve in curves]
    return {"aretes": len(created), "handles": created[:50]}


@command("VERIFSOLIDE", "edition_solides", "SOLIDCHECK", (),
         "Controle l'etancheite d'un solide", {}, modifies=False)
def _check(self, handles=None):
    entity = self.targets(handles)[0]
    return {"controle": entity.geometry.check()}


@command("PROPMECA", "mesures", "MASSPROP", (),
         "Volume, masse, inertie et centre de gravite",
         {"masse_volumique": "kg/m3"}, modifies=False)
def _massprop(self, masse_volumique=2400.0, handles=None):
    solids = self.solids(handles)
    return {"proprietes": [s.mass_properties(masse_volumique) for s in solids]}


@command("CONVENSOLIDE", "edition_solides", "CONVTOSOLID", (),
         "Ferme une surface pour en faire un solide", {"epaisseur": "mm"})
def _to_solid(self, epaisseur=0.0, handles=None):
    entity = self.targets(handles)[0]
    result = solid_edit.convert_to_solid(entity.geometry, epaisseur)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "volume_mm3": round(result.volume, 3)}


@command("CONVENSURFACE", "edition_solides", "CONVTOSURFACE", (),
         "Transforme un solide en surface", {})
def _to_surface(self, handles=None):
    entity = self.targets(handles)[0]
    result = solid_edit.convert_to_surface(entity.geometry)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "faces": len(result.polygons)}


# ===========================================================================
# Maillages
# ===========================================================================
@command("LISSERMAILLE", "maillages", "MESHSMOOTH", (),
         "Lisse un maillage par subdivision", {"niveaux": "1 a 3"})
def _smooth(self, niveaux=1, handles=None):
    entity = self.targets(handles)[0]
    result = mesh_tools.smooth(entity.geometry, int(niveaux))
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "faces": len(result.polygons)}


@command("AFFINERMAILLE", "maillages", "MESHREFINE", (),
         "Subdivise sans deformer", {"niveaux": "1 a 3"})
def _refine(self, niveaux=1, handles=None):
    entity = self.targets(handles)[0]
    result = mesh_tools.subdivide(entity.geometry, int(niveaux))
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "faces": len(result.polygons)}


@command("TRIANGULER", "maillages", "TRIANGULATE", (),
         "Convertit toutes les faces en triangles", {})
def _triangulate(self, handles=None):
    entity = self.targets(handles)[0]
    result = mesh_tools.triangulate(entity.geometry)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "triangles": len(result.polygons)}


@command("SOUDER", "maillages", "WELD", (),
         "Fusionne les sommets et repare le maillage", {"tolerance": "mm"})
def _weld(self, tolerance=0.1, handles=None):
    entity = self.targets(handles)[0]
    result = mesh_tools.weld(entity.geometry, tolerance)
    self.document.replace(entity.handle, result)
    return {"handle": entity.handle, "controle": result.check()}


# ===========================================================================
# Transformations
# ===========================================================================
@command("DEPLACER3D", "transformations", "3DMOVE", ("DEPLACER", "M"),
         "Deplace la selection", {"vecteur": "dx,dy,dz"})
def _move(self, vecteur=(0, 0, 0), handles=None):
    entities = self.targets(handles)
    matrix = Mat4.translation(vecteur)
    for entity in entities:
        self.document.entities[entity.handle] = entity.transformed(matrix)
        self.document.entities[entity.handle].handle = entity.handle
    return {"objets": len(entities), "vecteur": list(Vec3.of(vecteur))}


@command("ROTATION3D", "transformations", "3DROTATE", ("RO3",),
         "Tourne la selection autour d'un axe",
         {"axe": "vecteur", "angle": "degres", "base": "point de rotation"})
def _rotate(self, axe=(0, 0, 1), angle=90.0, base=(0, 0, 0), handles=None):
    entities = self.targets(handles)
    matrix = Mat4.rotation(axe, math.radians(angle), base)
    for entity in entities:
        clone = entity.transformed(matrix)
        clone.handle = entity.handle
        self.document.entities[entity.handle] = clone
    return {"objets": len(entities), "angle_deg": angle}


@command("ECHELLE", "transformations", "3DSCALE", ("SC",),
         "Met la selection a l'echelle", {"facteur": "nombre", "base": "point"})
def _scale(self, facteur=2.0, base=(0, 0, 0), handles=None):
    entities = self.targets(handles)
    matrix = Mat4.scaling(facteur, base)
    for entity in entities:
        clone = entity.transformed(matrix)
        clone.handle = entity.handle
        self.document.entities[entity.handle] = clone
    return {"objets": len(entities), "facteur": facteur}


@command("MIROIR3D", "transformations", "MIRROR3D", ("MI3",),
         "Symetrie par rapport a un plan",
         {"point": "point du plan", "normale": "normale",
          "conserver_source": "vrai pour garder l'original"})
def _mirror(self, point=(0, 0, 0), normale=(1, 0, 0), conserver_source=True,
            handles=None, calque=None):
    entities = self.targets(handles)
    plane = Plane.from_point_normal(point, normale)
    matrix = Mat4.mirror(plane)
    created: List[str] = []
    for entity in entities:
        clone = entity.transformed(matrix)
        created.append(self.document.add(clone.geometry, layer=calque or
                                         entity.layer).handle)
    if not conserver_source:
        self.document.remove([e.handle for e in entities])
    return {"copies": len(created), "handles": created}


@command("ALIGNER3D", "transformations", "3DALIGN", ("AL",),
         "Aligne la selection sur des points cibles",
         {"source": "points source", "cible": "points cible"})
def _align(self, source=None, cible=None, handles=None):
    if not source or not cible:
        raise CommandError("ALIGNER3D : fournissez source=[...] et cible=[...]")
    entities = self.targets(handles)
    matrix = Mat4.align(source, cible)
    for entity in entities:
        clone = entity.transformed(matrix)
        clone.handle = entity.handle
        self.document.entities[entity.handle] = clone
    return {"objets": len(entities)}


@command("COPIER", "transformations", "COPY", ("CO",),
         "Copie la selection", {"vecteur": "dx,dy,dz", "copies": "nombre"})
def _copy(self, vecteur=(1000, 0, 0), copies=1, handles=None, calque=None):
    entities = self.targets(handles)
    created: List[str] = []
    for index in range(1, int(copies) + 1):
        matrix = Mat4.translation(Vec3.of(vecteur) * index)
        for entity in entities:
            clone = entity.transformed(matrix)
            created.append(self.document.add(clone.geometry,
                                             layer=calque or entity.layer).handle)
    return {"copies": len(created), "handles": created}


@command("RESEAU3D", "transformations", "3DARRAY", ("RESEAU",),
         "Reseau rectangulaire en trois dimensions",
         {"colonnes": "nombre", "rangees": "nombre", "niveaux": "nombre",
          "pas_colonne": "mm", "pas_rangee": "mm", "pas_niveau": "mm"})
def _array_rect(self, colonnes=3, rangees=2, niveaux=1, pas_colonne=1000.0,
                pas_rangee=1000.0, pas_niveau=1000.0, handles=None, calque=None):
    entities = self.targets(handles)
    created: List[str] = []
    for entity in entities:
        copies = transform3d.array_rectangular(
            entity.geometry, int(colonnes), int(rangees), int(niveaux),
            pas_colonne, pas_rangee, pas_niveau)
        for index, geometry in enumerate(copies):
            if index == 0:
                continue
            created.append(self.document.add(geometry,
                                             layer=calque or entity.layer).handle)
    return {"occurrences": len(created) + len(entities), "handles": created}


@command("RESEAUPOLAIRE", "transformations", "ARRAYPOLAR", ("RESP",),
         "Reseau autour d'un axe",
         {"centre": "point", "nombre": "occurrences", "angle": "degres"})
def _array_polar(self, centre=(0, 0, 0), axe=(0, 0, 1), nombre=6, angle=360.0,
                 handles=None, calque=None):
    entities = self.targets(handles)
    created: List[str] = []
    for entity in entities:
        copies = transform3d.array_polar(entity.geometry, centre, axe,
                                         int(nombre), angle)
        for index, geometry in enumerate(copies):
            if index == 0:
                continue
            created.append(self.document.add(geometry,
                                             layer=calque or entity.layer).handle)
    return {"occurrences": len(created) + len(entities), "handles": created}


@command("RESEAUCHEMIN", "transformations", "ARRAYPATH", ("RESC",),
         "Reseau le long d'une trajectoire",
         {"trajectoire": "liste de points", "nombre": "occurrences"})
def _array_path(self, trajectoire=None, nombre=6, aligner=True, handles=None,
                calque=None):
    if not trajectoire:
        raise CommandError("RESEAUCHEMIN : trajectoire manquante")
    path = trajectoire if isinstance(trajectoire, Curve) else \
        Curve.polyline(trajectoire)
    entities = self.targets(handles)
    created: List[str] = []
    for entity in entities:
        copies = transform3d.array_path(entity.geometry, path, int(nombre),
                                        aligner)
        for index, geometry in enumerate(copies):
            if index == 0:
                continue
            created.append(self.document.add(geometry,
                                             layer=calque or entity.layer).handle)
    return {"occurrences": len(created) + len(entities), "handles": created}


@command("EFFACER", "transformations", "ERASE", ("E", "SUPPRIMER"),
         "Efface la selection", {})
def _erase(self, handles=None):
    entities = self.targets(handles)
    removed = self.document.remove([e.handle for e in entities])
    return {"effaces": removed}


# ===========================================================================
# Objets 2D
# ===========================================================================
@command("LIGNE", "dessin_2d", "LINE", ("L",), "Segment de droite",
         {"depart": "x,y,z", "arrivee": "x,y,z"})
def _line(self, depart=(0, 0, 0), arrivee=(1000, 0, 0), calque=None):
    return self.add(Curve.line(depart, arrivee), "ligne", calque)


@command("POLYLIGNE", "dessin_2d", "PLINE", ("PL",), "Polyligne ouverte ou fermee",
         {"points": "liste de points", "ferme": "vrai ou faux"})
def _pline(self, points=None, ferme=False, calque=None):
    if not points:
        raise CommandError("POLYLIGNE : fournissez points=[[x,y,z], ...]")
    return self.add(Curve.polyline(points, ferme), "polyligne", calque)


@command("CERCLE", "dessin_2d", "CIRCLE", ("C",), "Cercle",
         {"centre": "x,y,z", "rayon": "mm"})
def _circle(self, centre=(0, 0, 0), rayon=500.0, segments=64, calque=None):
    return self.add(Curve.circle(centre, rayon, None, segments), "cercle",
                    calque)


@command("ARC", "dessin_2d", "ARC", ("A",), "Arc de cercle",
         {"centre": "x,y,z", "rayon": "mm", "depart": "degres",
          "arrivee": "degres"})
def _arc(self, centre=(0, 0, 0), rayon=500.0, depart=0.0, arrivee=90.0,
         calque=None):
    return self.add(Curve.arc(centre, rayon, math.radians(depart),
                              math.radians(arrivee)), "arc", calque)


@command("RECTANG", "dessin_2d", "RECTANGLE", ("REC",), "Rectangle",
         {"largeur": "mm", "profondeur": "mm", "origine": "x,y,z",
          "raccord": "rayon d'angle en mm"})
def _rect(self, largeur=1000.0, profondeur=600.0, origine=(0, 0, 0),
          raccord=0.0, calque=None):
    profile = (Profile.rounded_rectangle(largeur, profondeur, raccord, origine)
               if raccord > 0 else Profile.rectangle(largeur, profondeur,
                                                     origine))
    return self.add(profile, "rectangle", calque)


@command("POLYGONE", "dessin_2d", "POLYGON", ("POL",), "Polygone regulier",
         {"cotes": "3 a 1024", "rayon": "mm", "inscrit": "vrai ou faux"})
def _polygon(self, cotes=6, rayon=500.0, centre=(0, 0, 0), inscrit=True,
             calque=None):
    return self.add(Profile.regular_polygon(int(cotes), rayon, centre, None,
                                            inscrit), "polygone", calque)


@command("ELLIPSE", "dessin_2d", "ELLIPSE", ("EL",), "Ellipse",
         {"rayon_x": "mm", "rayon_y": "mm"})
def _ellipse(self, rayon_x=800.0, rayon_y=400.0, centre=(0, 0, 0), calque=None):
    return self.add(Profile.ellipse(rayon_x, rayon_y, centre), "ellipse",
                    calque)


@command("SPLINE", "dessin_2d", "SPLINE", ("SPL",), "Courbe passant par des points",
         {"points": "liste de points"})
def _spline(self, points=None, ferme=False, calque=None):
    if not points:
        raise CommandError("SPLINE : fournissez points=[[x,y,z], ...]")
    return self.add(Curve.spline(points, 12, ferme), "spline", calque)


@command("POINT", "dessin_2d", "POINT", ("PO",), "Point isole",
         {"position": "x,y,z"})
def _point(self, position=(0, 0, 0), calque=None):
    return self.add(Curve([Vec3.of(position)], False, "point"), "point", calque)


# ===========================================================================
# Annotation
# ===========================================================================
@command("COTLIN", "annotation", "DIMLINEAR", ("COTL",),
         "Cote lineaire", {"depart": "point", "arrivee": "point",
                           "decalage": "mm"})
def _dimlinear(self, depart=(0, 0, 0), arrivee=(1000, 0, 0), decalage=200.0,
               calque="COTATION"):
    dimension = annotate.linear_dimension(depart, arrivee, decalage,
                                          layer=calque)
    self.annotations.append(dimension)
    self.document.add(dimension, kind="annotation", layer=calque)
    return {"texte": dimension["texte"], "mesure_mm": dimension["mesure_mm"]}


@command("COTALI", "annotation", "DIMALIGNED", (),
         "Cote alignee sur le segment", {"depart": "point", "arrivee": "point"})
def _dimaligned(self, depart=(0, 0, 0), arrivee=(1000, 500, 0), decalage=200.0,
                calque="COTATION"):
    dimension = annotate.aligned_dimension(depart, arrivee, decalage,
                                           layer=calque)
    self.annotations.append(dimension)
    self.document.add(dimension, kind="annotation", layer=calque)
    return {"texte": dimension["texte"], "mesure_mm": dimension["mesure_mm"]}


@command("COTANG", "annotation", "DIMANGULAR", (),
         "Cote angulaire", {"sommet": "point", "premier": "point",
                            "second": "point"})
def _dimangular(self, sommet=(0, 0, 0), premier=(1000, 0, 0),
                second=(0, 1000, 0), rayon=300.0, calque="COTATION"):
    dimension = annotate.angular_dimension(sommet, premier, second, rayon,
                                           layer=calque)
    self.annotations.append(dimension)
    self.document.add(dimension, kind="annotation", layer=calque)
    return {"texte": dimension["texte"], "mesure_deg": dimension["mesure_deg"]}


@command("COTRAYON", "annotation", "DIMRADIUS", (),
         "Cote de rayon", {"centre": "point", "rayon": "mm"})
def _dimradius(self, centre=(0, 0, 0), rayon=500.0, diametre=False,
               calque="COTATION"):
    dimension = annotate.radial_dimension(centre, rayon, 45.0, diametre,
                                          layer=calque)
    self.annotations.append(dimension)
    self.document.add(dimension, kind="annotation", layer=calque)
    return {"texte": dimension["texte"], "mesure_mm": dimension["mesure_mm"]}


@command("COTDIA", "annotation", "DIMDIAMETER", (),
         "Cote de diametre", {"centre": "point", "rayon": "mm"})
def _dimdiameter(self, centre=(0, 0, 0), rayon=500.0, calque="COTATION"):
    return _dimradius(self, centre, rayon, True, calque)


@command("TEXTMULT", "annotation", "MTEXT", ("T", "TEXTE"),
         "Texte multiligne", {"position": "point", "texte": "contenu",
                              "hauteur": "mm"})
def _mtext(self, position=(0, 0, 0), texte="", hauteur=25.0,
           calque="ANNOTATION"):
    annotation = annotate.mtext(position, str(texte), hauteur, layer=calque)
    self.annotations.append(annotation)
    self.document.add(annotation, kind="annotation", layer=calque)
    return {"texte": annotation["texte"], "lignes": len(annotation["lignes"])}


@command("LIGNEDEREPERE", "annotation", "MLEADER", ("REPERE",),
         "Fleche de renvoi avec texte", {"points": "liste", "texte": "contenu"})
def _leader(self, points=None, texte="", calque="ANNOTATION"):
    if not points:
        raise CommandError("LIGNEDEREPERE : fournissez points=[...]")
    annotation = annotate.leader(points, str(texte), layer=calque)
    self.annotations.append(annotation)
    self.document.add(annotation, kind="annotation", layer=calque)
    return {"texte": annotation["texte"]}


@command("HACHURES", "annotation", "HATCH", ("H",),
         "Remplit un contour ferme", {"profil": "contour", "motif": "nom",
                                      "echelle": "facteur"})
def _hatch(self, profil=None, motif="ANSI31", echelle=1.0, angle=0.0,
           calque="HACHURES", handles=None):
    if profil is None and handles:
        profil = _profile(self.targets(handles)[0].geometry)
    annotation = annotate.hatch(_profile(profil), motif, echelle, angle, calque)
    self.annotations.append(annotation)
    self.document.add(annotation, kind="annotation", layer=calque)
    return {"motif": motif, "aire_mm2": annotation["aire_mm2"],
            "segments": len(annotation["lignes"])}


@command("TABLEAU", "annotation", "TABLE", (),
         "Nomenclature ou legende", {"lignes": "liste de listes",
                                     "titre": "texte"})
def _table(self, lignes=None, position=(0, 0, 0), titre="", calque="ANNOTATION"):
    if not lignes:
        raise CommandError("TABLEAU : fournissez lignes=[[...], [...]]")
    annotation = annotate.table(position, lignes, None, 60.0, titre, calque)
    self.annotations.append(annotation)
    self.document.add(annotation, kind="annotation", layer=calque)
    return {"lignes": len(annotation["lignes"]),
            "colonnes": annotation["colonnes"]}


@command("NUAGEREV", "annotation", "REVCLOUD", (),
         "Nuage de revision", {"points": "contour"})
def _revcloud(self, points=None, longueur_arc=150.0, calque="REVISION"):
    if not points:
        raise CommandError("NUAGEREV : fournissez points=[...]")
    annotation = annotate.revision_cloud(points, longueur_arc, calque)
    self.annotations.append(annotation)
    self.document.add(annotation, kind="annotation", layer=calque)
    return {"sommets": len(annotation["points"])}


# ===========================================================================
# Organisation du dessin
# ===========================================================================
@command("CALQUE", "organisation", "LAYER", ("LA",),
         "Cree ou active un calque",
         {"nom": "nom du calque", "couleur": "indice ACI", "courant": "vrai"})
def _layer(self, nom="0", couleur=7, type_ligne="CONTINUOUS", epaisseur=25,
           courant=True, description=""):
    layer = self.document.add_layer(str(nom), int(couleur), type_ligne,
                                    int(epaisseur), description)
    if courant:
        self.document.set_current_layer(str(nom))
    return {"calque": layer.to_dict(), "courant": self.document.current_layer}


@command("BLOC", "organisation", "BLOCK", ("B_",),
         "Enregistre une selection comme bloc", {"nom": "nom du bloc"})
def _block(self, nom="BLOC", point_base=(0, 0, 0), handles=None):
    entities = self.targets(handles)
    block = self.document.define_block(str(nom), [e.handle for e in entities],
                                       point_base)
    return {"bloc": block.to_dict()}


@command("INSERER", "organisation", "INSERT", ("I",),
         "Insere une occurrence de bloc",
         {"nom": "nom du bloc", "position": "point", "echelle": "facteur"})
def _insert(self, nom="BLOC", position=(0, 0, 0), echelle=1.0, rotation=0.0,
            calque=None):
    placed = self.document.insert_block(str(nom), position, echelle, rotation,
                                        calque)
    return {"objets": len(placed), "handles": [e.handle for e in placed]}


@command("DECOMPOSER", "organisation", "EXPLODE", ("X",),
         "Detache les objets de leur bloc", {})
def _explode(self, handles=None):
    entities = self.targets(handles)
    return {"decomposes": self.document.explode_block(
        [e.handle for e in entities])}


@command("SCU", "organisation", "UCS", (),
         "Definit le systeme de coordonnees utilisateur",
         {"nom": "nom", "origine": "point", "axe_x": "vecteur"})
def _ucs(self, nom="UTILISATEUR", origine=(0, 0, 0), axe_x=(1, 0, 0),
         axe_y=(0, 1, 0)):
    return {"scu": self.document.set_ucs(str(nom), origine, axe_x,
                                         axe_y).to_dict()}


@command("PRESENTATION", "organisation", "LAYOUT", (),
         "Ajoute un espace papier", {"nom": "nom", "format": "A4 a A0",
                                     "echelle": "1/100 = 0.01"})
def _layout(self, nom="Presentation", format="A3", echelle=0.01):
    return {"presentation": self.document.add_layout(str(nom), str(format),
                                                     float(echelle)).to_dict()}


@command("SELECTIONNER", "organisation", "SELECT", ("SEL",),
         "Selectionne des objets",
         {"handles": "liste", "tout": "vrai", "calque": "nom",
          "fenetre": "deux points"}, modifies=False)
def _select(self, handles=None, tout=False, calque=None, fenetre=None,
            capture=False):
    if tout:
        chosen = self.document.select_all()
    elif calque:
        chosen = self.document.select_by_layer(str(calque))
    elif fenetre and len(fenetre) >= 2:
        chosen = self.document.select_window(fenetre[0], fenetre[1], capture)
    elif handles:
        chosen = self.document.select(handles)
    else:
        chosen = self.document.selection
    return {"selection": chosen, "objets": len(chosen)}


@command("ANNULER", "organisation", "UNDO", ("U",), "Annule la derniere action",
         {}, modifies=False)
def _undo(self):
    return {"annule": self.document.undo(),
            "profondeur": self.document.undo_depth}


@command("RETABLIR", "organisation", "REDO", (), "Retablit l'action annulee",
         {}, modifies=False)
def _redo(self):
    return {"retabli": self.document.redo()}


@command("ETAT", "organisation", "STATUS", (), "Fiche du document", {},
         modifies=False)
def _status(self):
    return {"etat": self.document.statistics()}


@command("LISTE", "organisation", "LIST", ("LI",),
         "Detail des objets selectionnes", {}, modifies=False)
def _list(self, handles=None):
    return {"objets": [e.to_dict() for e in self.targets(handles)]}


@command("PURGER", "organisation", "PURGE", (),
         "Supprime les calques et blocs inutilises", {})
def _purge(self):
    used = {entity.layer for entity in self.document.entities.values()}
    removed: List[str] = []
    for name in list(self.document.layers):
        if name != "0" and name not in used:
            self.document.delete_layer(name)
            removed.append(name)
    return {"calques_supprimes": removed}


# ===========================================================================
# Accrochages et aides au dessin
# ===========================================================================
@command("ACCROBJ", "aides", "OSNAP", ("OS",),
         "Regle les accrochages aux objets", {"modes": "valeur OSMODE"},
         modifies=False)
def _osnap(self, modes=None, ouverture=None):
    if modes is not None:
        self.snap.modes = int(modes)
        self.document.variables["OSMODE"] = int(modes)
    if ouverture is not None:
        self.snap.aperture = float(ouverture)
    return {"accrochages": self.snap.to_dict()}


@command("ACCROCHER", "aides", "SNAPPOINT", (),
         "Renvoie le point accroche le plus proche du curseur",
         {"curseur": "x,y,z"}, modifies=False)
def _snap_point(self, curseur=(0, 0, 0), dernier=None, handles=None):
    entities = (self.targets(handles) if handles
                else self.document.visible_entities())
    result = self.snap.snap(curseur, entities, dernier)
    return {"accrochage": result.to_dict() if result else None}


@command("ORTHO", "aides", "ORTHO", (), "Active ou desactive le mode ortho",
         {"actif": "vrai ou faux"}, modifies=False)
def _ortho(self, actif=True):
    self.snap.ortho = bool(actif)
    self.document.variables["ORTHOMODE"] = 1 if actif else 0
    return {"ortho": self.snap.ortho}


@command("RESOL", "aides", "SNAP", (), "Accrochage a la grille",
         {"actif": "vrai ou faux", "pas": "mm"}, modifies=False)
def _grid_snap(self, actif=True, pas=None):
    self.snap.grid_snap = bool(actif)
    if pas:
        self.snap.grid_spacing = float(pas)
    self.document.variables["SNAPMODE"] = 1 if actif else 0
    return {"resol": self.snap.grid_snap, "pas_mm": self.snap.grid_spacing}


@command("MESURER", "mesures", "MEASUREGEOM", ("MES",),
         "Distance, aire, volume, angle",
         {"type": "distance, aire, volume ou angle"}, modifies=False)
def _measure(self, type="distance", points=None, handles=None):
    kind = str(type).lower()
    if kind == "distance":
        if not points or len(points) < 2:
            raise CommandError("MESURER distance : deux points sont requis")
        a, b = Vec3.of(points[0]), Vec3.of(points[1])
        delta = b - a
        return {"distance_mm": round(a.distance_to(b), 4),
                "delta": [round(v, 4) for v in delta],
                "angle_xy_deg": round(math.degrees(math.atan2(delta.y, delta.x)),
                                      4)}
    if kind == "angle":
        if not points or len(points) < 3:
            raise CommandError("MESURER angle : trois points sont requis")
        a, b, c = (Vec3.of(p) for p in points[:3])
        return {"angle_deg": round(math.degrees((a - b).angle_to(c - b)), 4)}
    solids = self.solids(handles)
    if kind == "volume":
        return {"volume_mm3": round(sum(s.volume for s in solids), 3),
                "volume_m3": round(sum(s.volume for s in solids) * 1e-9, 6)}
    if kind == "aire":
        return {"aire_mm2": round(sum(s.area for s in solids), 3),
                "aire_m2": round(sum(s.area for s in solids) * 1e-6, 4)}
    raise CommandError("MESURER : type inconnu %r (distance, angle, aire, "
                       "volume)" % type)


# ===========================================================================
# Vues et rendu
# ===========================================================================
@command("VUEPOINT", "vues", "VPOINT", ("VP",),
         "Vue normalisee : dessus, face, isometrique...",
         {"vue": ", ".join(sorted(STANDARD_VIEWS))}, modifies=False)
def _vpoint(self, vue="iso_sud_ouest"):
    camera = self.viewport.camera
    camera.set_standard_view(str(vue))
    camera.zoom_extents(self.document.bbox)
    return {"camera": camera.to_dict()}


@command("ORBITE3D", "vues", "3DORBIT", ("ORB",), "Fait tourner la vue",
         {"azimut": "degres", "elevation": "degres"}, modifies=False)
def _orbit(self, azimut=15.0, elevation=0.0):
    camera = self.viewport.camera.orbit(float(azimut), float(elevation))
    return {"camera": camera.to_dict()}


@command("ZOOM", "vues", "ZOOM", ("Z",), "Zoom avant, arriere ou etendu",
         {"facteur": "nombre", "etendu": "vrai"}, modifies=False)
def _zoom(self, facteur=None, etendu=False):
    camera = self.viewport.camera
    if etendu or facteur is None:
        camera.zoom_extents(self.document.bbox)
    else:
        camera.dolly(float(facteur))
    return {"camera": camera.to_dict()}


@command("PAN", "vues", "PAN", ("P",), "Deplace la vue",
         {"dx": "mm", "dy": "mm"}, modifies=False)
def _pan(self, dx=0.0, dy=0.0):
    return {"camera": self.viewport.camera.pan(float(dx), float(dy)).to_dict()}


@command("STYLESVISUELS", "vues", "VSCURRENT", ("SV",),
         "Change le style visuel",
         {"style": ", ".join(sorted(VISUAL_STYLES))}, modifies=False)
def _style(self, style="ombre_avec_aretes"):
    self.viewport.set_style(str(style))
    return {"fenetre": self.viewport.to_dict()}


@command("RENDU", "vues", "RENDER", ("RR",),
         "Calcule une image du modele",
         {"largeur": "pixels", "hauteur": "pixels", "style": "style visuel"},
         modifies=False)
def _render(self, largeur=1280, hauteur=800, style=None, vue=None):
    camera = self.viewport.camera
    camera.width, camera.height = int(largeur), int(hauteur)
    if vue:
        camera.set_standard_view(str(vue))
    camera.zoom_extents(self.document.bbox)
    frame = self.renderer.render(self.document.solids(), camera,
                                 str(style or self.viewport.visual_style))
    return {"image_png_octets": len(frame.to_png()), "largeur": frame.width,
            "hauteur": frame.height, "style": style or self.viewport.visual_style}


@command("MASQUE", "vues", "HIDE", (),
         "Filaire sans les aretes cachees, en vectoriel", {}, modifies=False)
def _hide(self, largeur=1400, hauteur=900):
    camera = self.viewport.camera
    camera.width, camera.height = int(largeur), int(hauteur)
    camera.zoom_extents(self.document.bbox)
    svg = self.renderer.hidden_line_svg(self.document.solids(), camera)
    return {"svg_octets": len(svg), "polylignes": svg.count("polyline")}


@command("VUE", "vues", "VIEW", ("V",), "Enregistre une vue nommee",
         {"nom": "nom de la vue"}, modifies=False)
def _view(self, nom="Vue1"):
    return {"vue": self.document.save_view(str(nom),
                                           self.viewport.camera.to_dict())}


@command("PLANDECOUPE", "vues", "SECTIONPLANE", (),
         "Ajoute un plan de coupe a la vue",
         {"point": "point", "normale": "vecteur"}, modifies=False)
def _clip(self, point=(0, 0, 0), normale=(0, 0, 1)):
    self.viewport.camera.add_clip_plane(Plane.from_point_normal(point, normale))
    return {"plans_de_coupe": len(self.viewport.camera.clip_planes)}


# ===========================================================================
# Fichiers
# ===========================================================================
@command("EXPORTER", "fichiers", "EXPORT", ("EXP",),
         "Exporte le document dans un format d'echange",
         {"format": "dxf, ifc, step, stl, obj, gltf, pdf, png..."},
         modifies=False)
def _export(self, format="dxf", **options):
    import Interop
    payload = Interop.export_data(self.document, str(format), self.annotations,
                                  **options)
    return {"format": str(format), "octets": len(payload),
            "texte": isinstance(payload, str)}


@command("IMPORTER", "fichiers", "IMPORT", ("IMP",),
         "Importe un fichier et le fusionne au document",
         {"chemin": "chemin du fichier"})
def _import(self, chemin=None, prefixe=""):
    import Interop
    if not chemin:
        raise CommandError("IMPORTER : indiquez chemin=<fichier>")
    imported = Interop.import_file(str(chemin))
    added = self.document.merge(imported["document"], str(prefixe))
    return {"format": imported["format"], "objets_ajoutes": added}


@command("FORMATS", "fichiers", "FILEFORMATS", (),
         "Liste les formats lus et ecrits", {}, modifies=False)
def _formats(self):
    import Interop
    return {"capacites": Interop.capabilities()}


@command("AIDE", "general", "HELP", ("?",),
         "Aide sur une commande ou catalogue complet",
         {"commande": "nom de commande"}, modifies=False)
def _help(self, commande=None, groupe=None):
    if commande:
        return {"aide": CommandInterpreter.resolve(str(commande)).to_dict()}
    return {"groupes": {name: count for name, count
                        in sorted(_groups().items())},
            "commandes": [entry.to_dict() for entry in REGISTRY.values()
                          if not groupe or entry.group == groupe]}


def _groups() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for entry in REGISTRY.values():
        counts[entry.group] = counts.get(entry.group, 0) + 1
    return counts


def catalog() -> List[Dict[str, Any]]:
    """Catalogue complet, utilise par l'API et par le ruban de l'interface."""
    return [entry.to_dict() for entry in REGISTRY.values()]


def groups() -> Dict[str, int]:
    return _groups()
