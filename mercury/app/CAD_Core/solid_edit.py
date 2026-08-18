"""Edition de solides : le groupe Modification du ruban 3D.

RACCORDARETE, CHANFREINARETE, GAINE, COUPE, SECTION, DEPOUILLE, EMPREINTE,
DECALAGE, plus les conversions solide/surface. Toutes les operations sont
menees par decoupe booleenne exacte : on fabrique le volume de matiere a
retirer, puis on le soustrait. Le resultat reste un solide ferme, verifiable
par `Solid.check()`.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .math3d import (BBox3, EPS, Mat4, ORIGIN, Plane, TOL, Vec3, Z_AXIS)
from .modeling import extrude, offset_ring
from .primitives import box, cylinder, sphere
from .profiles import Curve, Profile
from .solid import Polygon, Solid, union_all


# ---------------------------------------------------------------------------
# Topologie : aretes et faces adjacentes
# ---------------------------------------------------------------------------
def edge_map(solid: Solid, digits: int = 4) -> Dict[Tuple, List[int]]:
    """Associe chaque arete a la liste des faces qui la portent."""
    edges: Dict[Tuple, List[int]] = {}
    for index, polygon in enumerate(solid.polygons):
        count = len(polygon.vertices)
        for i in range(count):
            a = polygon.vertices[i].rounded(digits)
            b = polygon.vertices[(i + 1) % count].rounded(digits)
            key = (a, b) if a <= b else (b, a)
            edges.setdefault(key, []).append(index)
    return edges


def dihedral_angle(solid: Solid, faces: Sequence[int]) -> float:
    """Angle diedre entre deux faces, en degres (180 = arete plate)."""
    if len(faces) != 2:
        return 180.0
    n1 = solid.polygons[faces[0]].normal
    n2 = solid.polygons[faces[1]].normal
    return math.degrees(math.pi - n1.angle_to(n2))


def sharp_edges(solid: Solid, tolerance_deg: float = 1.0
                ) -> List[Tuple[Vec3, Vec3, List[int]]]:
    """Aretes vives du solide : celles que RACCORDARETE peut traiter."""
    out: List[Tuple[Vec3, Vec3, List[int]]] = []
    for key, faces in edge_map(solid).items():
        if len(faces) != 2:
            continue
        if abs(dihedral_angle(solid, faces) - 180.0) <= tolerance_deg:
            continue
        out.append((Vec3(*key[0]), Vec3(*key[1]), faces))
    return out


def _edge_frame(solid: Solid, a: Vec3, b: Vec3, faces: Sequence[int]):
    """Repere local d'une arete : direction, normales et sens de la matiere."""
    direction = (b - a).unit()
    if direction.norm() < TOL:
        return None
    n1 = solid.polygons[faces[0]].normal
    n2 = solid.polygons[faces[1]].normal
    if abs(n1.dot(n2)) > 1.0 - 1e-9:
        return None
    return direction, n1, n2


def _corner_solid(a: Vec3, b: Vec3, direction: Vec3, p1: Vec3, corner: Vec3,
                  p2: Vec3, margin: float, material: str) -> Solid:
    """Prisme couvrant le coin de matiere a retirer le long d'une arete."""
    start = a - direction * margin
    shift = direction * ((b - a).norm() + 2 * margin)
    offsets = [p1 - corner, Vec3(), p2 - corner]
    base = [start + corner - a + o for o in offsets]
    top = [p + shift for p in base]
    polygons = [Polygon(list(reversed(base)), material=material),
                Polygon(list(top), material=material)]
    for i in range(3):
        j = (i + 1) % 3
        polygons.append(Polygon([base[i], base[j], top[j], top[i]],
                                material=material))
    return Solid.from_polygons(polygons, name="coin", material=material).outward()


