"""Moteur 3D : extrusion du modele BIM en maillage (livrable #07).

Chaque mur devient un prisme perce par ses baies : la portion ouverte
produit une allege sous la baie et un linteau au-dessus. La geometrie
obtenue est exploitable en rendu comme en export IFC.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from .geometry import Vec2, polygon_area

Vertex = Tuple[float, float, float]


@dataclass
class Group:
    """Regroupement de faces partageant un materiau et une entite source."""

    name: str
    material: str
    start: int
    count: int = 0
    entity_id: str = ""


@dataclass
class Mesh:
    vertices: List[Vertex] = field(default_factory=list)
    faces: List[Tuple[int, ...]] = field(default_factory=list)
    groups: List[Group] = field(default_factory=list)

    def open_group(self, name: str, material: str, entity_id: str = "") -> None:
        self.groups.append(Group(name, material, len(self.faces), 0, entity_id))

    def close_group(self) -> None:
        if self.groups:
            self.groups[-1].count = len(self.faces) - self.groups[-1].start

    def add_box(self, origin: Vec2, direction: Vec2, length: float,
                thickness: float, z0: float, z1: float) -> None:
        if length <= 0 or thickness <= 0 or z1 <= z0:
            return
        normal = direction.perp() * (thickness / 2.0)
        a = origin + normal
        b = origin - normal
        c = origin + direction * length - normal
        d = origin + direction * length + normal
        base = len(self.vertices)
        for p in (a, b, c, d):
            self.vertices.append((p.x, p.y, z0))
        for p in (a, b, c, d):
            self.vertices.append((p.x, p.y, z1))
        f = base
        self.faces.extend([
            (f + 0, f + 1, f + 2, f + 3),
            (f + 4, f + 7, f + 6, f + 5),
            (f + 0, f + 4, f + 5, f + 1),
            (f + 1, f + 5, f + 6, f + 2),
            (f + 2, f + 6, f + 7, f + 3),
            (f + 3, f + 7, f + 4, f + 0),
        ])

    def add_prism(self, outline: Sequence[Vec2], z0: float, z1: float) -> None:
        points = list(outline)
        if len(points) < 3:
            return
        if polygon_area(points) < 0:
            points.reverse()
        base = len(self.vertices)
        n = len(points)
        for p in points:
            self.vertices.append((p.x, p.y, z0))
        for p in points:
            self.vertices.append((p.x, p.y, z1))
        self.faces.append(tuple(range(base, base + n))[::-1])
        self.faces.append(tuple(range(base + n, base + 2 * n)))
        for i in range(n):
            j = (i + 1) % n
            self.faces.append((base + i, base + j, base + n + j, base + n + i))

    @property
    def stats(self) -> Dict[str, int]:
        return {"vertices": len(self.vertices), "faces": len(self.faces),
                "groups": len(self.groups)}


class Engine3D:
    """Transforme un projet BIM en maillage."""

    def build(self, project) -> Mesh:
        mesh = Mesh()
        for slab in project.slabs:
            mesh.open_group("dalle_" + slab.id, "beton", slab.id)
            mesh.add_prism([Vec2(*p) for p in slab.outline],
                           slab.z - slab.thickness, slab.z)
            mesh.close_group()
        for wall in project.walls:
            self._extrude_wall(mesh, wall)
        for item in project.furniture:
            mesh.open_group("mobilier_" + item.id, "mobilier", item.id)
            direction = Vec2(math.cos(item.rotation), math.sin(item.rotation))
            origin = Vec2(*item.position) - direction * (item.size[0] / 2.0)
            mesh.add_box(origin, direction, item.size[0], item.size[1],
                         0.0, item.size[2])
            mesh.close_group()
        return mesh

    @staticmethod
    def _extrude_wall(mesh: Mesh, wall) -> None:
        a, b = Vec2(*wall.start), Vec2(*wall.end)
        length = (b - a).norm()
        if length < 1.0:
            return
        direction = (b - a).unit()
        material = "maconnerie" if wall.exterior else "cloison"
        mesh.open_group("mur_" + wall.id, material, wall.id)

        cursor = 0.0
        for opening in sorted(wall.openings, key=lambda o: o.offset):
            x0 = max(0.0, opening.offset - opening.width / 2.0)
            x1 = min(length, opening.offset + opening.width / 2.0)
            if x0 > cursor + 1.0:
                mesh.add_box(a + direction * cursor, direction, x0 - cursor,
                             wall.thickness, 0.0, wall.height)
            cursor = max(cursor, x1)
            if opening.sill > 1.0:
                mesh.add_box(a + direction * x0, direction, x1 - x0,
                             wall.thickness, 0.0, opening.sill)
            head = min(wall.height, opening.sill + opening.height)
            if head < wall.height - 1.0:
                mesh.add_box(a + direction * x0, direction, x1 - x0,
                             wall.thickness, head, wall.height)
        if cursor < length - 1.0:
            mesh.add_box(a + direction * cursor, direction, length - cursor,
                         wall.thickness, 0.0, wall.height)
        mesh.close_group()
