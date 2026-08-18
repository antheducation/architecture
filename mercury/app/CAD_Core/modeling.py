"""Outils volumiques a partir d'un profil : le coeur du ruban 3D.

EXTRUSION, REVOLUTION, BALAYAGE, LISSAGE, APPUYERTIRER, EPAISSIR, ainsi que
les surfaces reglees, tabulees, de Coons et de revolution. Chaque fonction
prend un ou plusieurs `Profile` et rend un `Solid` ferme (ou une surface
ouverte pour les fonctions de la famille SURFACE*).
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .math3d import (EPS, Mat4, ORIGIN, Plane, TOL, Vec3, X_AXIS, Y_AXIS,
                     Z_AXIS, polygon_normal)
from .profiles import Curve, DEFAULT_SEGMENTS, Profile
from .solid import Polygon, Solid


def _cap(profile: Profile, flip: bool, material: str) -> List[Polygon]:
    """Face pleine d'un profil, ouvertures comprises."""
    polygons: List[Polygon] = []
    for triangle in profile.triangulate():
        points = list(triangle)
        if flip:
            points.reverse()
        polygons.append(Polygon(points, material=material))
    return polygons


def _cap_oriented(rings: Sequence[Sequence[Vec3]], normal: Vec3,
                  material: str) -> List[Polygon]:
    """Face pleine dont la normale suit exactement la direction demandee."""
    profile = Profile(list(rings[0]), [list(r) for r in rings[1:]])
    return _cap(profile.oriented(normal), False, material)


def _ring_walls(bottom: Sequence[Vec3], top: Sequence[Vec3], material: str,
                outward: bool) -> List[Polygon]:
    """Bande laterale entre deux anneaux de meme longueur."""
    polygons: List[Polygon] = []
    count = len(bottom)
    for i in range(count):
        j = (i + 1) % count
        quad = [bottom[i], bottom[j], top[j], top[i]]
        if not outward:
            quad.reverse()
        polygons.append(Polygon(quad, material=material))
    return polygons


def offset_ring(points: Sequence[Vec3], distance: float,
                normal: Optional[Vec3] = None) -> List[Vec3]:
    """Decale un contour ferme dans son plan (depouille, coque, OFFSET)."""
    pts = [Vec3.of(p) for p in points]
    if abs(distance) < TOL or len(pts) < 3:
        return list(pts)
    n = Vec3.of(normal) if normal is not None else polygon_normal(pts)
    out: List[Vec3] = []
    count = len(pts)
    for i in range(count):
        previous = pts[(i - 1) % count]
        current = pts[i]
        following = pts[(i + 1) % count]
        d1 = (current - previous).unit()
        d2 = (following - current).unit()
        n1 = n.cross(d1).unit()
        n2 = n.cross(d2).unit()
        bisector = (n1 + n2)
        if bisector.norm() < 1e-6:
            bisector = n1
        bisector = bisector.unit()
        scale = max(0.2, bisector.dot(n1))
        out.append(current + bisector * (distance / scale))
    return out


def extrude(profile: Profile, height: float = 1000.0, direction=None,
            taper: float = 0.0, path: Optional[Curve] = None,
            material: str = "default", name: str = "extrusion") -> Solid:
    """Commande EXTRUSION : hauteur, direction, depouille ou trajectoire.

    - `height` seul : extrusion droite selon la normale du profil.
    - `direction` : vecteur complet de l'extrusion (option Direction) ;
      il remplace `height`, sa longueur donne la hauteur.
    - `taper` : angle de depouille en degres (option Angle d'extrusion).
    - `path` : extrusion le long d'une trajectoire (option Trajectoire).
    """
    if path is not None:
        return sweep(profile, path, material=material, name=name)
    if len(profile.outline) < 3:
        raise ValueError("EXTRUSION : le profil doit avoir au moins 3 sommets")
    normal = profile.normal
    if direction is not None:
        vector = Vec3.of(direction)
        if vector.norm() < TOL:
            raise ValueError("EXTRUSION : direction nulle")
    else:
        if abs(height) < TOL:
            raise ValueError("EXTRUSION : hauteur nulle")
        vector = normal * height
    reference = normal if vector.dot(normal) > 0 else -normal
    # Le contour est oriente dans le sens direct vu depuis la direction
    # d'extrusion : les murs lateraux en heritent une normale sortante, et
    # les ouvertures, deja retournees, percent correctement le volume.
    source = profile.oriented(reference)
    inset = 0.0
    if abs(taper) > 1e-9:
        inset = vector.norm() * math.tan(math.radians(taper))

    polygons: List[Polygon] = _cap_oriented(source.rings(), -reference, material)
    top_rings: List[List[Vec3]] = []
    for ring_index, ring in enumerate(source.rings()):
        ring_normal = reference if ring_index == 0 else -reference
        shifted = offset_ring(ring, inset, ring_normal) if abs(inset) > TOL \
            else list(ring)
        top = [p + vector for p in shifted]
        top_rings.append(top)
        polygons.extend(_ring_walls(ring, top, material, outward=True))
    polygons.extend(_cap_oriented(top_rings, reference, material))
    solid = Solid.from_polygons(polygons, name=name, material=material)
    return solid.heal().outward().apply_appearance()


