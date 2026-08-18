"""Application FastAPI de MERCURY CAD AI X (livrables #10 et #24).

Expose l'ensemble des moteurs derriere une API versionnee et documentee.
Le endpoint /health repond sans toucher a la base : c'est la sonde de
disponibilite utilisee par Docker, Kubernetes et la chaine d'integration.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import (FileResponse, JSONResponse, PlainTextResponse,
                               RedirectResponse)

from AI_Engine.generative_design import build_program
from API.cad import router as cad_router
from API.deps import get_state
from API.schemas import (
    CommandRequest, GenerateRequest, OpeningCreate, ProjectCreate,
    ReadingBatch, SensorCreate, WallCreate,
)
from BIM_Engine.models import BuildingProject, Opening, Wall
from DELIVERABLES import DELIVERABLES

VERSION = "1.0.0"
START_TIME = time.time()

app = FastAPI(
    title="MERCURY CAD AI X - PROJET TITAN",
    version=VERSION,
    description="Plateforme CAO 2D vers BIM 3D assistee par intelligence "
                "artificielle : modelisation 3D complete, conception "
                "generative, metre, environnement, jumeau numerique, et "
                "echange de fichiers DWG, DXF, IFC, STEP, STL, PDF et images.",
)

# Noyau CAO 3D : documents, commandes, outils volumiques, formats de fichiers.
app.include_router(cad_router)


# ---------------------------------------------------------------------------
# Systeme
# ---------------------------------------------------------------------------
@app.get("/health", tags=["systeme"])
def health() -> Dict[str, Any]:
    """Sonde de disponibilite. Ne touche pas la base : toujours rapide."""
    return {"status": "ok", "version": VERSION,
            "uptime_seconds": round(time.time() - START_TIME, 1)}


@app.get("/ready", tags=["systeme"])
def ready() -> Dict[str, Any]:
    """Sonde de preparation : verifie reellement l'acces a la base."""
    state = get_state()
    try:
        state.database.query("SELECT 1")
    except Exception as error:
        raise HTTPException(503, "base indisponible : %s" % error)
    return {"ready": True, "migrations": state.applied_migrations,
            "projets": len(state.repository.list())}


@app.get("/", tags=["systeme"])
def root() -> Dict[str, Any]:
    from CAD_Core.commands import catalog as command_catalog
    import Interop
    return {"produit": "MERCURY CAD AI X - PROJET TITAN", "version": VERSION,
            "documentation": "/docs", "interface": "/app",
            "livrables": len(DELIVERABLES),
            "commandes_cao": len(command_catalog()),
            "formats_fichiers": len(Interop.FORMATS)}


@app.get("/app", include_in_schema=False)
def workspace_redirect() -> RedirectResponse:
    """Redirige vers /app/ : l'interface charge ses fichiers en relatif."""
    return RedirectResponse("/app/", status_code=308)


@app.get("/app/", include_in_schema=False)
def workspace() -> FileResponse:
    """Sert l'interface de modelisation 3D."""
    return _frontend_file("index.html", "text/html")


@app.get("/app/{asset}", include_in_schema=False)
def workspace_asset(asset: str) -> FileResponse:
    """Sert les fichiers statiques de l'interface (style, scripts)."""
    media = {"style.css": "text/css", "app.js": "application/javascript",
             "viewer.js": "application/javascript",
             "index.html": "text/html"}
    if asset not in media:
        raise HTTPException(404, "ressource inconnue : %s" % asset)
    return _frontend_file(asset, media[asset])


def _frontend_file(name: str, media_type: str) -> FileResponse:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))), "Frontend", name)
    if not os.path.isfile(path):
        raise HTTPException(404, "ressource introuvable : %s" % name)
    return FileResponse(path, media_type=media_type)


@app.get("/api/v1/deliverables", tags=["systeme"])
def deliverables(groupe: Optional[str] = None) -> Dict[str, Any]:
    """Registre des 70 livrables : numero, groupe, module, etat."""
    items = [d for d in DELIVERABLES if not groupe or d["groupe"] == groupe]
    return {"total": len(items), "livrables": items}


# ---------------------------------------------------------------------------
# Projets
# ---------------------------------------------------------------------------
@app.post("/api/v1/projects", tags=["projets"])
def create_project(payload: ProjectCreate) -> Dict[str, Any]:
    state = get_state()
    try:
        project = BuildingProject(name=payload.name,
                                  building_type=payload.building_type)
    except ValueError as error:
        raise HTTPException(400, str(error))
    state.repository.save(project)
    return {"projet": _summary(project)}


@app.get("/api/v1/projects", tags=["projets"])
def list_projects(limit: int = Query(100, ge=1, le=1000)) -> Dict[str, Any]:
    return {"projets": get_state().repository.list(limit=limit)}