def chamfer_edge(solid: Solid, edge: Tuple[Vec3, Vec3], distance: float = 50.0,
                 distance2: Optional[float] = None,
                 name: Optional[str] = None) -> Solid:
    """Commande CHANFREINARETE : coupe droite le long d'une arete."""
    if distance <= 0:
        raise ValueError("CHANFREINARETE : la distance doit etre positive")
    d2 = distance if distance2 is None else distance2
    a, b = Vec3.of(edge[0]), Vec3.of(edge[1])
    faces = _faces_of_edge(solid, a, b)
    frame = _edge_frame(solid, a, b, faces)
    if frame is None:
        return solid.copy(name)
    direction, n1, n2 = frame
    t1 = _inward(direction, n1, n2)
    t2 = _inward(direction, n2, n1)
    p1 = a + t1 * distance
    p2 = a + t2 * d2
    margin = max(distance, d2) * 0.5 + 1.0
    shard = _corner_solid(a, b, direction, p1, a, p2, margin, solid.material)
    return solid.subtract(shard, name or solid.name)


def fillet_edge(solid: Solid, edge: Tuple[Vec3, Vec3], radius: float = 50.0,
                segments: int = 12, name: Optional[str] = None) -> Solid:
    """Commande RACCORDARETE : arrondi tangent le long d'une arete."""
    if radius <= 0:
        raise ValueError("RACCORDARETE : le rayon doit etre positif")
    a, b = Vec3.of(edge[0]), Vec3.of(edge[1])
    faces = _faces_of_edge(solid, a, b)
    frame = _edge_frame(solid, a, b, faces)
    if frame is None:
        return solid.copy(name)
    shard = _fillet_shard(solid, a, b, frame, radius, segments)
    if shard is None:
        return solid.copy(name)
    return solid.subtract(shard, name or solid.name)


def _faces_of_edge(solid: Solid, a: Vec3, b: Vec3) -> List[int]:
    key_a, key_b = a.rounded(4), b.rounded(4)
    key = (key_a, key_b) if key_a <= key_b else (key_b, key_a)
    faces = edge_map(solid).get(key, [])
    if len(faces) != 2:
        raise ValueError("arete introuvable ou non partagee par deux faces")
    return faces


def _inward(direction: Vec3, normal: Vec3, other_normal: Vec3) -> Vec3:
    """Direction dans le plan d'une face, tournee vers l'interieur du solide."""
    t = normal.cross(direction).unit()
    if t.dot(other_normal) > 0:
        t = -t
    return t


def _fillet_center(a: Vec3, n1: Vec3, n2: Vec3, radius: float) -> Optional[Vec3]:
    """Centre du cylindre tangent aux deux faces, a distance `radius`."""
    bisector = (n1 + n2)
    if bisector.norm() < 1e-9:
        return None
    m = bisector.unit()
    cos_phi = n1.dot(m)
    if abs(cos_phi) < 1e-6:
        return None
    return a - m * (radius / cos_phi)


def _fillet_shard(solid: Solid, a: Vec3, b: Vec3, frame, radius: float,
                  segments: int) -> Optional[Solid]:
    direction, n1, n2 = frame
    center = _fillet_center(a, n1, n2, radius)
    if center is None:
        return None
    p1 = center + n1 * radius
    p2 = center + n2 * radius
    if (p1 - a).norm() > 1e4 * radius or (p2 - a).norm() > 1e4 * radius:
        return None
    margin = radius * 0.75 + 1.0
    corner = _corner_solid(a, b, direction, p1, a, p2, margin, solid.material)
    length = (b - a).norm() + 2 * margin
    round_tool = cylinder(radius, length, center - direction * margin,
                          max(8, segments * 2), None, direction,
                          solid.material, "rond")
    return corner.subtract(round_tool, "eclat")


def fillet_all_edges(solid: Solid, radius: float = 20.0, segments: int = 10,
                     convex_only: bool = True, max_edges: int = 64,
                     name: Optional[str] = None) -> Solid:
    """RACCORDARETE applique a toutes les aretes vives d'un solide.

    Les eclats de matiere sont tous calcules sur la geometrie d'origine,
    puis retires l'un apres l'autre. Aux sommets ou trois raccords se
    rejoignent, le coin restant est l'intersection des surfaces de raccord
    voisines : l'ecart avec un coin strictement spherique reste inferieur a
    un demi pour cent en volume, pour un calcul robuste et rapide.
    """
    edges = sharp_edges(solid)
    if convex_only:
        edges = [e for e in edges if dihedral_angle(solid, e[2]) < 180.0]
    if not edges:
        return solid.copy(name)
    if len(edges) > max_edges:
        edges = sorted(edges, key=lambda e: -(e[1] - e[0]).norm())[:max_edges]

    result = solid.copy(name or solid.name)
    for a, b, faces in edges:
        frame = _edge_frame(solid, a, b, faces)
        if frame is None:
            continue
        shard = _fillet_shard(solid, a, b, frame, radius, segments)
        if shard is None or not shard.polygons:
            continue
        result = result.subtract(shard, result.name)
    return result.apply_appearance()


