"""Routes CAO 3D : documents, commandes, outils, formats de fichiers.

Ce routeur expose le noyau CAO complet : creation et edition de documents,
execution de n'importe quelle commande du catalogue, rendu d'images, import
et export de tous les formats geres. L'interface web n'utilise rien d'autre.
"""
from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

import Interop
from CAD_Core.commands import (CommandError, CommandInterpreter, catalog,
                               groups)
from CAD_Core.document import ACI_COLORS, CadDocument, LINETYPES, PAPER_SIZES
from CAD_Core.render_engine import Renderer3D
from CAD_Core.snapping import OSNAP_MODES
from CAD_Core.view3d import STANDARD_VIEWS, VISUAL_STYLES, Camera

router = APIRouter(prefix="/api/v1/cad", tags=["cao"])

MAX_UPLOAD_BYTES = 64 * 1024 * 1024


class DocumentCreate(BaseModel):
    nom: str = Field("SansTitre", min_length=1, max_length=120)
    unites: str = Field("mm", pattern="^(mm|cm|m|in|ft)$")


class CommandRun(BaseModel):
    commande: str = Field(..., min_length=1, max_length=200)
    parametres: Dict[str, Any] = Field(default_factory=dict)


class ScriptRun(BaseModel):
    script: str = Field(..., min_length=1, max_length=200000)


class RenderRequest(BaseModel):
    largeur: int = Field(1280, ge=64, le=4096)
    hauteur: int = Field(800, ge=64, le=4096)
    style: str = "ombre_avec_aretes"
    vue: Optional[str] = None
    azimut: Optional[float] = None
    elevation: Optional[float] = None
    perspective: bool = False


class ExportRequest(BaseModel):
    format: str = Field("dxf", min_length=1, max_length=12)
    options: Dict[str, Any] = Field(default_factory=dict)


class CadWorkspace:
    """Documents CAO ouverts, avec leur interpreteur de commandes."""

    def __init__(self, limit: int = 64) -> None:
        self.limit = limit
        self.sessions: Dict[str, CommandInterpreter] = {}
        self._counter = 0

    def create(self, name: str, units: str = "mm") -> str:
        if len(self.sessions) >= self.limit:
            oldest = next(iter(self.sessions))
            del self.sessions[oldest]
        self._counter += 1
        key = "doc-%04d" % self._counter
        self.sessions[key] = CommandInterpreter(CadDocument(name, units))
        return key

    def get(self, key: str) -> CommandInterpreter:
        if key not in self.sessions:
            raise HTTPException(404, "document inconnu : %s" % key)
        return self.sessions[key]

    def close(self, key: str) -> bool:
        return self.sessions.pop(key, None) is not None

    def list(self) -> List[Dict[str, Any]]:
        return [{"id": key, "nom": session.document.name,
                 "objets": len(session.document.entities),
                 "calques": len(session.document.layers),
                 "unites": session.document.units}
                for key, session in self.sessions.items()]


WORKSPACE = CadWorkspace()


# ---------------------------------------------------------------------------
# Catalogue et capacites
# ---------------------------------------------------------------------------
@router.get("/commands")
def list_commands(groupe: Optional[str] = None) -> Dict[str, Any]:
    """Catalogue des commandes : c'est ce qui alimente le ruban de l'interface."""
    items = [c for c in catalog() if not groupe or c["groupe"] == groupe]
    return {"total": len(items), "groupes": groups(), "commandes": items}


@router.get("/capabilities")
def capabilities() -> Dict[str, Any]:
    """Tout ce que sait faire le module CAO : commandes, formats, styles."""
    return {
        "commandes": len(catalog()),
        "groupes_commandes": groups(),
        "formats": Interop.capabilities(),
        "styles_visuels": sorted(VISUAL_STYLES),
        "vues_normalisees": sorted(STANDARD_VIEWS),
        "accrochages": sorted(OSNAP_MODES),
        "types_de_ligne": LINETYPES,
        "formats_papier": sorted(PAPER_SIZES),
        "couleurs_aci": len(ACI_COLORS),
    }