def revolve(profile: Profile, axis_point=ORIGIN, axis_direction=Y_AXIS,
            angle: float = 2 * math.pi, segments: int = DEFAULT_SEGMENTS,
            material: str = "default", name: str = "revolution") -> Solid:
    """Commande REVOLUTION : profil tourne autour d'un axe, total ou partiel."""
    if len(profile.outline) < 3:
        raise ValueError("REVOLUTION : le profil doit avoir au moins 3 sommets")
    axis = Vec3.of(axis_direction).unit()
    if axis.norm() < TOL:
        raise ValueError("REVOLUTION : axe nul")
    base = Vec3.of(axis_point)
    full = abs(abs(angle) - 2 * math.pi) < 1e-6
    steps = max(3, int(math.ceil(abs(angle) / (2 * math.pi) * segments)))
    source = profile.oriented()
    rings: List[List[List[Vec3]]] = []
    for step in range(steps + 1):
        rotation = Mat4.rotation(axis, angle * step / float(steps), base)
        rings.append([[rotation.apply(p) for p in ring]
                      for ring in source.rings()])

    polygons: List[Polygon] = []
    for step in range(steps):
        current, following = rings[step], rings[step + 1]
        for ring_index in range(len(current)):
            polygons.extend(_ring_walls_open(current[ring_index],
                                             following[ring_index],
                                             material, True))
    if not full:
        # La normale sortante d'une face de coupe est l'oppose du deplacement
        # de la matiere : c'est ce qui ferme proprement une revolution
        # partielle (option Angle de revolution).
        def motion(rings_at_step) -> Vec3:
            centroid = Vec3()
            points = rings_at_step[0]
            for point in points:
                centroid = centroid + point
            centroid = centroid / float(len(points))
            radial = centroid - base
            radial = radial - axis * radial.dot(axis)
            direction = axis.cross(radial)
            if direction.norm() < TOL:
                direction = axis.any_perpendicular()
            return direction.unit() * (1.0 if angle >= 0 else -1.0)

        polygons.extend(_cap_oriented(rings[0], -motion(rings[0]), material))
        polygons.extend(_cap_oriented(rings[steps], motion(rings[steps]),
                                      material))
    solid = Solid.from_polygons(polygons, name=name, material=material)
    return solid.heal().outward().apply_appearance()


def _ring_walls_open(bottom: Sequence[Vec3], top: Sequence[Vec3], material: str,
                     outward: bool) -> List[Polygon]:
    """Bande entre deux anneaux fermes, faces degenerees ecartees."""
    polygons: List[Polygon] = []
    count = len(bottom)
    for i in range(count):
        j = (i + 1) % count
        quad = [bottom[i], bottom[j], top[j], top[i]]
        if not outward:
            quad.reverse()
        polygon = Polygon(quad, material=material)
        if not polygon.is_degenerate(1e-9):
            polygons.append(polygon)
    return polygons