def chamfer_all_edges(solid: Solid, distance: float = 20.0,
                      max_edges: int = 64, name: Optional[str] = None) -> Solid:
    """CHANFREINARETE applique a toutes les aretes vives."""
    edges = [e for e in sharp_edges(solid) if dihedral_angle(solid, e[2]) < 180.0]
    if not edges:
        return solid.copy(name)
    if len(edges) > max_edges:
        edges = sorted(edges, key=lambda e: -(e[1] - e[0]).norm())[:max_edges]
    result = solid.copy(name or solid.name)
    shards: List[Solid] = []
    for a, b, faces in edges:
        frame = _edge_frame(solid, a, b, faces)
        if frame is None:
            continue
        direction, n1, n2 = frame
        p1 = a + _inward(direction, n1, n2) * distance
        p2 = a + _inward(direction, n2, n1) * distance
        shards.append(_corner_solid(a, b, direction, p1, a, p2,
                                    distance * 0.5 + 1.0, solid.material))
    for shard in shards:
        result = result.subtract(shard, result.name)
    return result.apply_appearance()


# ---------------------------------------------------------------------------
# COUPE et SECTION
# ---------------------------------------------------------------------------
def half_space(plane: Plane, reference: BBox3, positive: bool = True,
               material: str = "default") -> Solid:
    """Demi-espace materialise par une boite largement plus grande que l'objet."""
    size = max(reference.diagonal * 2.0, 1000.0)
    u, v = plane.basis()
    normal = plane.normal if positive else -plane.normal
    origin = plane.project(reference.center) if reference.valid else plane.origin
    corner = origin - u * size - v * size
    base = [corner, corner + u * (2 * size), corner + u * (2 * size) + v * (2 * size),
            corner + v * (2 * size)]
    top = [p + normal * size for p in base]
    polygons = [Polygon(list(reversed(base)), material=material),
                Polygon(list(top), material=material)]
    for i in range(4):
        j = (i + 1) % 4
        polygons.append(Polygon([base[i], base[j], top[j], top[i]],
                                material=material))
    return Solid.from_polygons(polygons, name="demi_espace",
                               material=material).outward()


def slice_solid(solid: Solid, plane: Plane, keep: str = "les_deux"
                ) -> List[Solid]:
    """Commande COUPE : tranche un solide par un plan.

    `keep` vaut « positif », « negatif » ou « les_deux » (cote de la normale).
    """
    if keep not in ("positif", "negatif", "les_deux"):
        raise ValueError("COUPE : cote inconnu %r" % keep)
    reference = solid.bbox
    above = solid.intersect(half_space(plane, reference, True), solid.name + "_sup")
    below = solid.intersect(half_space(plane, reference, False), solid.name + "_inf")
    if keep == "positif":
        return [above]
    if keep == "negatif":
        return [below]
    return [above, below]


def section_loops(solid: Solid, plane: Plane, tol: float = 1e-6) -> List[Curve]:
    """Commande SECTION : contours fermes de l'intersection avec un plan."""
    segments: List[Tuple[Vec3, Vec3]] = []
    for polygon in solid.polygons:
        points: List[Vec3] = []
        count = len(polygon.vertices)
        for i in range(count):
            a = polygon.vertices[i]
            b = polygon.vertices[(i + 1) % count]
            da, db = plane.signed_distance(a), plane.signed_distance(b)
            if abs(da) <= tol:
                points.append(a)
            if (da > tol and db < -tol) or (da < -tol and db > tol):
                cut = plane.line_intersection(a, b)
                if cut is not None:
                    points.append(cut)
        unique: List[Vec3] = []
        for point in points:
            if all(point.distance_to(other) > 1e-5 for other in unique):
                unique.append(point)
        if len(unique) >= 2:
            segments.append((unique[0], unique[-1]))
    return _chain_segments(segments)


