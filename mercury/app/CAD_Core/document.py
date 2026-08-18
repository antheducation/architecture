"""Document CAO : calques, blocs, objets, SCU, vues, presentations, annuler.

C'est la structure que manipulent l'interface, l'interpreteur de commandes
et les modules d'import-export. Elle reprend l'organisation d'un fichier
DWG : un espace objet, des presentations, une table de calques, une table
de blocs, des styles, et un historique d'annulation.
"""
from __future__ import annotations

import copy
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .math3d import BBox3, Mat4, ORIGIN, Plane, Vec3, X_AXIS, Y_AXIS, Z_AXIS
from .profiles import Curve, Profile
from .solid import Solid

# Couleurs de l'index AutoCAD (ACI) les plus utilisees.
ACI_COLORS: Dict[int, Tuple[int, int, int]] = {
    0: (0, 0, 0), 1: (255, 0, 0), 2: (255, 255, 0), 3: (0, 255, 0),
    4: (0, 255, 255), 5: (0, 0, 255), 6: (255, 0, 255), 7: (255, 255, 255),
    8: (128, 128, 128), 9: (192, 192, 192), 30: (255, 127, 0),
    40: (255, 191, 0), 140: (0, 127, 255), 250: (51, 51, 51),
    251: (91, 91, 91), 252: (132, 132, 132), 253: (173, 173, 173),
    254: (214, 214, 214), 255: (255, 255, 255), 256: (255, 255, 255),
}

LINETYPES = ["CONTINUOUS", "CENTER", "DASHED", "DASHDOT", "HIDDEN", "PHANTOM",
             "DOT", "BORDER", "DIVIDE"]

LINEWEIGHTS = [0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80,
               90, 100, 106, 120, 140, 158, 200, 211]

UNITS = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "ft": 304.8}


@dataclass
class Layer:
    """Calque : couleur, type de ligne, epaisseur, etats."""

    name: str
    color: int = 7
    linetype: str = "CONTINUOUS"
    lineweight: int = 25
    on: bool = True
    frozen: bool = False
    locked: bool = False
    plot: bool = True
    transparency: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "couleur": self.color,
                "type_ligne": self.linetype, "epaisseur": self.lineweight,
                "actif": self.on, "gele": self.frozen, "verrouille": self.locked,
                "traceable": self.plot, "transparence": self.transparency,
                "description": self.description,
                "rvb": list(ACI_COLORS.get(self.color, (255, 255, 255)))}


@dataclass
class Entity:
    """Objet du dessin : geometrie plus proprietes graphiques."""

    handle: str
    kind: str                              # solide, courbe, profil, annotation
    geometry: Any
    layer: str = "0"
    color: int = 256                       # 256 = DUCALQUE
    linetype: str = "PARCALQUE"
    lineweight: int = -1                   # -1 = PARCALQUE
    material: str = "default"
    visible: bool = True
    locked: bool = False
    transparency: int = 0
    name: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    created: float = field(default_factory=lambda: 0.0)

    @property
    def bbox(self) -> BBox3:
        geometry = self.geometry
        if isinstance(geometry, Solid):
            return geometry.bbox
        if isinstance(geometry, Curve):
            return BBox3.of(geometry.points)
        if isinstance(geometry, Profile):
            return BBox3.of(p for ring in geometry.rings() for p in ring)
        if isinstance(geometry, dict) and "points" in geometry:
            return BBox3.of(Vec3.of(p) for p in geometry["points"])
        return BBox3()

    def transformed(self, matrix: Mat4) -> "Entity":
        clone = copy.deepcopy(self)
        geometry = self.geometry
        if isinstance(geometry, (Solid, Curve, Profile)):
            clone.geometry = geometry.transformed(matrix)
        elif isinstance(geometry, dict) and "points" in geometry:
            clone.geometry = dict(geometry)
            clone.geometry["points"] = [list(matrix.apply(p))
                                        for p in geometry["points"]]
        return clone

    def to_dict(self) -> Dict[str, Any]:
        base = {"handle": self.handle, "type": self.kind, "nom": self.name,
                "calque": self.layer, "couleur": self.color,
                "type_ligne": self.linetype, "epaisseur": self.lineweight,
                "materiau": self.material, "visible": self.visible,
                "verrouille": self.locked, "transparence": self.transparency,
                "boite": self.bbox.to_dict()}
        geometry = self.geometry
        if isinstance(geometry, Solid):
            base["geometrie"] = geometry.to_dict()
        elif isinstance(geometry, (Curve, Profile)):
            base["geometrie"] = geometry.to_dict()
        elif isinstance(geometry, dict):
            base["geometrie"] = {k: v for k, v in geometry.items()
                                 if k != "points"}
            base["geometrie"]["points"] = len(geometry.get("points", ()))
        return base