@router.get("/formats")
def list_formats(nature: Optional[str] = None,
                 capacite: Optional[str] = None) -> Dict[str, Any]:
    """Matrice des formats de fichiers lus et ecrits."""
    items = Interop.formats(nature, capacite)
    return {"total": len(items), "formats": items,
            "dwg": Interop.dwg_module.describe_backends()}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@router.post("/documents")
def create_document(payload: DocumentCreate) -> Dict[str, Any]:
    key = WORKSPACE.create(payload.nom, payload.unites)
    return {"document": key, "etat": WORKSPACE.get(key).document.statistics()}


@router.get("/documents")
def list_documents() -> Dict[str, Any]:
    items = WORKSPACE.list()
    return {"total": len(items), "documents": items}


@router.get("/documents/{document_id}")
def get_document(document_id: str, detail: bool = False) -> Dict[str, Any]:
    session = WORKSPACE.get(document_id)
    if detail:
        return {"document": document_id, "contenu": session.document.to_dict()}
    return {"document": document_id, "etat": session.document.statistics(),
            "calques": [layer.to_dict()
                        for layer in session.document.layers.values()],
            "fenetre": session.viewport.to_dict()}


@router.delete("/documents/{document_id}")
def close_document(document_id: str) -> Dict[str, bool]:
    return {"ferme": WORKSPACE.close(document_id)}


@router.get("/documents/{document_id}/entities")
def list_entities(document_id: str, calque: Optional[str] = None,
                  limit: int = Query(500, ge=1, le=5000)) -> Dict[str, Any]:
    session = WORKSPACE.get(document_id)
    items = [entity.to_dict() for entity in session.document.entities.values()
             if not calque or entity.layer == calque][:limit]
    return {"total": len(items), "objets": items}


# ---------------------------------------------------------------------------
# Execution de commandes
# ---------------------------------------------------------------------------
@router.post("/documents/{document_id}/command")
def run_command(document_id: str, payload: CommandRun) -> Dict[str, Any]:
    """Execute une commande du catalogue sur le document."""
    session = WORKSPACE.get(document_id)
    try:
        result = session.execute(payload.commande, **payload.parametres)
    except CommandError as error:
        raise HTTPException(400, str(error))
    return {"document": document_id, "resultat": result,
            "etat": session.document.statistics()}


@router.post("/documents/{document_id}/script")
def run_script(document_id: str, payload: ScriptRun) -> Dict[str, Any]:
    """Execute un script de commandes, comme un fichier .scr d'AutoCAD."""
    session = WORKSPACE.get(document_id)
    try:
        results = session.run_script(payload.script)
    except CommandError as error:
        raise HTTPException(400, str(error))
    return {"document": document_id, "commandes": len(results),
            "resultats": results, "etat": session.document.statistics()}


@router.get("/documents/{document_id}/history")
def history(document_id: str,
            limit: int = Query(100, ge=1, le=1000)) -> Dict[str, Any]:
    session = WORKSPACE.get(document_id)
    return {"total": len(session.history), "historique": session.history[-limit:]}


