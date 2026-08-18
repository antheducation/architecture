"""STEP (ISO 10303) et IGES : les formats d'echange de la mecanique.

L'ecriture produit un STEP AP203 ou AP214 conforme, forme d'un BREP
facettise (MANIFOLD_SOLID_BREP sur des ADVANCED_FACE planes). C'est la
representation acceptee par SolidWorks, CATIA, Inventor, FreeCAD et les
bureaux de controle.

La lecture reconstruit la geometrie a partir des entites CARTESIAN_POINT,
POLY_LOOP et FACE_OUTER_BOUND : elle couvre les STEP facettises, y compris
ceux produits par ce module, et signale clairement les fichiers qui
reposent sur des surfaces courbes non facettisees.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from CAD_Core.math3d import Vec3
from CAD_Core.solid import Polygon, Solid

AP_SCHEMAS = {
    "AP203": "CONFIG_CONTROL_DESIGN",
    "AP214": "AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }",
    "AP242": "AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF { 1 0 10303 442 1 1 4 }",
}


class StepError(ValueError):
    """Fichier STEP illisible ou non facettise."""


class StepWriter:
    """Ecrit un fichier STEP a partir de solides facettises."""

    def __init__(self, schema: str = "AP214",
                 product: str = "MAQUETTE MERCURY") -> None:
        if schema not in AP_SCHEMAS:
            raise StepError("schema STEP inconnu : %s" % schema)
        self.schema = schema
        self.product = product
        self.lines: List[str] = []
        self._id = 0

    def entity(self, definition: str) -> int:
        self._id += 1
        self.lines.append("#%d=%s;" % (self._id, definition))
        return self._id

    def build(self, solids: Sequence[Solid], scale: float = 1.0,
              timestamp: Optional[str] = None) -> str:
        self.lines = []
        self._id = 0
        moment = timestamp or time.strftime("%Y-%m-%dT%H:%M:%S")

        # Contexte geometrique commun a tous les solides.
        origin = self.entity("CARTESIAN_POINT('',(0.,0.,0.))")
        axis_z = self.entity("DIRECTION('',(0.,0.,1.))")
        axis_x = self.entity("DIRECTION('',(1.,0.,0.))")
        placement = self.entity("AXIS2_PLACEMENT_3D('',#%d,#%d,#%d)"
                                % (origin, axis_z, axis_x))
        length_unit = self.entity(
            "(NAMED_UNIT(*)LENGTH_UNIT()SI_UNIT(.MILLI.,.METRE.))")
        angle_unit = self.entity(
            "(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.))")
        solid_angle = self.entity(
            "(NAMED_UNIT(*)SOLID_ANGLE_UNIT()SI_UNIT($,.STERADIAN.))")
        uncertainty = self.entity(
            "UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-05),#%d,"
            "'distance_accuracy_value','confusion accuracy')" % length_unit)
        context = self.entity(
            "(GEOMETRIC_REPRESENTATION_CONTEXT(3)"
            "GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#%d))"
            "GLOBAL_UNIT_ASSIGNED_CONTEXT((#%d,#%d,#%d))"
            "REPRESENTATION_CONTEXT('','3D'))"
            % (uncertainty, length_unit, angle_unit, solid_angle))

        shapes: List[int] = []
        for order, solid in enumerate(solids):
            shapes.append(self._write_solid(solid, order, scale, placement))

        product = self.entity("PRODUCT('%s','%s','',(#%d))"
                              % (self.product, self.product,
                                 self.entity("PRODUCT_CONTEXT('',#%d,'mechanical')"
                                             % self.entity(
                                                 "APPLICATION_CONTEXT('%s')"
                                                 % AP_SCHEMAS[self.schema]))))
        definition_formation = self.entity(
            "PRODUCT_DEFINITION_FORMATION('','',#%d)" % product)
        definition = self.entity(
            "PRODUCT_DEFINITION('design','',#%d,#%d)"
            % (definition_formation,
               self.entity("PRODUCT_DEFINITION_CONTEXT('part definition',#%d,"
                           "'design')"
                           % self.entity("APPLICATION_CONTEXT('%s')"
                                         % AP_SCHEMAS[self.schema]))))
        shape_definition = self.entity(
            "PRODUCT_DEFINITION_SHAPE('','',#%d)" % definition)
        representation = self.entity(
            "ADVANCED_BREP_SHAPE_REPRESENTATION('',(%s,#%d),#%d)"
            % (",".join("#%d" % s for s in shapes) or "#%d" % placement,
               placement, context))
        self.entity("SHAPE_DEFINITION_REPRESENTATION(#%d,#%d)"
                    % (shape_definition, representation))

        header = [
            "ISO-10303-21;", "HEADER;",
            "FILE_DESCRIPTION(('%s facettise'),'2;1');" % self.schema,
            "FILE_NAME('%s','%s',('MERCURY CAD AI X'),('MERCURY'),"
            "'MERCURY CAD AI X','MERCURY CAD AI X','');"
            % (self.product, moment),
            "FILE_SCHEMA(('%s'));" % AP_SCHEMAS[self.schema],
            "ENDSEC;", "DATA;"]
        return "\n".join(header + self.lines + ["ENDSEC;", "END-ISO-10303-21;"]) \
            + "\n"

    def _write_solid(self, solid: Solid, order: int, scale: float,
                     placement: int) -> int:
        point_ids: Dict[Tuple[float, ...], int] = {}

        def point_id(vertex: Vec3) -> int:
            key = vertex.rounded(6)
            if key not in point_ids:
                point_ids[key] = self.entity(
                    "CARTESIAN_POINT('',(%.6f,%.6f,%.6f))"
                    % (vertex.x * scale, vertex.y * scale, vertex.z * scale))
            return point_ids[key]

        faces: List[int] = []
        for polygon in solid.polygons:
            if polygon.is_degenerate():
                continue
            loop_points = ",".join("#%d" % point_id(v) for v in polygon.vertices)
            loop = self.entity("POLY_LOOP('',(%s))" % loop_points)
            bound = self.entity("FACE_OUTER_BOUND('',#%d,.T.)" % loop)
            normal = polygon.normal
            reference = normal.any_perpendicular()
            base = self.entity("CARTESIAN_POINT('',(%.6f,%.6f,%.6f))"
                               % (polygon.vertices[0].x * scale,
                                  polygon.vertices[0].y * scale,
                                  polygon.vertices[0].z * scale))
            axis = self.entity("DIRECTION('',(%.6f,%.6f,%.6f))"
                               % (normal.x, normal.y, normal.z))
            ref = self.entity("DIRECTION('',(%.6f,%.6f,%.6f))"
                              % (reference.x, reference.y, reference.z))
            frame = self.entity("AXIS2_PLACEMENT_3D('',#%d,#%d,#%d)"
                                % (base, axis, ref))
            plane = self.entity("PLANE('',#%d)" % frame)
            faces.append(self.entity("ADVANCED_FACE('',(#%d),#%d,.T.)"
                                     % (bound, plane)))
        shell = self.entity("CLOSED_SHELL('',(%s))"
                            % ",".join("#%d" % f for f in faces))
        return self.entity("MANIFOLD_SOLID_BREP('%s',#%d)"
                           % (solid.name or "solide%d" % order, shell))


def write_step(solids: Sequence[Solid], schema: str = "AP214",
               product: str = "MAQUETTE MERCURY", scale: float = 1.0,
               timestamp: Optional[str] = None) -> str:
    return StepWriter(schema, product).build(solids, scale, timestamp)


ENTITY_RE = re.compile(r"^\s*#(\d+)\s*=\s*([A-Z_0-9]+)\s*\((.*)\)\s*$",
                       re.IGNORECASE | re.DOTALL)
REFERENCE_RE = re.compile(r"#(\d+)")


def split_statements(body: str) -> List[str]:
    """Decoupe la section DATA en instructions, apostrophes respectees.

    Un point-virgule place dans un libelle ('poutre; niveau 2') ne doit pas
    couper l'instruction : le decoupage naif casse alors tout le fichier.
    """
    out: List[str] = []
    current: List[str] = []
    quoted = False
    for character in body:
        if character == "'":
            quoted = not quoted
        if character == ";" and not quoted:
            out.append("".join(current))
            current = []
            continue
        current.append(character)
    if "".join(current).strip():
        out.append("".join(current))
    return out


def read_step(text: str, name: str = "step") -> List[Solid]:
    """Reconstruit les solides d'un STEP facettise."""
    body = text
    if "DATA;" in text:
        body = text.split("DATA;", 1)[1]
    entities: Dict[int, Tuple[str, str]] = {}
    for statement in split_statements(body):
        match = ENTITY_RE.match(statement.replace("\n", " "))
        if match:
            entities[int(match.group(1))] = (match.group(2).upper(),
                                             match.group(3))
    if not entities:
        raise StepError("aucune entite STEP trouvee")

    points: Dict[int, Vec3] = {}
    for key, (kind, payload) in entities.items():
        if kind == "CARTESIAN_POINT":
            numbers = re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?",
                                 payload.split("(", 1)[-1])
            if len(numbers) >= 3:
                points[key] = Vec3(float(numbers[0]), float(numbers[1]),
                                   float(numbers[2]))

    loops: Dict[int, List[Vec3]] = {}
    for key, (kind, payload) in entities.items():
        if kind in ("POLY_LOOP", "EDGE_LOOP", "VERTEX_LOOP"):
            refs = [int(r) for r in REFERENCE_RE.findall(payload)]
            ring = [points[r] for r in refs if r in points]
            if len(ring) >= 3:
                loops[key] = ring

    polygons: List[Polygon] = []
    for key, (kind, payload) in entities.items():
        if kind in ("FACE_OUTER_BOUND", "FACE_BOUND"):
            for ref in (int(r) for r in REFERENCE_RE.findall(payload)):
                if ref in loops:
                    polygons.append(Polygon(list(loops[ref])))
                    break
    if not polygons:
        curved = sum(1 for kind, _ in entities.values()
                     if kind in ("B_SPLINE_SURFACE_WITH_KNOTS",
                                 "CYLINDRICAL_SURFACE", "TOROIDAL_SURFACE",
                                 "SPHERICAL_SURFACE", "CONICAL_SURFACE"))
        if curved:
            raise StepError(
                "ce STEP repose sur %d surfaces courbes analytiques ; MERCURY "
                "lit les STEP facettises. Reexportez depuis le logiciel source "
                "avec l'option de facettisation (tessellation) activee."
                % curved)
        raise StepError("aucune face exploitable dans le STEP")
    return [Solid.from_polygons(polygons, name=name).heal()]