@app.get("/api/v1/projects/{project_id}", tags=["projets"])
def get_project(project_id: str, version: Optional[int] = None) -> Dict[str, Any]:
    project = _load(project_id, version)
    state = get_state()
    return {"projet": _summary(project),
            "versions": state.repository.versions(project_id),
            "modele": project.to_dict()}


@app.delete("/api/v1/projects/{project_id}", tags=["projets"])
def delete_project(project_id: str) -> Dict[str, bool]:
    return {"supprime": get_state().repository.delete(project_id)}


# ---------------------------------------------------------------------------
# Conception generative (#03)
# ---------------------------------------------------------------------------
@app.post("/api/v1/design/generate", tags=["conception"])
def generate(payload: GenerateRequest) -> Dict[str, Any]:
    """Programme architectural vers plans complets, classes par score."""
    state = get_state()
    try:
        program = build_program(payload.typologie, payload.surface,
                                payload.chambres, payload.salles_de_bain)
        projects = state.designer.generate(program, payload.variantes,
                                           payload.iterations, payload.graine)
    except ValueError as error:
        raise HTTPException(400, str(error))
    results = []
    for project in projects:
        state.repository.save(project)
        results.append({**_summary(project),
                        "score": project.metadata.get("cout"),
                        "detail_score": project.metadata.get("detail_cout")})
    return {"programme": program.describe(),
            "saturation": program.saturation,
            "emprise_mm": [round(program.plot_width), round(program.plot_depth)],
            "variantes": results, "meilleure": results[0]["id"] if results else None}


# ---------------------------------------------------------------------------
# Edition
# ---------------------------------------------------------------------------
@app.post("/api/v1/projects/{project_id}/walls", tags=["edition"])
def add_wall(project_id: str, payload: WallCreate) -> Dict[str, Any]:
    project = _load(project_id)
    try:
        wall = Wall(start=tuple(payload.start), end=tuple(payload.end),
                    thickness=payload.thickness, height=payload.height,
                    exterior=payload.exterior)
    except ValueError as error:
        raise HTTPException(400, str(error))
    project.add_wall(wall)
    get_state().repository.save(project.bump())
    return {"mur": {"id": wall.id, "longueur_mm": round(wall.length, 1)},
            "version": project.version}


@app.post("/api/v1/projects/{project_id}/openings", tags=["edition"])
def add_opening(project_id: str, payload: OpeningCreate) -> Dict[str, Any]:
    project = _load(project_id)
    wall = project.wall(payload.wall_id)
    if wall is None:
        raise HTTPException(404, "mur introuvable")
    try:
        opening = wall.add_opening(Opening(
            type=payload.type, offset=payload.offset, width=payload.width,
            height=payload.height, sill=payload.sill))
    except ValueError as error:
        raise HTTPException(400, str(error))
    get_state().repository.save(project.bump())
    return {"baie": {"id": opening.id, "type": opening.type},
            "version": project.version}


@app.post("/api/v1/projects/{project_id}/rooms/rebuild", tags=["edition"])
def rebuild_rooms(project_id: str) -> Dict[str, Any]:
    """Recalcule les pieces depuis les murs (arrangement planaire)."""
    state = get_state()
    project = _load(project_id)
    faces = state.engine_2d.detect_rooms(project.walls)
    if not faces and project.rooms:
        return {"pieces": len(project.rooms),
                "avertissement": "aucun contour ferme : les murs doivent se "
                                 "rejoindre ; l'etat precedent est conserve"}
    from BIM_Engine.models import Room
    thickness = (sum(w.thickness for w in project.walls) / len(project.walls)
                 if project.walls else 100.0)
    project.rooms = []
    for index, face in enumerate(faces):
        metrics = state.engine_2d.room_metrics(face, thickness)
        project.rooms.append(Room(name="Piece %d" % (index + 1), **metrics,
                                  height=project.levels[0].height,
                                  level_id=project.levels[0].id))
    state.repository.save(project.bump())
    return {"pieces": len(project.rooms),
            "surface_m2": project.total_area_m2, "version": project.version}


# ---------------------------------------------------------------------------
# Assistant (#04)
# ---------------------------------------------------------------------------
@app.post("/api/v1/assistant", tags=["assistant"])
def assistant(payload: CommandRequest) -> Dict[str, Any]:
    state = get_state()
    command = state.assistant.parse(payload.message)
    return {"commande": command.as_dict(),
            "message": _explain(command)}


# ---------------------------------------------------------------------------
# Metre, couts, environnement
# ---------------------------------------------------------------------------
@app.get("/api/v1/projects/{project_id}/takeoff", tags=["economie"])
def takeoff(project_id: str) -> Dict[str, Any]:
    state = get_state()
    project = _load(project_id)
    return {"resume": state.takeoff.summary(project),
            "nomenclature": state.documents.room_schedule(project),
            "metre": [line.as_dict() for line in state.takeoff.compute(project)]}