def sweep(profile: Profile, path: Curve, twist: float = 0.0,
          scale: float = 1.0, align: bool = True, material: str = "default",
          name: str = "balayage") -> Solid:
    """Commande BALAYAGE : profil deplace le long d'une trajectoire.

    Le repere est transporte parallelement le long du chemin : le profil ne
    vrille pas de lui-meme, exactement comme l'option Torsion=0 d'AutoCAD.
    """
    if len(path.points) < 2:
        raise ValueError("BALAYAGE : la trajectoire doit avoir 2 points au moins")
    working = path
    if abs(twist) > 1e-6 or abs(scale - 1.0) > 1e-6:
        # Une torsion ou une mise a l'echelle progressive doit etre decrite
        # par assez de sections, sinon le solide obtenu est un prisme vrille
        # en une seule marche au lieu d'une helice reguliere.
        needed = max(len(path.points), int(abs(twist) / 5.0) + 2, 8)
        working = path.resampled(needed)
        working.closed = path.closed
    points = list(working.points)
    if working.closed and len(points) > 2:
        points = points + [points[0]]
    if len(profile.outline) < 3:
        raise ValueError("BALAYAGE : le profil doit avoir au moins 3 sommets")

    source = profile.oriented()
    origin = source.centroid
    normal = source.normal
    tangents = Curve(points).tangents()

    # Repere initial aligne sur la premiere tangente, puis transport parallele.
    frames: List[Tuple[Vec3, Vec3, Vec3]] = []
    reference = tangents[0]
    up = reference.any_perpendicular()
    for index, tangent in enumerate(tangents):
        if index > 0:
            previous = tangents[index - 1]
            axis = previous.cross(tangent)
            if axis.norm() > 1e-9:
                up = Mat4.rotation(axis, previous.angle_to(tangent)).apply_vector(up)
        side = tangent.cross(up).unit()
        frames.append((tangent, up.unit(), side))


    rings: List[List[List[Vec3]]] = []
    total = float(len(points) - 1)
    for index, point in enumerate(points):
        tangent, up, side = frames[index]
        t = index / total if total else 0.0
        # (up, side, tangent) forme un triedre direct : un repere indirect
        # retournerait silencieusement l'enroulement des sections et donc
        # l'orientation des faces du balayage.
        matrix = Mat4.frame(point, up, side, tangent)
        if align:
            base = Mat4.frame(origin, *_profile_frame(source, normal)).inverse()
        else:
            base = Mat4.translation(-origin)
        factor = 1.0 + (scale - 1.0) * t
        transform = matrix * Mat4.scaling(factor) * \
            Mat4.rotation(Z_AXIS, math.radians(twist) * t) * base
        rings.append([[transform.apply(p) for p in ring] for ring in source.rings()])

    polygons: List[Polygon] = []
    for index in range(len(rings) - 1):
        for ring_index in range(len(rings[index])):
            polygons.extend(_ring_walls_open(rings[index][ring_index],
                                             rings[index + 1][ring_index],
                                             material, ring_index == 0))
    if not working.closed:
        polygons.extend(_cap_oriented(rings[0], -tangents[0], material))
        polygons.extend(_cap_oriented(rings[-1], tangents[-1], material))
    solid = Solid.from_polygons(polygons, name=name, material=material)
    return solid.heal().outward().apply_appearance()


def _profile_frame(profile: Profile, normal: Vec3) -> Tuple[Vec3, Vec3, Vec3]:
    plane = Plane.from_point_normal(profile.centroid, normal)
    u, v = plane.basis()
    return u, v, normal


def loft(profiles: Sequence[Profile], ruled: bool = True, closed: bool = False,
         smooth_levels: int = 0, material: str = "default",
         name: str = "lissage") -> Solid:
    """Commande LISSAGE : transition entre plusieurs sections.

    `ruled` produit des faces reglees entre sections consecutives ; sinon
    les sections sont interpolees par une spline pour adoucir la surface.
    """
    sections = [p.oriented() for p in profiles if len(p.outline) >= 3]
    if len(sections) < 2:
        raise ValueError("LISSAGE : au moins deux sections sont necessaires")
    resolution = max(len(s.outline) for s in sections)
    rings = [_resample_ring(s.outline, resolution) for s in sections]
    rings = _align_rings(rings)
    if not ruled:
        rings = _interpolate_rings(rings, max(2, smooth_levels or 4))

    polygons: List[Polygon] = []
    for index in range(len(rings) - 1):
        polygons.extend(_ring_walls_open(rings[index], rings[index + 1],
                                         material, True))
    if closed:
        polygons.extend(_ring_walls_open(rings[-1], rings[0], material, True))
    else:
        direction = (rings[-1][0] - rings[0][0])
        axis_hint = polygon_normal(rings[0])
        if axis_hint.dot(direction) < 0:
            axis_hint = -axis_hint
        polygons.extend(_cap_oriented([rings[0]], -axis_hint, material))
        polygons.extend(_cap_oriented([rings[-1]], axis_hint, material))
    solid = Solid.from_polygons(polygons, name=name, material=material)
    return solid.heal().outward().apply_appearance()


