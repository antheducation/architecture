"""Format natif MERCURY : un JSON qui rend le document a l'identique.

Les formats d'echange perdent toujours quelque chose : le DXF ne garde pas
les solides exacts, le STL oublie les calques, le glTF ignore les blocs. Le
format natif conserve tout : geometrie, calques, blocs, SCU, presentations,
styles, variables et annotations. C'est le format d'enregistrement du
travail en cours et celui des sauvegardes automatiques.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from CAD_Core.document import (Block, CadDocument, Entity, Layer, Layout, UCS)
from CAD_Core.math3d import Vec3
from CAD_Core.profiles import Curve, Profile
from CAD_Core.solid import Polygon, Solid

FORMAT_VERSION = 1


class NativeFormatError(ValueError):
    """Fichier natif illisible ou de version incompatible."""


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------
def _solid_to_dict(solid: Solid) -> Dict[str, Any]:
    return {
        "classe": "solide", "nom": solid.name, "calque": solid.layer,
        "materiau": solid.material, "couleur": solid.color,
        "metadonnees": solid.metadata,
        "faces": [{"sommets": [[round(v.x, 6), round(v.y, 6), round(v.z, 6)]
                               for v in polygon.vertices],
                   "materiau": polygon.material, "calque": polygon.layer,
                   "couleur": polygon.color}
                  for polygon in solid.polygons],
    }


def _curve_to_dict(curve: Curve) -> Dict[str, Any]:
    return {"classe": "courbe", "nom": curve.name, "calque": curve.layer,
            "ferme": curve.closed,
            "points": [[round(p.x, 6), round(p.y, 6), round(p.z, 6)]
                       for p in curve.points]}


def _profile_to_dict(profile: Profile) -> Dict[str, Any]:
    return {"classe": "profil", "nom": profile.name, "calque": profile.layer,
            "contour": [[round(p.x, 6), round(p.y, 6), round(p.z, 6)]
                        for p in profile.outline],
            "ouvertures": [[[round(p.x, 6), round(p.y, 6), round(p.z, 6)]
                            for p in hole] for hole in profile.holes]}


def geometry_to_dict(geometry) -> Dict[str, Any]:
    if isinstance(geometry, Solid):
        return _solid_to_dict(geometry)
    if isinstance(geometry, Curve):
        return _curve_to_dict(geometry)
    if isinstance(geometry, Profile):
        return _profile_to_dict(geometry)
    if isinstance(geometry, dict):
        return {"classe": "annotation", "donnees": geometry}
    raise NativeFormatError("geometrie non serialisable : %r" % type(geometry))


def geometry_from_dict(payload: Dict[str, Any]):
    classe = payload.get("classe")
    if classe == "solide":
        polygons = [Polygon([Vec3(*point) for point in face["sommets"]],
                            face.get("materiau", "default"),
                            face.get("calque", "0"), face.get("couleur", 256))
                    for face in payload.get("faces", [])
                    if len(face.get("sommets", [])) >= 3]
        return Solid(polygons, payload.get("nom", "solide"),
                     payload.get("calque", "0"),
                     payload.get("materiau", "default"),
                     payload.get("couleur", 256),
                     dict(payload.get("metadonnees", {})))
    if classe == "courbe":
        return Curve([Vec3(*point) for point in payload.get("points", [])],
                     bool(payload.get("ferme", False)),
                     payload.get("nom", "courbe"), payload.get("calque", "0"))
    if classe == "profil":
        return Profile([Vec3(*point) for point in payload.get("contour", [])],
                       [[Vec3(*point) for point in hole]
                        for hole in payload.get("ouvertures", [])],
                       payload.get("nom", "profil"), payload.get("calque", "0"))
    if classe == "annotation":
        return dict(payload.get("donnees", {}))
    raise NativeFormatError("classe de geometrie inconnue : %r" % classe)


def _entity_to_dict(entity: Entity) -> Dict[str, Any]:
    return {"handle": entity.handle, "type": entity.kind, "nom": entity.name,
            "calque": entity.layer, "couleur": entity.color,
            "type_ligne": entity.linetype, "epaisseur": entity.lineweight,
            "materiau": entity.material, "visible": entity.visible,
            "verrouille": entity.locked, "transparence": entity.transparency,
            "attributs": entity.attributes,
            "geometrie": geometry_to_dict(entity.geometry)}


def _entity_from_dict(payload: Dict[str, Any]) -> Entity:
    return Entity(payload.get("handle", "0"), payload.get("type", "solide"),
                  geometry_from_dict(payload["geometrie"]),
                  payload.get("calque", "0"), payload.get("couleur", 256),
                  payload.get("type_ligne", "PARCALQUE"),
                  payload.get("epaisseur", -1),
                  payload.get("materiau", "default"),
                  bool(payload.get("visible", True)),
                  bool(payload.get("verrouille", False)),
                  int(payload.get("transparence", 0)),
                  payload.get("nom", ""),
                  dict(payload.get("attributs", {})))


def write_native(document: CadDocument, indent: Optional[int] = 2) -> str:
    """Serialise l'integralite du document."""
    payload = {
        "format": "MERCURY", "version_format": FORMAT_VERSION,
        "document": document.name, "unites": document.units,
        "calque_courant": document.current_layer,
        "scu_courant": document.current_ucs,
        "compteur": document._counter,
        "calques": [layer.to_dict() for layer in document.layers.values()],
        "objets": [_entity_to_dict(entity)
                   for entity in document.entities.values()],
        "blocs": [{"nom": block.name, "point_base": list(block.base_point),
                   "description": block.description,
                   "attributs": dict(block.attributes),
                   "objets": [_entity_to_dict(member)
                              for member in block.entities]}
                  for block in document.blocks.values()],
        "scu": [ucs.to_dict() for ucs in document.ucs_table.values()],
        "presentations": [layout.to_dict()
                          for layout in document.layouts.values()],
        "styles_texte": document.text_styles,
        "styles_cotation": document.dim_styles,
        "materiaux": document.materials,
        "vues_nommees": document.named_views,
        "variables": document.variables,
        "selection": list(document.selection),
    }
    return json.dumps(payload, ensure_ascii=False, indent=indent)