@dataclass
class Block:
    """Bloc : geometrie reutilisable inseree par references."""

    name: str
    entities: List[Entity] = field(default_factory=list)
    base_point: Vec3 = ORIGIN
    description: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "objets": len(self.entities),
                "point_base": list(self.base_point),
                "description": self.description,
                "attributs": dict(self.attributes)}


@dataclass
class UCS:
    """Systeme de coordonnees utilisateur."""

    name: str = "GENERAL"
    origin: Vec3 = ORIGIN
    x_axis: Vec3 = X_AXIS
    y_axis: Vec3 = Y_AXIS

    @property
    def z_axis(self) -> Vec3:
        return self.x_axis.cross(self.y_axis).unit()

    @property
    def matrix(self) -> Mat4:
        return Mat4.frame(self.origin, self.x_axis, self.y_axis, self.z_axis)

    def to_world(self, point) -> Vec3:
        return self.matrix.apply(point)

    def to_local(self, point) -> Vec3:
        return self.matrix.inverse().apply(point)

    @property
    def plane(self) -> Plane:
        return Plane.from_point_normal(self.origin, self.z_axis)

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "origine": list(self.origin),
                "axe_x": list(self.x_axis), "axe_y": list(self.y_axis),
                "axe_z": list(self.z_axis)}


@dataclass
class Layout:
    """Presentation : espace papier, cartouche, fenetres et echelle."""

    name: str = "Presentation1"
    paper_size: str = "A3"
    width_mm: float = 420.0
    height_mm: float = 297.0
    scale: float = 0.01                    # 1:100
    viewports: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "format": self.paper_size,
                "largeur_mm": self.width_mm, "hauteur_mm": self.height_mm,
                "echelle": self.scale, "fenetres": len(self.viewports)}


PAPER_SIZES = {"A4": (297.0, 210.0), "A3": (420.0, 297.0), "A2": (594.0, 420.0),
               "A1": (841.0, 594.0), "A0": (1189.0, 841.0),
               "LETTER": (279.4, 215.9), "TABLOID": (431.8, 279.4)}