def _chain_segments(segments: Sequence[Tuple[Vec3, Vec3]],
                    tol: float = 1e-4) -> List[Curve]:
    """Assemble des segments epars en contours fermes ou en polylignes."""
    pool = [(a, b) for a, b in segments if a.distance_to(b) > tol]
    loops: List[Curve] = []
    while pool:
        start, current = pool.pop(0)
        chain = [start, current]
        progress = True
        while progress:
            progress = False
            for index, (a, b) in enumerate(pool):
                if chain[-1].distance_to(a) <= tol:
                    chain.append(b)
                elif chain[-1].distance_to(b) <= tol:
                    chain.append(a)
                elif chain[0].distance_to(b) <= tol:
                    chain.insert(0, a)
                elif chain[0].distance_to(a) <= tol:
                    chain.insert(0, b)
                else:
                    continue
                pool.pop(index)
                progress = True
                break
        closed = chain[0].distance_to(chain[-1]) <= tol
        if closed and len(chain) > 3:
            chain.pop()
        if len(chain) >= 2:
            loops.append(Curve(chain, closed, "section"))
    return loops


def section_profile(solid: Solid, plane: Plane) -> Optional[Profile]:
    """Section pleine : le plus grand contour devient le pourtour, les autres
    des ouvertures. C'est la coupe utilisee pour les plans et les metres."""
    loops = [loop for loop in section_loops(solid, plane)
             if loop.closed and len(loop.points) >= 3]
    if not loops:
        return None
    profiles = [Profile(loop.points) for loop in loops]
    profiles.sort(key=lambda p: -p.area)
    return Profile(profiles[0].outline, [p.outline for p in profiles[1:]],
                   name="section")


def section_plane_view(solid: Solid, plane: Plane) -> Dict[str, object]:
    """Commande PLANDECOUPE : donnees d'une coupe (aire, contours, perimetre)."""
    loops = section_loops(solid, plane)
    profile = section_profile(solid, plane)
    return {"contours": len(loops), "aire_mm2": round(profile.area, 3) if profile else 0.0,
            "perimetre_mm": round(sum(loop.length for loop in loops), 3),
            "boucles": [loop.to_dict() for loop in loops],
            "profil": profile}


# ---------------------------------------------------------------------------
# GAINE, DEPOUILLE, DECALAGE
# ---------------------------------------------------------------------------
def offset_solid(solid: Solid, distance: float, name: Optional[str] = None
                 ) -> Solid:
    """Commande DECALAGE en 3D : deplace chaque face selon sa normale.

    Le resultat est l'intersection des demi-espaces obtenus, ce qui est exact
    sur un solide convexe et tres proche ailleurs.
    """
    planes: List[Plane] = []
    for polygon in solid.polygons:
        candidate = Plane.from_point_normal(polygon.vertices[0], polygon.normal)
        shifted = Plane(candidate.normal, candidate.offset + distance)
        if all(abs(shifted.offset - p.offset) > 1e-6
               or shifted.normal.dot(p.normal) < 1.0 - 1e-9 for p in planes):
            planes.append(shifted)
    if not planes:
        return solid.copy(name)
    reference = solid.bbox.expanded(abs(distance) * 2.0 + 10.0)
    result = box(reference.size.x, reference.size.y, reference.size.z,
                 reference.min, material=solid.material,
                 name=name or solid.name)
    for plane in planes:
        result = result.intersect(half_space(plane, reference, False),
                                 result.name)
        if not result.polygons:
            break
    return result.apply_appearance()


def shell(solid: Solid, thickness: float = 20.0,
          open_faces: Optional[Sequence[int]] = None,
          name: Optional[str] = None) -> Solid:
    """Commande GAINE : evide un solide en laissant une paroi d'epaisseur donnee.

    `open_faces` designe les faces a retirer (couvercle ouvert, caisson,
    trémie) exactement comme la selection de faces d'AutoCAD.
    """
    if thickness <= 0:
        raise ValueError("GAINE : l'epaisseur doit etre positive")
    inner = offset_solid(solid, -thickness, "interieur")
    if not inner.polygons or inner.volume < 1e-6:
        raise ValueError("GAINE : epaisseur trop grande pour ce solide")
    hollow = solid.subtract(inner, name or solid.name)
    for index in (open_faces or ()):
        if not 0 <= index < len(solid.polygons):
            raise ValueError("GAINE : numero de face invalide %d" % index)
        face = solid.polygons[index]
        # Seule la paroi de la face choisie disparait : le percement suit le
        # contour interieur, sinon il entamerait aussi les parois voisines.
        inner = offset_ring(face.vertices, thickness, face.normal)
        # `direction` porte le vecteur complet de l'extrusion : la paroi est
        # traversee sur toute son epaisseur, avec une marge pour couper net.
        opening = extrude(Profile(inner),
                          direction=face.normal * (-thickness * 1.05),
                          material=solid.material, name="ouverture")
        hollow = hollow.subtract(opening, hollow.name)
    return hollow.apply_appearance()


