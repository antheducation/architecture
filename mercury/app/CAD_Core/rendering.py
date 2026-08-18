"""Rendu (livrable #09) : export OBJ, glTF et vues vectorielles SVG.

Le rendu temps reel est assure cote client par WebGL ; le serveur produit
les formats d'echange et les vues 2D vectorielles, seuls livrables qui
partent en agence ou en impression.
"""
from __future__ import annotations

import base64
import json
import struct
from typing import Dict, List, Sequence, Tuple

from .engine_3d import Mesh
from .geometry import Vec2, bounding_box

PALETTE: Dict[str, Tuple[float, float, float]] = {
    "maconnerie": (0.85, 0.83, 0.78),
    "cloison": (0.90, 0.89, 0.86),
    "beton": (0.72, 0.72, 0.70),
    "mobilier": (0.55, 0.40, 0.28),
    "default": (0.80, 0.80, 0.80),
}


class Renderer:
    """Convertit un maillage ou un projet en formats diffusables."""

    @staticmethod
    def to_obj(mesh: Mesh, scale: float = 0.001) -> str:
        lines = ["# MERCURY CAD AI X - export OBJ", "mtllib mercury.mtl"]
        for x, y, z in mesh.vertices:
            lines.append("v %.5f %.5f %.5f" % (x * scale, z * scale, -y * scale))
        by_face: Dict[int, str] = {}
        for group in mesh.groups:
            for i in range(group.start, group.start + group.count):
                by_face[i] = group.material
        current = None
        for i, face in enumerate(mesh.faces):
            material = by_face.get(i, "default")
            if material != current:
                current = material
                lines.append("usemtl " + material)
            lines.append("f " + " ".join(str(idx + 1) for idx in face))
        return "\n".join(lines) + "\n"

    @staticmethod
    def to_mtl() -> str:
        out = ["# MERCURY CAD AI X - materiaux"]
        for name, (r, g, b) in PALETTE.items():
            out += ["newmtl " + name, "Kd %.3f %.3f %.3f" % (r, g, b),
                    "Ks 0.05 0.05 0.05", "Ns 20", "illum 2", ""]
        return "\n".join(out)

    @staticmethod
    def to_gltf(mesh: Mesh, scale: float = 0.001) -> str:
        positions: List[float] = []
        indices: List[int] = []
        for x, y, z in mesh.vertices:
            positions += [x * scale, z * scale, -y * scale]
        for face in mesh.faces:
            for k in range(1, len(face) - 1):
                indices += [face[0], face[k], face[k + 1]]
        if not positions:
            positions = [0.0, 0.0, 0.0]
            indices = [0, 0, 0]
        pos_bytes = struct.pack("<%df" % len(positions), *positions)
        idx_bytes = struct.pack("<%dI" % len(indices), *indices)
        padding = (4 - len(pos_bytes) % 4) % 4
        buffer = pos_bytes + b"\x00" * padding + idx_bytes
        uri = "data:application/octet-stream;base64," + \
            base64.b64encode(buffer).decode()
        document = {
            "asset": {"version": "2.0", "generator": "MERCURY CAD AI X"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "name": "Projet"}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                        "indices": 1}]}],
            "buffers": [{"byteLength": len(buffer), "uri": uri}],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes),
                 "target": 34962},
                {"buffer": 0, "byteOffset": len(pos_bytes) + padding,
                 "byteLength": len(idx_bytes), "target": 34963},
            ],
            "accessors": [
                {"bufferView": 0, "componentType": 5126,
                 "count": len(positions) // 3, "type": "VEC3",
                 "min": [min(positions[i::3]) for i in range(3)],
                 "max": [max(positions[i::3]) for i in range(3)]},
                {"bufferView": 1, "componentType": 5125,
                 "count": len(indices), "type": "SCALAR"},
            ],
        }
        return json.dumps(document)

    @staticmethod
    def plan_svg(project, width_px: int = 1400, margin: int = 60) -> str:
        points = [Vec2(*w.start) for w in project.walls] + \
                 [Vec2(*w.end) for w in project.walls]
        if not points:
            return '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'
        x0, y0, x1, y1 = bounding_box(points)
        span_x = max(1.0, x1 - x0)
        span_y = max(1.0, y1 - y0)
        k = (width_px - 2 * margin) / span_x
        height_px = int(span_y * k + 2 * margin)

        def sx(x: float) -> float:
            return margin + (x - x0) * k

        def sy(y: float) -> float:
            return height_px - margin - (y - y0) * k

        out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">'
               % (width_px, height_px),
               '<rect width="100%" height="100%" fill="#ffffff"/>',
               '<g stroke="#111111" stroke-width="1.4" fill="none">']
        for wall in project.walls:
            a, b = Vec2(*wall.start), Vec2(*wall.end)
            normal = (b - a).unit().perp() * (wall.thickness / 2.0)
            for p, q in ((a + normal, b + normal), (a - normal, b - normal)):
                out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                           % (sx(p.x), sy(p.y), sx(q.x), sy(q.y)))
        out.append('</g><g font-family="sans-serif" font-size="13" fill="#333"'
                   ' text-anchor="middle">')
        for room in project.rooms:
            out.append('<text x="%.1f" y="%.1f">%s</text>'
                       % (sx(room.centroid[0]), sy(room.centroid[1]), room.name))
            out.append('<text x="%.1f" y="%.1f" font-size="11">%.2f m2</text>'
                       % (sx(room.centroid[0]), sy(room.centroid[1]) + 16,
                          room.area_m2))
        out.append("</g></svg>")
        return "\n".join(out)