class CadDocument:
    """Document CAO complet : l'equivalent d'un fichier DWG en memoire."""

    MAX_UNDO = 50

    def __init__(self, name: str = "SansTitre", units: str = "mm") -> None:
        if units not in UNITS:
            raise ValueError("unite inconnue : %s" % units)
        self.name = name
        self.units = units
        self.entities: Dict[str, Entity] = {}
        self.layers: Dict[str, Layer] = {"0": Layer("0")}
        self.blocks: Dict[str, Block] = {}
        self.ucs_table: Dict[str, UCS] = {"GENERAL": UCS()}
        self.named_views: Dict[str, Dict[str, Any]] = {}
        self.layouts: Dict[str, Layout] = {"Presentation1": Layout()}
        self.text_styles: Dict[str, Dict[str, Any]] = {
            "Standard": {"police": "arial.ttf", "hauteur": 2.5, "largeur": 1.0,
                         "oblique": 0.0}}
        self.dim_styles: Dict[str, Dict[str, Any]] = {
            "ISO-25": {"hauteur_texte": 2.5, "fleche": 2.5, "decimales": 2,
                       "unite": "mm", "facteur_echelle": 1.0}}
        self.materials: Dict[str, Dict[str, Any]] = {}
        self.current_layer = "0"
        self.current_ucs = "GENERAL"
        self.variables: Dict[str, Any] = {
            "OSMODE": 4133, "ORTHOMODE": 0, "SNAPMODE": 0, "GRIDMODE": 1,
            "LUNITS": 2, "AUPREC": 0, "INSUNITS": 4, "DIMSCALE": 1.0,
        }
        self._counter = 0
        self._undo: List[bytes] = []
        self._redo: List[bytes] = []
        self.selection: List[str] = []
        self.created = time.time()

    # -- identifiants ------------------------------------------------------
    def new_handle(self) -> str:
        self._counter += 1
        return "%X" % (0x100 + self._counter)

    # -- calques -----------------------------------------------------------
    def add_layer(self, name: str, color: int = 7,
                  linetype: str = "CONTINUOUS", lineweight: int = 25,
                  description: str = "") -> Layer:
        """Commande CALQUE : cree ou met a jour un calque."""
        if linetype not in LINETYPES:
            raise ValueError("type de ligne inconnu : %s" % linetype)
        layer = Layer(name, color, linetype, lineweight,
                      description=description)
        self.layers[name] = layer
        return layer

    def set_current_layer(self, name: str) -> Layer:
        if name not in self.layers:
            self.add_layer(name)
        self.current_layer = name
        return self.layers[name]

    def delete_layer(self, name: str) -> bool:
        """Un calque portant des objets ou le calque 0 ne peut etre supprime."""
        if name == "0" or name not in self.layers:
            return False
        if any(entity.layer == name for entity in self.entities.values()):
            raise ValueError("le calque %s contient des objets" % name)
        del self.layers[name]
        if self.current_layer == name:
            self.current_layer = "0"
        return True

    def layer_entities(self, name: str) -> List[Entity]:
        return [e for e in self.entities.values() if e.layer == name]

    # -- objets ------------------------------------------------------------
    def add(self, geometry, kind: Optional[str] = None,
            layer: Optional[str] = None, name: str = "", **properties) -> Entity:
        """Ajoute un objet et renvoie sa fiche."""
        if kind is None:
            kind = ("solide" if isinstance(geometry, Solid)
                    else "courbe" if isinstance(geometry, Curve)
                    else "profil" if isinstance(geometry, Profile)
                    else "annotation")
        layer = layer or self.current_layer
        if layer not in self.layers:
            self.add_layer(layer)
        entity = Entity(self.new_handle(), kind, geometry, layer,
                        name=name or getattr(geometry, "name", "") or kind,
                        created=time.time(), **properties)
        self.entities[entity.handle] = entity
        return entity

    def get(self, handle: str) -> Entity:
        if handle not in self.entities:
            raise KeyError("objet inconnu : %s" % handle)
        return self.entities[handle]

    def remove(self, handles: Union[str, Sequence[str]]) -> int:
        """Commande EFFACER."""
        targets = [handles] if isinstance(handles, str) else list(handles)
        removed = 0
        for handle in targets:
            entity = self.entities.get(handle)
            if entity is None:
                continue
            if entity.locked or self.layers[entity.layer].locked:
                raise ValueError("objet %s verrouille" % handle)
            del self.entities[handle]
            removed += 1
        self.selection = [h for h in self.selection if h in self.entities]
        return removed

    def replace(self, handle: str, geometry) -> Entity:
        entity = self.get(handle)
        entity.geometry = geometry
        return entity

    def solids(self) -> List[Solid]:
        return [e.geometry for e in self.visible_entities()
                if isinstance(e.geometry, Solid)]

    def visible_entities(self) -> List[Entity]:
        out: List[Entity] = []
        for entity in self.entities.values():
            layer = self.layers.get(entity.layer)
            if not entity.visible or layer is None or not layer.on or layer.frozen:
                continue
            out.append(entity)
        return out

    # -- selection ---------------------------------------------------------
    def select_all(self) -> List[str]:
        self.selection = [e.handle for e in self.visible_entities()]
        return self.selection

    def select(self, handles: Sequence[str], add: bool = False) -> List[str]:
        chosen = [h for h in handles if h in self.entities]
        self.selection = (self.selection + chosen) if add else chosen
        self.selection = list(dict.fromkeys(self.selection))
        return self.selection

    def select_window(self, corner_a, corner_b, crossing: bool = False
                      ) -> List[str]:
        """Selection par fenetre (englobante) ou par capture (secante)."""
        box = BBox3().add(corner_a).add(corner_b)
        chosen: List[str] = []
        for entity in self.visible_entities():
            entity_box = entity.bbox
            if not entity_box.valid:
                continue
            if crossing:
                if box.intersects(entity_box):
                    chosen.append(entity.handle)
            elif box.contains(entity_box.min) and box.contains(entity_box.max):
                chosen.append(entity.handle)
        self.selection = chosen
        return chosen

    def select_by_layer(self, layer: str) -> List[str]:
        self.selection = [e.handle for e in self.layer_entities(layer)]
        return self.selection

    def selected_entities(self) -> List[Entity]:
        return [self.entities[h] for h in self.selection if h in self.entities]

    # -- blocs -------------------------------------------------------------
    def define_block(self, name: str, handles: Sequence[str], base_point=ORIGIN,
                     description: str = "") -> Block:
        """Commande BLOC : transforme une selection en definition reutilisable."""
        members = [copy.deepcopy(self.entities[h]) for h in handles
                   if h in self.entities]
        if not members:
            raise ValueError("BLOC : aucune geometrie a enregistrer")
        block = Block(name, members, Vec3.of(base_point), description)
        self.blocks[name] = block
        return block

    def insert_block(self, name: str, position=ORIGIN, scale: float = 1.0,
                     rotation_deg: float = 0.0,
                     layer: Optional[str] = None) -> List[Entity]:
        """Commande INSERER : place une occurrence de bloc."""
        if name not in self.blocks:
            raise ValueError("bloc inconnu : %s" % name)
        block = self.blocks[name]
        matrix = (Mat4.translation(Vec3.of(position) - block.base_point)
                  * Mat4.rotation(Z_AXIS, math.radians(rotation_deg),
                                  block.base_point)
                  * Mat4.scaling(scale, block.base_point))
        placed: List[Entity] = []
        for member in block.entities:
            clone = member.transformed(matrix)
            clone.handle = self.new_handle()
            clone.layer = layer or member.layer or self.current_layer
            if clone.layer not in self.layers:
                self.add_layer(clone.layer)
            clone.attributes = dict(member.attributes)
            clone.attributes["bloc"] = name
            self.entities[clone.handle] = clone
            placed.append(clone)
        return placed

    def explode_block(self, handles: Sequence[str]) -> int:
        """Commande DECOMPOSER : detache les objets de leur bloc d'origine."""
        count = 0
        for handle in handles:
            entity = self.entities.get(handle)
            if entity is not None and "bloc" in entity.attributes:
                entity.attributes.pop("bloc")
                count += 1
        return count

    # -- SCU et vues -------------------------------------------------------
    def set_ucs(self, name: str, origin=ORIGIN, x_axis=X_AXIS,
                y_axis=Y_AXIS) -> UCS:
        """Commande SCU."""
        ucs = UCS(name, Vec3.of(origin), Vec3.of(x_axis).unit(),
                  Vec3.of(y_axis).unit())
        self.ucs_table[name] = ucs
        self.current_ucs = name
        return ucs

    @property
    def ucs(self) -> UCS:
        return self.ucs_table[self.current_ucs]

    def save_view(self, name: str, camera: Dict[str, Any]) -> Dict[str, Any]:
        """Commande VUE : enregistre une vue nommee."""
        self.named_views[name] = dict(camera)
        return self.named_views[name]

    def add_layout(self, name: str, paper: str = "A3",
                   scale: float = 0.01) -> Layout:
        """Commande PRESENTATION : ajoute un espace papier."""
        if paper not in PAPER_SIZES:
            raise ValueError("format papier inconnu : %s" % paper)
        width, height = PAPER_SIZES[paper]
        layout = Layout(name, paper, width, height, scale)
        self.layouts[name] = layout
        return layout

    # -- annuler / retablir ------------------------------------------------
    def snapshot(self) -> None:
        """Enregistre l'etat avant une modification (commande ANNULER)."""
        import pickle
        self._undo.append(pickle.dumps(
            (self.entities, self.layers, self.blocks, self.selection,
             self._counter), protocol=4))
        if len(self._undo) > self.MAX_UNDO:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self) -> bool:
        """Commande ANNULER."""
        import pickle
        if not self._undo:
            return False
        self._redo.append(pickle.dumps(
            (self.entities, self.layers, self.blocks, self.selection,
             self._counter), protocol=4))
        state = pickle.loads(self._undo.pop())
        (self.entities, self.layers, self.blocks, self.selection,
         self._counter) = state
        return True

    def redo(self) -> bool:
        """Commande RETABLIR."""
        import pickle
        if not self._redo:
            return False
        self._undo.append(pickle.dumps(
            (self.entities, self.layers, self.blocks, self.selection,
             self._counter), protocol=4))
        state = pickle.loads(self._redo.pop())
        (self.entities, self.layers, self.blocks, self.selection,
         self._counter) = state
        return True

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    # -- mesures et synthese -----------------------------------------------
    @property
    def bbox(self) -> BBox3:
        box = BBox3()
        for entity in self.entities.values():
            entity_box = entity.bbox
            if entity_box.valid:
                box.add(entity_box.min).add(entity_box.max)
        return box

    def scale_to_mm(self) -> float:
        return UNITS[self.units]

    def statistics(self) -> Dict[str, Any]:
        """Fiche du document : ce qu'affiche la commande ETAT."""
        kinds: Dict[str, int] = {}
        for entity in self.entities.values():
            kinds[entity.kind] = kinds.get(entity.kind, 0) + 1
        solids = self.solids()
        return {
            "nom": self.name, "unites": self.units,
            "objets": len(self.entities), "par_type": kinds,
            "calques": len(self.layers), "blocs": len(self.blocks),
            "presentations": len(self.layouts),
            "vues_nommees": len(self.named_views),
            "scu": self.current_ucs, "calque_courant": self.current_layer,
            "selection": len(self.selection),
            "annulations": len(self._undo),
            "volume_total_mm3": round(sum(s.volume for s in solids), 3),
            "aire_totale_mm2": round(sum(s.area for s in solids), 3),
            "etendue": self.bbox.to_dict(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document": self.name, "unites": self.units,
            "calques": [layer.to_dict() for layer in self.layers.values()],
            "objets": [entity.to_dict() for entity in self.entities.values()],
            "blocs": [block.to_dict() for block in self.blocks.values()],
            "scu": [ucs.to_dict() for ucs in self.ucs_table.values()],
            "presentations": [layout.to_dict() for layout in self.layouts.values()],
            "vues_nommees": self.named_views,
            "styles_texte": self.text_styles, "styles_cotation": self.dim_styles,
            "variables": self.variables,
            "statistiques": self.statistics(),
        }

    def merge(self, other: "CadDocument", prefix: str = "") -> int:
        """Fusionne un autre document (XREF liee ou import)."""
        added = 0
        for layer in other.layers.values():
            key = prefix + layer.name
            if key not in self.layers:
                self.layers[key] = Layer(key, layer.color, layer.linetype,
                                         layer.lineweight)
        for entity in other.entities.values():
            clone = copy.deepcopy(entity)
            clone.handle = self.new_handle()
            clone.layer = prefix + entity.layer
            self.entities[clone.handle] = clone
            added += 1
        for name, block in other.blocks.items():
            self.blocks.setdefault(prefix + name, copy.deepcopy(block))
        return added