def read_native(text: str, name: Optional[str] = None) -> CadDocument:
    """Reconstruit un document identique a l'original."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise NativeFormatError("JSON MERCURY illisible : %s" % error)
    if payload.get("format") != "MERCURY":
        raise NativeFormatError(
            "ce JSON n'est pas un fichier natif MERCURY (cle 'format' absente)")
    version = int(payload.get("version_format", 0))
    if version > FORMAT_VERSION:
        raise NativeFormatError(
            "fichier ecrit par une version plus recente (format %d, lu %d)"
            % (version, FORMAT_VERSION))
    document = CadDocument(name or payload.get("document", "importe"),
                           payload.get("unites", "mm"))
    document.layers.clear()
    for layer in payload.get("calques", []):
        document.layers[layer["nom"]] = Layer(
            layer["nom"], int(layer.get("couleur", 7)),
            layer.get("type_ligne", "CONTINUOUS"),
            int(layer.get("epaisseur", 25)), bool(layer.get("actif", True)),
            bool(layer.get("gele", False)), bool(layer.get("verrouille", False)),
            bool(layer.get("traceable", True)),
            int(layer.get("transparence", 0)), layer.get("description", ""))
    if not document.layers:
        document.layers["0"] = Layer("0")
    for entity_payload in payload.get("objets", []):
        entity = _entity_from_dict(entity_payload)
        document.entities[entity.handle] = entity
    for block_payload in payload.get("blocs", []):
        document.blocks[block_payload["nom"]] = Block(
            block_payload["nom"],
            [_entity_from_dict(member)
             for member in block_payload.get("objets", [])],
            Vec3(*block_payload.get("point_base", [0, 0, 0])),
            block_payload.get("description", ""),
            dict(block_payload.get("attributs", {})))
    for ucs_payload in payload.get("scu", []):
        document.ucs_table[ucs_payload["nom"]] = UCS(
            ucs_payload["nom"], Vec3(*ucs_payload.get("origine", [0, 0, 0])),
            Vec3(*ucs_payload.get("axe_x", [1, 0, 0])),
            Vec3(*ucs_payload.get("axe_y", [0, 1, 0])))
    document.layouts.clear()
    for layout_payload in payload.get("presentations", []):
        document.layouts[layout_payload["nom"]] = Layout(
            layout_payload["nom"], layout_payload.get("format", "A3"),
            float(layout_payload.get("largeur_mm", 420.0)),
            float(layout_payload.get("hauteur_mm", 297.0)),
            float(layout_payload.get("echelle", 0.01)))
    if not document.layouts:
        document.layouts["Presentation1"] = Layout()
    document.text_styles = payload.get("styles_texte", document.text_styles)
    document.dim_styles = payload.get("styles_cotation", document.dim_styles)
    document.materials = payload.get("materiaux", {})
    document.named_views = payload.get("vues_nommees", {})
    document.variables.update(payload.get("variables", {}))
    document.current_layer = payload.get("calque_courant", "0")
    if document.current_layer not in document.layers:
        document.current_layer = next(iter(document.layers))
    document.current_ucs = payload.get("scu_courant", "GENERAL")
    if document.current_ucs not in document.ucs_table:
        document.ucs_table[document.current_ucs] = UCS(document.current_ucs)
    document._counter = int(payload.get("compteur", len(document.entities)))
    document.selection = [h for h in payload.get("selection", [])
                          if h in document.entities]
    return document