@app.get("/api/v1/projects/{project_id}/estimate", tags=["economie"])
def estimate(project_id: str, devise: str = "EUR",
             coef_region: float = Query(1.0, gt=0)) -> Dict[str, Any]:
    state = get_state()
    project = _load(project_id)
    result = state.estimator.estimate(project, devise, coef_region)
    schedule = state.estimator.schedule(result)
    return {"devis": result, "planning": state.planner.plan(schedule)}


@app.get("/api/v1/projects/{project_id}/carbon", tags=["environnement"])
def carbon(project_id: str) -> Dict[str, Any]:
    return get_state().carbon.analyze(_load(project_id))


@app.get("/api/v1/projects/{project_id}/energy", tags=["environnement"])
def energy(project_id: str, isolation: str = "neuf",
           climat: str = "oceanique") -> Dict[str, Any]:
    from Sustainability.energy import EnergyOptions
    state = get_state()
    try:
        return state.energy.simulate(
            _load(project_id), EnergyOptions(insulation=isolation, climate=climat))
    except ValueError as error:
        raise HTTPException(400, str(error))


@app.get("/api/v1/projects/{project_id}/certification", tags=["environnement"])
def certification(project_id: str) -> Dict[str, Any]:
    state = get_state()
    project = _load(project_id)
    return state.certification.score(state.energy.simulate(project),
                                     state.carbon.analyze(project))


# ---------------------------------------------------------------------------
# Jumeau numerique (#41, #43)
# ---------------------------------------------------------------------------
@app.post("/api/v1/iot/sensors", tags=["jumeau"])
def declare_sensor(payload: SensorCreate) -> Dict[str, Any]:
    state = get_state()
    project = _load(payload.projet)
    if payload.piece and project.room(payload.piece) is None:
        raise HTTPException(404, "piece introuvable dans ce projet")
    try:
        sensor = state.sensors.declare(payload.id, payload.grandeur,
                                       payload.projet, payload.piece, payload.nom)
    except ValueError as error:
        raise HTTPException(400, str(error))
    return {"capteur": sensor.as_dict()}


@app.post("/api/v1/iot/readings", tags=["jumeau"])
def ingest(payload: ReadingBatch) -> Dict[str, Any]:
    return get_state().iot.ingest(payload.mesures)


@app.get("/api/v1/projects/{project_id}/twin", tags=["jumeau"])
def twin(project_id: str) -> Dict[str, Any]:
    return get_state().twin.state(_load(project_id))


# ---------------------------------------------------------------------------
# Bibliotheque et exports
# ---------------------------------------------------------------------------
@app.get("/api/v1/library", tags=["bibliotheque"])
def library(q: str = "", categorie: str = "",
            limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    items = get_state().library.search(q, categorie, limit)
    return {"total": len(items),
            "objets": [{"id": i.id, "nom": i.name, "categorie": i.category,
                        "dimensions_mm": list(i.size), "prix": i.unit_cost}
                       for i in items]}


@app.post("/api/v1/projects/{project_id}/export", tags=["exports"])
def export(project_id: str, format: str = Body("ifc", embed=True)):
    state = get_state()
    project = _load(project_id)
    fmt = format.lower()
    if fmt == "ifc":
        return PlainTextResponse(state.ifc.export(project),
                                 media_type="application/x-step")
    mesh = state.engine_3d.build(project)
    if fmt == "obj":
        return PlainTextResponse(state.renderer.to_obj(mesh))
    if fmt == "gltf":
        return PlainTextResponse(state.renderer.to_gltf(mesh),
                                 media_type="model/gltf+json")
    if fmt == "svg":
        return PlainTextResponse(state.renderer.plan_svg(project),
                                 media_type="image/svg+xml")
    if fmt == "json":
        return JSONResponse(project.to_dict())
    raise HTTPException(400, "format non supporte : ifc, obj, gltf, svg, json")


@app.get("/api/v1/projects/{project_id}/mesh", tags=["exports"])
def mesh(project_id: str) -> Dict[str, Any]:
    state = get_state()
    return {"maillage": state.engine_3d.build(_load(project_id)).stats}


# ---------------------------------------------------------------------------
# Utilitaires internes
# ---------------------------------------------------------------------------
def _load(project_id: str, version: Optional[int] = None) -> BuildingProject:
    try:
        return get_state().repository.load(project_id, version)
    except KeyError as error:
        raise HTTPException(404, str(error))


def _summary(project: BuildingProject) -> Dict[str, Any]:
    return {"id": project.id, "nom": project.name,
            "type": project.building_type, "version": project.version,
            "surface_m2": project.total_area_m2,
            "pieces": len(project.rooms), "murs": len(project.walls)}


def _explain(command) -> str:
    if command.action == "unknown":
        return ("Commande non comprise. Exemples : « genere une maison de "
                "110 m2 », « change le style en moderne », « exporte en ifc ».")
    return "Commande reconnue : %s" % command.action