# ---------------------------------------------------------------------------
# Geometrie pour la visionneuse
# ---------------------------------------------------------------------------
@router.get("/documents/{document_id}/mesh")
def document_mesh(document_id: str,
                  angle_aretes: float = Query(18.0, ge=0.0, le=180.0)
                  ) -> Dict[str, Any]:
    """Maillage triangule pret pour WebGL : positions, normales, groupes.

    Seules les aretes vives sont renvoyees : au-dela de `angle_aretes` degres
    entre deux faces voisines. Une sphere facettisee garde ainsi sa silhouette
    lisse au lieu d'afficher le quadrillage de sa triangulation, exactement
    comme les isolignes d'AutoCAD. `angle_aretes=0` renvoie toutes les aretes.
    """
    from CAD_Core.solid_edit import dihedral_angle, edge_map
    session = WORKSPACE.get(document_id)
    positions: List[float] = []
    normals: List[float] = []
    groups_out: List[Dict[str, Any]] = []
    edges: List[float] = []
    for entity in session.document.visible_entities():
        geometry = entity.geometry
        if not hasattr(geometry, "polygons"):
            continue
        start = len(positions) // 3
        for polygon in geometry.polygons:
            normal = polygon.normal
            for a, b, c in polygon.triangulate():
                for point in (a, b, c):
                    positions += [point.x, point.y, point.z]
                    normals += [normal.x, normal.y, normal.z]
        if angle_aretes <= 0.0:
            for a, b in geometry.edges():
                edges += [a.x, a.y, a.z, b.x, b.y, b.z]
        else:
            for key, faces in edge_map(geometry).items():
                if len(faces) == 2 and \
                        abs(dihedral_angle(geometry, faces) - 180.0) < angle_aretes:
                    continue
                edges += list(key[0]) + list(key[1])
        groups_out.append({"handle": entity.handle, "nom": entity.name,
                           "calque": entity.layer,
                           "materiau": entity.material or geometry.material,
                           "debut": start,
                           "sommets": len(positions) // 3 - start})
    box = session.document.bbox
    return {"document": document_id, "positions": positions, "normales": normals,
            "aretes": edges, "groupes": groups_out,
            "sommets": len(positions) // 3,
            "boite": box.to_dict() if box.valid else {"vide": True}}


@router.get("/documents/{document_id}/curves")
def document_curves(document_id: str) -> Dict[str, Any]:
    """Courbes et contours du document, pour l'affichage filaire."""
    from CAD_Core.profiles import Curve, Profile
    session = WORKSPACE.get(document_id)
    items: List[Dict[str, Any]] = []
    for entity in session.document.visible_entities():
        geometry = entity.geometry
        if isinstance(geometry, Curve):
            items.append({"handle": entity.handle, "calque": entity.layer,
                          "ferme": geometry.closed,
                          "points": [list(p) for p in geometry.points]})
        elif isinstance(geometry, Profile):
            for ring in geometry.rings():
                items.append({"handle": entity.handle, "calque": entity.layer,
                              "ferme": True, "points": [list(p) for p in ring]})
    return {"total": len(items), "courbes": items}


@router.post("/documents/{document_id}/render")
def render(document_id: str, payload: RenderRequest) -> Response:
    """Rend une image PNG du document avec le style visuel demande."""
    session = WORKSPACE.get(document_id)
    if payload.style not in VISUAL_STYLES:
        raise HTTPException(400, "style visuel inconnu : %s" % payload.style)
    camera = Camera(width=payload.largeur, height=payload.hauteur)
    camera.perspective = payload.perspective
    if payload.vue:
        if payload.vue not in STANDARD_VIEWS:
            raise HTTPException(400, "vue inconnue : %s" % payload.vue)
        camera.set_standard_view(payload.vue)
    if payload.azimut is not None:
        camera.azimuth_deg = payload.azimut
    if payload.elevation is not None:
        camera.elevation_deg = payload.elevation
    camera.zoom_extents(session.document.bbox)
    frame = Renderer3D().render(session.document.solids(), camera, payload.style)
    return Response(content=frame.to_png(), media_type="image/png")


# ---------------------------------------------------------------------------
# Fichiers
# ---------------------------------------------------------------------------
@router.post("/documents/{document_id}/export")
def export_document(document_id: str, payload: ExportRequest):
    """Exporte le document dans l'un des formats du registre."""
    session = WORKSPACE.get(document_id)
    try:
        spec = Interop.spec_for(payload.format)
        data = Interop.export_data(session.document, spec.key,
                                   session.annotations, **payload.options)
    except Interop.InteropError as error:
        raise HTTPException(400, str(error))
    except ValueError as error:
        raise HTTPException(400, "export impossible : %s" % error)
    filename = "%s%s" % (session.document.name.replace(" ", "_"),
                         spec.extensions[0])
    headers = {"Content-Disposition": 'attachment; filename="%s"' % filename}
    if isinstance(data, (bytes, bytearray)):
        return Response(content=bytes(data),
                        media_type="application/octet-stream", headers=headers)
    return PlainTextResponse(data, media_type="text/plain; charset=utf-8",
                             headers=headers)


@router.post("/documents/{document_id}/import")
async def import_into_document(document_id: str,
                               fichier: UploadFile = File(...)) -> Dict[str, Any]:
    """Importe un fichier et le fusionne dans le document ouvert."""
    session = WORKSPACE.get(document_id)
    data = await fichier.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "fichier trop volumineux (maximum %d Mo)"
                            % (MAX_UPLOAD_BYTES // (1024 * 1024)))
    try:
        imported = _import_payload(data, fichier.filename or "")
    except (Interop.InteropError, ValueError) as error:
        raise HTTPException(400, str(error))
    added = session.document.merge(imported["document"])
    return {"document": document_id, "format": imported["format"],
            "objets_ajoutes": added, "etat": session.document.statistics()}


@router.post("/files/identify")
async def identify_file(fichier: UploadFile = File(...)) -> Dict[str, Any]:
    """Reconnait un fichier a sa signature, sans l'importer."""
    data = await fichier.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "fichier trop volumineux")
    try:
        return {"fichier": fichier.filename,
                "identification": Interop.identify(data, fichier.filename or "")}
    except Interop.InteropError as error:
        raise HTTPException(400, str(error))


@router.post("/files/open")
async def open_file(fichier: UploadFile = File(...)) -> Dict[str, Any]:
    """Ouvre un fichier dans un nouveau document."""
    data = await fichier.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "fichier trop volumineux")
    name = os.path.splitext(os.path.basename(fichier.filename or "importe"))[0]
    try:
        imported = _import_payload(data, fichier.filename or "")
    except (Interop.InteropError, ValueError) as error:
        raise HTTPException(400, str(error))
    key = WORKSPACE.create(name, imported["document"].units)
    session = WORKSPACE.get(key)
    session.document = imported["document"]
    session.document.name = name
    return {"document": key, "format": imported["format"],
            "etat": session.document.statistics()}


@router.post("/files/convert")
async def convert_file(fichier: UploadFile = File(...),
                       cible: str = Query(..., min_length=2, max_length=12)):
    """Convertit un fichier d'un format vers un autre, sans ouvrir de document."""
    data = await fichier.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "fichier trop volumineux")
    try:
        imported = _import_payload(data, fichier.filename or "")
        spec = Interop.spec_for(cible)
        payload = Interop.export_data(imported["document"], spec.key)
    except (Interop.InteropError, ValueError) as error:
        raise HTTPException(400, str(error))
    base = os.path.splitext(os.path.basename(fichier.filename or "sortie"))[0]
    headers = {"Content-Disposition": 'attachment; filename="%s%s"'
               % (base, spec.extensions[0])}
    if isinstance(payload, (bytes, bytearray)):
        return Response(content=bytes(payload),
                        media_type="application/octet-stream", headers=headers)
    return PlainTextResponse(payload, media_type="text/plain; charset=utf-8",
                             headers=headers)


def _import_payload(data: bytes, filename: str) -> Dict[str, Any]:
    """Import d'un contenu televerse ; le DWG transite par un fichier temporaire."""
    extension = os.path.splitext(filename)[1].lower()
    if extension == ".dwg":
        with tempfile.NamedTemporaryFile(suffix=".dwg", delete=False) as handle:
            handle.write(data)
            path = handle.name
        try:
            return Interop.import_file(path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    return Interop.import_data(data, filename)
