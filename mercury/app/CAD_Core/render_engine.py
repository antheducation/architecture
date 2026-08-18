"""Moteur de rendu du serveur : rasteriseur avec tampon de profondeur.

Produit les images que l'interface affiche et que les dossiers impriment :
rendu ombre, rendu conceptuel, lignes cachees, filaire. Le tampon est ecrit
en PNG sans dependance externe (zlib de la bibliotheque standard).

Le rendu temps reel reste cote client en WebGL ; ce moteur sert aux exports,
aux vignettes, aux planches et aux tests automatises.
"""
from __future__ import annotations

import math
import struct
import zlib
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .math3d import Mat4, TOL, Vec3
from .mesh_tools import vertex_normals
from .solid import Solid
from .view3d import Camera, DEFAULT_LIGHTS, Light, VISUAL_STYLES

MATERIAL_COLORS: Dict[str, Tuple[int, int, int]] = {
    "default": (198, 198, 198), "maconnerie": (216, 210, 198),
    "cloison": (230, 228, 222), "beton": (183, 183, 179),
    "acier": (140, 150, 160), "bois": (168, 120, 72),
    "verre": (168, 205, 219), "isolant": (232, 205, 130),
    "mobilier": (140, 102, 71), "terre": (150, 122, 90),
    "metal": (170, 175, 182), "plastique": (200, 200, 210),
}


class Framebuffer:
    """Tampon image RGB avec tampon de profondeur."""

    __slots__ = ("width", "height", "pixels", "depth")

    def __init__(self, width: int, height: int,
                 background: Sequence[int] = (255, 255, 255)) -> None:
        if width < 1 or height < 1:
            raise ValueError("dimensions d'image invalides")
        self.width = int(width)
        self.height = int(height)
        r, g, b = (int(c) for c in background[:3])
        self.pixels = bytearray(bytes((r, g, b)) * (self.width * self.height))
        self.depth = [float("inf")] * (self.width * self.height)

    def set(self, x: int, y: int, color: Tuple[int, int, int],
            z: float = -float("inf")) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        index = y * self.width + x
        if z > self.depth[index]:
            return
        self.depth[index] = z
        offset = index * 3
        self.pixels[offset] = max(0, min(255, int(color[0])))
        self.pixels[offset + 1] = max(0, min(255, int(color[1])))
        self.pixels[offset + 2] = max(0, min(255, int(color[2])))

    def blend(self, x: int, y: int, color: Tuple[int, int, int],
              alpha: float) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        offset = (y * self.width + x) * 3
        for channel in range(3):
            current = self.pixels[offset + channel]
            self.pixels[offset + channel] = max(0, min(255, int(
                current * (1.0 - alpha) + color[channel] * alpha)))

    def get(self, x: int, y: int) -> Tuple[int, int, int]:
        offset = (y * self.width + x) * 3
        return (self.pixels[offset], self.pixels[offset + 1],
                self.pixels[offset + 2])

    def to_png(self) -> bytes:
        """Encode l'image en PNG (filtre 0, compression zlib)."""
        raw = bytearray()
        stride = self.width * 3
        for row in range(self.height):
            raw.append(0)
            raw.extend(self.pixels[row * stride:(row + 1) * stride])

        def chunk(tag: bytes, payload: bytes) -> bytes:
            return (struct.pack(">I", len(payload)) + tag + payload
                    + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                + chunk(b"IEND", b""))

    def to_ppm(self) -> bytes:
        """Format PPM binaire : utile au diagnostic et aux tests."""
        return (b"P6\n%d %d\n255\n" % (self.width, self.height)
                + bytes(self.pixels))


def material_color(name: str) -> Tuple[int, int, int]:
    return MATERIAL_COLORS.get(name, MATERIAL_COLORS["default"])