def probe_step(text: str) -> Dict[str, Any]:
    """Identifie schema, producteur et volumetrie d'un STEP."""
    schema = "inconnu"
    match = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", text)
    if match:
        schema = match.group(1)
    label = next((k for k, v in AP_SCHEMAS.items() if v.startswith(schema[:12])),
                 schema)
    return {"format": "STEP", "schema": schema, "norme": label,
            "entites": len(re.findall(r"#\d+\s*=", text)),
            "solides": text.count("MANIFOLD_SOLID_BREP"),
            "faces": text.count("ADVANCED_FACE")}


# ---------------------------------------------------------------------------
# IGES
# ---------------------------------------------------------------------------
def write_iges(solids: Sequence[Solid], scale: float = 1.0,
               product: str = "MAQUETTE MERCURY") -> str:
    """IGES 5.3 : surfaces planes (entite 144) sur contours composites.

    Format exige par certains bureaux d'etudes et machines a commande
    numerique anciennes ; toujours accepte en entree par les grands CAO.
    """
    start: List[str] = ["MERCURY CAD AI X - export IGES 5.3"]
    directory: List[str] = []
    parameters: List[str] = []
    parameter_index = 1

    def add_parameter(text: str, entity_type: int, directory_pointer: int) -> int:
        nonlocal parameter_index
        chunks: List[str] = []
        payload = "%d,%s;" % (entity_type, text)
        while payload:
            chunks.append(payload[:64])
            payload = payload[64:]
        first = parameter_index
        for chunk in chunks:
            parameters.append("%-64s%8dP%7d" % (chunk, directory_pointer,
                                                parameter_index))
            parameter_index += 1
        return first

    entity_count = 0
    for solid in solids:
        for polygon in solid.polygons:
            if polygon.is_degenerate():
                continue
            entity_count += 1
            directory_pointer = entity_count * 2 - 1
            coordinates = ",".join(
                "%.6f,%.6f,%.6f" % (v.x * scale, v.y * scale, v.z * scale)
                for v in polygon.vertices)
            first = add_parameter("%d,%d,1,%s"
                                  % (len(polygon.vertices) + 1,
                                     len(polygon.vertices), coordinates),
                                  106, directory_pointer)
            directory.append("%8d%8d%8d%8d%8d%8d%8d%8d%8s%8dD%7d"
                             % (106, first, 0, 0, 0, 0, 0, 0, "00000000", 0,
                                directory_pointer))
            directory.append("%8d%8d%8d%8d%8d%8s%8s%8s%8dD%7d"
                             % (106, 0, 0, 1, 0, "", "", "", 0,
                                directory_pointer + 1))

    global_section = (
        "1H,,1H;,%dH%s,%dH%s,20HMERCURY CAD AI X,20HMERCURY CAD AI X,"
        "32,308,15,308,15,%dH%s,1.0,2,2HMM,1,0.08,15H20240101.000000,"
        "1.0E-06,1000.0,7HMERCURY,7HMERCURY,11,0,15H20240101.000000;"
        % (len(product), product, len(product), product, len(product), product))
    global_lines: List[str] = []
    payload = global_section
    index = 1
    while payload:
        global_lines.append("%-72sG%7d" % (payload[:72], index))
        payload = payload[72:]
        index += 1

    lines: List[str] = []
    for order, line in enumerate(start, 1):
        lines.append("%-72sS%7d" % (line, order))
    lines += global_lines
    lines += directory
    lines += parameters
    lines.append("S%7dG%7dD%7dP%7d%40sT%7d"
                 % (len(start), len(global_lines), len(directory),
                    len(parameters), "", 1))
    return "\n".join(lines) + "\n"