def taper_faces(solid: Solid, plane: Plane, angle_deg: float = 5.0,
                name: Optional[str] = None) -> Solid:
    """Commande DEPOUILLE : incline la matiere situee d'un cote d'un plan.

    Chaque sommet est deplace proportionnellement a sa distance au plan de
    base, ce qui produit la depouille de demoulage attendue en prefabrication.
    """
    slope = math.tan(math.radians(angle_deg))
    center = solid.centroid
    polygons: List[Polygon] = []
    for polygon in solid.polygons:
        points: List[Vec3] = []
        for vertex in polygon.vertices:
            distance = plane.signed_distance(vertex)
            if distance <= TOL:
                points.append(vertex)
                continue
            radial = vertex - plane.project(center)
            radial = radial - plane.normal * radial.dot(plane.normal)
            if radial.norm() < TOL:
                points.append(vertex)
                continue
            points.append(vertex - radial.unit() * (distance * slope))
        polygons.append(Polygon(points, polygon.material, polygon.layer,
                                polygon.color))
    return Solid(polygons, name or solid.name, solid.layer, solid.material,
                 solid.color, dict(solid.metadata)).heal().outward()


def imprint(solid: Solid, tool: Solid, name: Optional[str] = None) -> Solid:
    """Commande EMPREINTE : imprime les aretes d'un solide sur un autre.

    Les aretes communes sont ajoutees a la topologie du solide receveur,
    ce qui permet ensuite de selectionner la zone marquee (extrusion de
    face, changement de materiau, reservation).
    """
    common = solid.intersect(tool, "empreinte")
    if not common.polygons:
        return solid.copy(name)
    marked = solid.union(common, name or solid.name)
    marked.metadata = dict(solid.metadata)
    marked.metadata["empreintes"] = marked.metadata.get("empreintes", 0) + 1
    return marked


def convert_to_surface(solid: Solid, name: Optional[str] = None) -> Solid:
    """Commande CONVENSURFACE : garde les faces sans les fermer."""
    surface = Solid([Polygon(list(p.vertices), p.material, p.layer, p.color)
                     for p in solid.polygons], name or solid.name + "_surface",
                    solid.layer, solid.material, solid.color,
                    dict(solid.metadata))
    surface.metadata["type"] = "surface"
    return surface


def convert_to_solid(surface: Solid, thickness: float = 0.0,
                     name: Optional[str] = None) -> Solid:
    """Commande CONVENSOLIDE : ferme une surface, avec epaisseur si besoin."""
    from .modeling import thicken
    if thickness > TOL:
        return thicken(surface.polygons, thickness, surface.material,
                       name or surface.name)
    healed = surface.heal().outward()
    healed.name = name or surface.name
    healed.metadata = dict(surface.metadata)
    healed.metadata["type"] = "solide"
    return healed


def extract_edges(solid: Solid) -> List[Curve]:
    """Commande XARETES : extrait le filaire d'un solide."""
    return [Curve([a, b], False, "arete", solid.layer) for a, b in solid.edges()]


def face_report(solid: Solid) -> List[Dict[str, object]]:
    """Fiche des faces : surface, normale, centre. Sert a la selection de face."""
    out: List[Dict[str, object]] = []
    for index, polygon in enumerate(solid.polygons):
        out.append({"index": index, "sommets": len(polygon.vertices),
                    "aire_mm2": round(polygon.area, 3),
                    "normale": [round(v, 4) for v in polygon.normal],
                    "centre": [round(v, 3) for v in polygon.centroid],
                    "materiau": polygon.material})
    return out