def _resample_ring(points: Sequence[Vec3], count: int) -> List[Vec3]:
    curve = Curve(list(points), True)
    resampled = curve.resampled(count + 1).points
    return resampled[:count]


def _align_rings(rings: List[List[Vec3]]) -> List[List[Vec3]]:
    """Fait tourner chaque anneau pour minimiser la torsion du lissage."""
    aligned = [rings[0]]
    for ring in rings[1:]:
        previous = aligned[-1]
        best_shift, best_cost = 0, None
        for shift in range(len(ring)):
            cost = sum(previous[i].distance_to(ring[(i + shift) % len(ring)])
                       for i in range(0, len(ring), max(1, len(ring) // 12)))
            if best_cost is None or cost < best_cost:
                best_cost, best_shift = cost, shift
        aligned.append(ring[best_shift:] + ring[:best_shift])
    return aligned


def _interpolate_rings(rings: List[List[Vec3]], density: int) -> List[List[Vec3]]:
    """Insere des anneaux intermediaires par spline de Catmull-Rom."""
    if len(rings) < 3:
        return rings
    count = len(rings[0])
    out: List[List[Vec3]] = []
    for index in range(len(rings) - 1):
        for step in range(density):
            t = step / float(density)
            ring: List[Vec3] = []
            for k in range(count):
                p0 = rings[max(0, index - 1)][k]
                p1 = rings[index][k]
                p2 = rings[index + 1][k]
                p3 = rings[min(len(rings) - 1, index + 2)][k]
                t2, t3 = t * t, t * t * t
                ring.append((p1 * 2.0 + (p2 - p0) * t
                             + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * t2
                             + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * t3) * 0.5)
            out.append(ring)
    out.append(rings[-1])
    return out


def presspull(profile: Profile, distance: float, material: str = "default",
              name: str = "appuyer_tirer") -> Solid:
    """Commande APPUYERTIRER : pousse ou tire une zone fermee.

    Une distance negative produit le solide a soustraire (percement), ce que
    l'appelant enchaine avec SOUSTRACTION.
    """
    if abs(distance) < TOL:
        raise ValueError("APPUYERTIRER : distance nulle")
    return extrude(profile, distance, material=material, name=name)


def thicken(polygons: Sequence[Polygon], thickness: float = 100.0,
            material: str = "default", name: str = "epaissi") -> Solid:
    """Commande EPAISSIR : donne une epaisseur a une surface pour la solidifier."""
    if abs(thickness) < TOL:
        raise ValueError("EPAISSIR : epaisseur nulle")
    faces = [p for p in polygons if not p.is_degenerate()]
    if not faces:
        raise ValueError("EPAISSIR : aucune face exploitable")
    bottom = [Polygon(list(reversed(p.vertices)), material=material) for p in faces]
    top = [Polygon([v + p.normal * thickness for v in p.vertices],
                   material=material) for p in faces]
    polygons_out: List[Polygon] = list(bottom) + list(top)
    border: dict = {}
    for polygon in faces:
        count = len(polygon.vertices)
        for i in range(count):
            a = polygon.vertices[i]
            b = polygon.vertices[(i + 1) % count]
            key = tuple(sorted([a.rounded(4), b.rounded(4)]))
            border[key] = border.get(key, 0) + 1
    for polygon in faces:
        count = len(polygon.vertices)
        offset = polygon.normal * thickness
        for i in range(count):
            a = polygon.vertices[i]
            b = polygon.vertices[(i + 1) % count]
            key = tuple(sorted([a.rounded(4), b.rounded(4)]))
            if border.get(key, 0) != 1:
                continue
            polygons_out.append(Polygon([a, b, b + offset, a + offset],
                                        material=material))
    solid = Solid.from_polygons(polygons_out, name=name, material=material)
    return solid.heal().outward().apply_appearance()


# ---------------------------------------------------------------------------
# Surfaces (famille SURF* : SURFPLAN, SURFREGLE, SURFRESEAU, SURFEXTRUSION)
# ---------------------------------------------------------------------------
def planar_surface(profile: Profile, material: str = "default",
                   name: str = "surface_plane") -> Solid:
    """Commande SURFPLAN : surface pleine posee sur un contour ferme."""
    return Solid.from_polygons(_cap(profile.oriented(), False, material),
                               name=name, material=material)


def ruled_surface(first: Curve, second: Curve, material: str = "default",
                  name: str = "surface_reglee") -> Solid:
    """Commande SURFREGLE : surface tendue entre deux courbes."""
    count = max(len(first.points), len(second.points), 2)
    a = first.resampled(count).points
    b = second.resampled(count).points
    polygons = [Polygon([a[i], a[i + 1], b[i + 1], b[i]], material=material)
                for i in range(count - 1)]
    return Solid.from_polygons([p for p in polygons if not p.is_degenerate()],
                               name=name, material=material)


def tabulated_surface(curve: Curve, direction, material: str = "default",
                      name: str = "surface_tabulee") -> Solid:
    """Commande SURFEXTRUSION : courbe extrudee selon un vecteur."""
    vector = Vec3.of(direction)
    moved = Curve([p + vector for p in curve.points], curve.closed)
    return ruled_surface(curve, moved, material, name)


def coons_surface(curves: Sequence[Curve], resolution: int = 12,
                  material: str = "default", name: str = "surface_coons"
                  ) -> Solid:
    """Commande SURFRESEAU : carreau de Coons sur quatre courbes de bord."""
    if len(curves) != 4:
        raise ValueError("SURFRESEAU : exactement quatre courbes de bord")
    c0, c1, c2, c3 = [c.resampled(resolution + 1).points for c in curves]
    # c0 : bord bas (u), c1 : bord droit (v), c2 : bord haut (u), c3 : bord gauche (v)
    grid: List[List[Vec3]] = []
    for j in range(resolution + 1):
        v = j / float(resolution)
        row: List[Vec3] = []
        for i in range(resolution + 1):
            u = i / float(resolution)
            linear_u = c0[i] * (1 - v) + c2[i] * v
            linear_v = c3[j] * (1 - u) + c1[j] * u
            bilinear = (c0[0] * (1 - u) * (1 - v) + c0[-1] * u * (1 - v)
                        + c2[0] * (1 - u) * v + c2[-1] * u * v)
            row.append(linear_u + linear_v - bilinear)
        grid.append(row)
    polygons: List[Polygon] = []
    for j in range(resolution):
        for i in range(resolution):
            polygon = Polygon([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1],
                               grid[j + 1][i]], material=material)
            if not polygon.is_degenerate():
                polygons.append(polygon)
    return Solid.from_polygons(polygons, name=name, material=material)


def revolved_surface(curve: Curve, axis_point=ORIGIN, axis_direction=Z_AXIS,
                     angle: float = 2 * math.pi, segments: int = DEFAULT_SEGMENTS,
                     material: str = "default", name: str = "surface_revolution"
                     ) -> Solid:
    """Commande SURFREVOLUTION : courbe tournee autour d'un axe."""
    axis = Vec3.of(axis_direction).unit()
    base = Vec3.of(axis_point)
    steps = max(3, int(math.ceil(abs(angle) / (2 * math.pi) * segments)))
    rings = [[Mat4.rotation(axis, angle * s / float(steps), base).apply(p)
              for p in curve.points] for s in range(steps + 1)]
    polygons: List[Polygon] = []
    for s in range(steps):
        for i in range(len(curve.points) - 1):
            polygon = Polygon([rings[s][i], rings[s][i + 1], rings[s + 1][i + 1],
                               rings[s + 1][i]], material=material)
            if not polygon.is_degenerate():
                polygons.append(polygon)
    return Solid.from_polygons(polygons, name=name, material=material)