class Renderer3D:
    """Rasteriseur : projette, trie en profondeur, ombre et trace les aretes."""

    def __init__(self, lights: Optional[Sequence[Light]] = None,
                 ambient: float = 0.28) -> None:
        self.lights = list(lights) if lights else list(DEFAULT_LIGHTS)
        self.ambient = ambient

    # -- eclairage ---------------------------------------------------------
    def shade(self, normal: Vec3, base: Tuple[int, int, int], style: str,
              view_direction: Vec3) -> Tuple[int, int, int]:
        shading = VISUAL_STYLES[style]["ombrage"]
        if shading == "aucun":
            return base
        if shading == "uniforme":
            intensity = 0.55 + 0.45 * abs(normal.dot(view_direction))
            return tuple(int(c * intensity) for c in base)
        diffuse = 0.0
        tint = [0.0, 0.0, 0.0]
        for light in self.lights:
            direction = (light.direction.unit() if light.kind == "distante"
                         else (Vec3() - light.position).unit())
            factor = max(0.0, normal.dot(-direction)) * light.intensity
            diffuse += factor
            for channel in range(3):
                tint[channel] += factor * light.color[channel]
        total = self.ambient + diffuse
        if shading == "gris":
            gray = sum(base) / 3.0
            value = min(255.0, gray * total)
            return (int(value), int(value), int(value))
        if shading == "gooch":
            # Ombrage conceptuel : du bleu froid au jaune chaud, tres lisible
            # sur une maquette de conception.
            warm = (255, 214, 140)
            cool = (74, 96, 148)
            t = max(0.0, min(1.0, 0.5 * (1.0 + normal.dot(
                -self.lights[0].direction.unit()))))
            return tuple(int(cool[i] * (1 - t) + warm[i] * t * 0.6
                             + base[i] * 0.35 * t) for i in range(3))
        if shading == "transparent":
            total *= 0.65
        scale = min(1.6, total)
        return tuple(min(255, int(base[i] * scale
                                  * (0.7 + 0.3 * tint[i] / max(1e-6, diffuse or 1))))
                     for i in range(3))

    # -- rendu -------------------------------------------------------------
    def render(self, solids: Sequence[Solid], camera: Camera,
               style: str = "ombre_avec_aretes",
               background: Optional[Sequence[int]] = None,
               smooth: bool = True) -> Framebuffer:
        """Rend une liste de solides et renvoie le tampon image."""
        if style not in VISUAL_STYLES:
            raise ValueError("style visuel inconnu : %s" % style)
        settings = VISUAL_STYLES[style]
        frame = Framebuffer(camera.width, camera.height,
                            background or settings["arriere_plan"])
        matrix = camera.view_projection()
        view_direction = camera.direction
        half_width = camera.width * 0.5
        half_height = camera.height * 0.5

        def to_screen(point: Vec3) -> Tuple[float, float, float]:
            clip = matrix.apply(point)
            return ((clip.x * 0.5 + 0.5) * camera.width,
                    (0.5 - clip.y * 0.5) * camera.height, clip.z)

        if settings["faces"]:
            normals_cache: Dict[int, Dict[Tuple[float, ...], Vec3]] = {}
            for solid in solids:
                if smooth and settings["ombrage"] in ("lisse", "gooch"):
                    normals_cache[id(solid)] = vertex_normals(solid)
                for polygon in solid.polygons:
                    if self._clipped(polygon.vertices, camera):
                        continue
                    base = material_color(polygon.material)
                    normal = polygon.normal
                    smooth_normals = normals_cache.get(id(solid))
                    for triangle in polygon.triangulate():
                        self._raster_triangle(frame, triangle, to_screen, base,
                                              normal, style, view_direction,
                                              smooth_normals)
        if settings["aretes"]:
            edge_color = (30, 34, 40) if sum(settings["arriere_plan"]) > 380 \
                else (222, 226, 232)
            for solid in solids:
                for a, b in solid.edges():
                    if self._clipped((a, b), camera):
                        continue
                    self._raster_line(frame, to_screen(a), to_screen(b),
                                      edge_color, bias=1e-4)
        return frame

    @staticmethod
    def _clipped(points: Iterable[Vec3], camera: Camera) -> bool:
        if not camera.clip_planes:
            return False
        for plane in camera.clip_planes:
            if all(plane.signed_distance(p) > 0 for p in points):
                return True
        return False

    def _raster_triangle(self, frame: Framebuffer, triangle, to_screen,
                         base: Tuple[int, int, int], normal: Vec3, style: str,
                         view_direction: Vec3,
                         smooth_normals: Optional[Dict[Tuple[float, ...], Vec3]]
                         ) -> None:
        projected = [to_screen(v) for v in triangle]
        xs = [p[0] for p in projected]
        ys = [p[1] for p in projected]
        if max(xs) < 0 or min(xs) >= frame.width:
            return
        if max(ys) < 0 or min(ys) >= frame.height:
            return
        x0, x1 = max(0, int(min(xs))), min(frame.width - 1, int(max(xs)) + 1)
        y0, y1 = max(0, int(min(ys))), min(frame.height - 1, int(max(ys)) + 1)
        if x1 < x0 or y1 < y0:
            return
        ax, ay, az = projected[0]
        bx, by, bz = projected[1]
        cx, cy, cz = projected[2]
        denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(denominator) < 1e-9:
            return
        transparent = VISUAL_STYLES[style]["ombrage"] == "transparent"
        flat = self.shade(normal, base, style, view_direction)
        corner_colors = None
        if smooth_normals is not None:
            corner_colors = [
                self.shade(smooth_normals.get(v.rounded(4), normal), base,
                           style, view_direction) for v in triangle]
        for y in range(y0, y1 + 1):
            py = y + 0.5
            for x in range(x0, x1 + 1):
                px = x + 0.5
                w0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denominator
                w1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denominator
                w2 = 1.0 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                z = w0 * az + w1 * bz + w2 * cz
                if corner_colors is not None:
                    color = tuple(int(w0 * corner_colors[0][i]
                                      + w1 * corner_colors[1][i]
                                      + w2 * corner_colors[2][i])
                                  for i in range(3))
                else:
                    color = flat
                if transparent:
                    frame.blend(x, y, color, 0.45)
                else:
                    frame.set(x, y, color, z)

    @staticmethod
    def _raster_line(frame: Framebuffer, start, end,
                     color: Tuple[int, int, int], bias: float = 0.0) -> None:
        x0, y0, z0 = start
        x1, y1, z1 = end
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        if steps > 8192:
            return
        for i in range(steps + 1):
            t = i / float(steps)
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            z = z0 + (z1 - z0) * t - bias
            frame.set(x, y, color, z)

    # -- sortie vectorielle ------------------------------------------------
    def hidden_line_svg(self, solids: Sequence[Solid], camera: Camera,
                        samples: int = 12, stroke: str = "#111318",
                        width: float = 0.8) -> str:
        """Commande MASQUE : filaire debarrasse des aretes cachees.

        Chaque arete est echantillonnee et confrontee au tampon de
        profondeur du rendu plein : les portions masquees sont retirees, ce
        qui donne un trait vectoriel propre pour l'impression.
        """
        frame = self.render(solids, camera, "cache")
        matrix = camera.view_projection()

        def to_screen(point: Vec3):
            clip = matrix.apply(point)
            return ((clip.x * 0.5 + 0.5) * camera.width,
                    (0.5 - clip.y * 0.5) * camera.height, clip.z)

        def visible(x: float, y: float, z: float) -> bool:
            xi, yi = int(x), int(y)
            if not (0 <= xi < frame.width and 0 <= yi < frame.height):
                return False
            return z <= frame.depth[yi * frame.width + xi] + 2e-3

        parts: List[str] = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d">' % (camera.width, camera.height,
                                      camera.width, camera.height),
            '<rect width="100%%" height="100%%" fill="#ffffff"/>',
            '<g stroke="%s" stroke-width="%.2f" fill="none" '
            'stroke-linecap="round">' % (stroke, width)]
        for solid in solids:
            for a, b in solid.edges():
                pa, pb = to_screen(a), to_screen(b)
                run: List[Tuple[float, float]] = []
                for index in range(samples + 1):
                    t = index / float(samples)
                    x = pa[0] + (pb[0] - pa[0]) * t
                    y = pa[1] + (pb[1] - pa[1]) * t
                    z = pa[2] + (pb[2] - pa[2]) * t
                    if visible(x, y, z):
                        run.append((x, y))
                    elif len(run) >= 2:
                        parts.append('<polyline points="%s"/>' % " ".join(
                            "%.1f,%.1f" % p for p in run))
                        run = []
                    else:
                        run = []
                if len(run) >= 2:
                    parts.append('<polyline points="%s"/>' % " ".join(
                        "%.1f,%.1f" % p for p in run))
        parts.append("</g></svg>")
        return "\n".join(parts)

    def wireframe_svg(self, solids: Sequence[Solid], camera: Camera,
                      stroke: str = "#1c2430") -> str:
        """Filaire complet, aretes cachees comprises (style Filaire 3D)."""
        matrix = camera.view_projection()
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" '
                 'height="%d">' % (camera.width, camera.height),
                 '<rect width="100%%" height="100%%" fill="#ffffff"/>',
                 '<g stroke="%s" stroke-width="0.6" fill="none">' % stroke]
        for solid in solids:
            for a, b in solid.edges():
                ca, cb = matrix.apply(a), matrix.apply(b)
                parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                             % ((ca.x * 0.5 + 0.5) * camera.width,
                                (0.5 - ca.y * 0.5) * camera.height,
                                (cb.x * 0.5 + 0.5) * camera.width,
                                (0.5 - cb.y * 0.5) * camera.height))
        parts.append("</g></svg>")
        return "\n".join(parts)


def render_thumbnail(solids: Sequence[Solid], width: int = 480,
                     height: int = 320, style: str = "conceptuel") -> bytes:
    """Vignette PNG cadree automatiquement : aperçu de fichier, galerie."""
    from .math3d import BBox3
    camera = Camera(width=width, height=height)
    box = BBox3()
    for solid in solids:
        solid_box = solid.bbox
        if solid_box.valid:
            box.add(solid_box.min).add(solid_box.max)
    camera.zoom_extents(box)
    return Renderer3D().render(solids, camera, style).to_png()
