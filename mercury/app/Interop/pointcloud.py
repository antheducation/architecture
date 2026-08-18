"""Nuages de points et donnees de terrain : XYZ, PTS, CSV, LAS.

Les releves de geometre et les scans de chantier arrivent sous ces formats.
MERCURY les lit pour caler un projet sur le terrain naturel, en extraire un
maillage de terrain (triangulation) et comparer le construit au modele.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from CAD_Core.math3d import BBox3, Vec3
from CAD_Core.solid import Polygon, Solid


class PointCloudError(ValueError):
    """Nuage de points illisible."""


@dataclass
class PointCloud:
    """Nuage de points avec couleurs et intensites optionnelles."""

    points: List[Vec3] = field(default_factory=list)
    colors: List[Tuple[int, int, int]] = field(default_factory=list)
    intensities: List[float] = field(default_factory=list)
    name: str = "nuage"

    @property
    def bbox(self) -> BBox3:
        return BBox3.of(self.points)

    def __len__(self) -> int:
        return len(self.points)

    def decimated(self, step: int = 10) -> "PointCloud":
        """Allege le nuage : un point sur `step`, couleurs conservees."""
        step = max(1, int(step))
        return PointCloud(self.points[::step], self.colors[::step],
                          self.intensities[::step], self.name)

    def statistics(self) -> Dict[str, Any]:
        box = self.bbox
        altitudes = [p.z for p in self.points]
        return {"points": len(self.points), "boite": box.to_dict(),
                "altitude_min": round(min(altitudes), 3) if altitudes else 0.0,
                "altitude_max": round(max(altitudes), 3) if altitudes else 0.0,
                "altitude_moyenne": round(sum(altitudes) / len(altitudes), 3)
                if altitudes else 0.0,
                "couleurs": bool(self.colors), "intensites": bool(self.intensities)}

    def to_terrain(self, resolution: int = 40, name: str = "terrain") -> Solid:
        """Maillage de terrain par grille : la surface du TN pour le projet.

        Une grille regularisee est plus robuste qu'une triangulation de
        Delaunay sur des releves bruites, et suffit aux calculs de deblais
        et de remblais.
        """
        if len(self.points) < 3:
            raise PointCloudError("nuage trop pauvre pour un terrain")
        box = self.bbox
        resolution = max(2, min(200, resolution))
        step_x = max(1e-6, box.size.x / resolution)
        step_y = max(1e-6, box.size.y / resolution)
        cells: Dict[Tuple[int, int], List[float]] = {}
        for point in self.points:
            key = (int((point.x - box.min.x) / step_x),
                   int((point.y - box.min.y) / step_y))
            cells.setdefault(key, []).append(point.z)
        grid: List[List[Optional[float]]] = []
        for j in range(resolution + 1):
            row: List[Optional[float]] = []
            for i in range(resolution + 1):
                values = cells.get((i, j))
                row.append(sum(values) / len(values) if values else None)
            grid.append(row)
        # Bouchage des trous par la moyenne des voisins connus.
        default = sum(p.z for p in self.points) / len(self.points)
        for j in range(resolution + 1):
            for i in range(resolution + 1):
                if grid[j][i] is None:
                    neighbours = [grid[j + dj][i + di]
                                  for dj in (-1, 0, 1) for di in (-1, 0, 1)
                                  if 0 <= j + dj <= resolution
                                  and 0 <= i + di <= resolution
                                  and grid[j + dj][i + di] is not None]
                    grid[j][i] = (sum(neighbours) / len(neighbours)
                                  if neighbours else default)
        polygons: List[Polygon] = []
        for j in range(resolution):
            for i in range(resolution):
                p00 = Vec3(box.min.x + i * step_x, box.min.y + j * step_y,
                           grid[j][i])
                p10 = Vec3(box.min.x + (i + 1) * step_x, box.min.y + j * step_y,
                           grid[j][i + 1])
                p11 = Vec3(box.min.x + (i + 1) * step_x,
                           box.min.y + (j + 1) * step_y, grid[j + 1][i + 1])
                p01 = Vec3(box.min.x + i * step_x, box.min.y + (j + 1) * step_y,
                           grid[j + 1][i])
                polygon = Polygon([p00, p10, p11, p01], material="terre")
                if not polygon.is_degenerate():
                    polygons.append(polygon)
        return Solid.from_polygons(polygons, name=name, material="terre")


# ---------------------------------------------------------------------------
# XYZ, PTS, CSV
# ---------------------------------------------------------------------------
def read_xyz(text: str, separator: Optional[str] = None,
             name: str = "nuage") -> PointCloud:
    """Lit un fichier XYZ, PTS ou CSV de points (avec couleurs facultatives)."""
    cloud = PointCloud(name=name)
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in "#;/":
            continue
        parts = line.split(separator) if separator else line.replace(",", " ").split()
        if len(parts) < 3:
            continue
        try:
            cloud.points.append(Vec3(float(parts[0]), float(parts[1]),
                                     float(parts[2])))
        except ValueError:
            continue                          # ligne d'en-tete
        if len(parts) >= 7:
            try:
                cloud.intensities.append(float(parts[3]))
                cloud.colors.append((int(float(parts[4])), int(float(parts[5])),
                                     int(float(parts[6]))))
            except ValueError:
                pass
        elif len(parts) >= 6:
            try:
                cloud.colors.append((int(float(parts[3])), int(float(parts[4])),
                                     int(float(parts[5]))))
            except ValueError:
                pass
    if not cloud.points:
        raise PointCloudError("aucun point valide dans le fichier")
    return cloud


def write_xyz(cloud: PointCloud, separator: str = " ") -> str:
    lines: List[str] = []
    for index, point in enumerate(cloud.points):
        row = ["%.4f" % point.x, "%.4f" % point.y, "%.4f" % point.z]
        if index < len(cloud.intensities):
            row.append("%.3f" % cloud.intensities[index])
        if index < len(cloud.colors):
            row += [str(c) for c in cloud.colors[index]]
        lines.append(separator.join(row))
    return "\n".join(lines) + "\n"


def write_csv(cloud: PointCloud) -> str:
    header = "X,Y,Z"
    if cloud.colors:
        header += ",R,V,B"
    return header + "\n" + write_xyz(cloud, ",")


# ---------------------------------------------------------------------------
# LAS (LiDAR)
# ---------------------------------------------------------------------------
def read_las(data: bytes, name: str = "las") -> PointCloud:
    """Lit un LAS 1.0 a 1.4, formats de point 0 a 3 (les plus repandus)."""
    if data[:4] != b"LASF":
        raise PointCloudError("signature LAS absente")
    version = "%d.%d" % (data[24], data[25])
    offset_to_points = struct.unpack_from("<I", data, 96)[0]
    point_format = data[104] & 0x3F
    point_size = struct.unpack_from("<H", data, 105)[0]
    legacy_count = struct.unpack_from("<I", data, 107)[0]
    scale = struct.unpack_from("<3d", data, 131)
    origin = struct.unpack_from("<3d", data, 155)
    count = legacy_count
    if version >= "1.4" and len(data) > 255:
        extended = struct.unpack_from("<Q", data, 247)[0]
        if extended:
            count = extended
    if point_format > 5:
        raise PointCloudError("format de point LAS %d non gere (0 a 5 lus)"
                              % point_format)
    cloud = PointCloud(name=name)
    for index in range(count):
        base = offset_to_points + index * point_size
        if base + 12 > len(data):
            break
        x, y, z = struct.unpack_from("<3i", data, base)
        cloud.points.append(Vec3(x * scale[0] + origin[0],
                                 y * scale[1] + origin[1],
                                 z * scale[2] + origin[2]))
        if base + 14 <= len(data):
            cloud.intensities.append(
                float(struct.unpack_from("<H", data, base + 12)[0]))
        if point_format in (2, 3, 5) and base + point_size <= len(data):
            colour_offset = {2: 20, 3: 28, 5: 28}[point_format]
            if base + colour_offset + 6 <= len(data):
                r, g, b = struct.unpack_from("<3H", data, base + colour_offset)
                cloud.colors.append((r >> 8, g >> 8, b >> 8))
    if not cloud.points:
        raise PointCloudError("LAS sans point exploitable")
    return cloud


def write_las(cloud: PointCloud, scale: float = 0.001) -> bytes:
    """Ecrit un LAS 1.2, format de point 2 (coordonnees, intensite, couleur)."""
    if not cloud.points:
        raise PointCloudError("nuage vide : rien a ecrire")
    box = cloud.bbox
    point_size = 26
    header_size = 227
    header = bytearray(header_size)
    header[0:4] = b"LASF"
    struct.pack_into("<H", header, 4, 0)          # source
    struct.pack_into("<H", header, 6, 0)          # encodage global
    header[24] = 1
    header[25] = 2                                 # LAS 1.2
    header[26:58] = b"MERCURY CAD AI X".ljust(32, b"\x00")
    header[58:90] = b"MERCURY CAD AI X".ljust(32, b"\x00")
    struct.pack_into("<HH", header, 90, 1, 2026)   # jour, annee
    struct.pack_into("<H", header, 94, header_size)
    struct.pack_into("<I", header, 96, header_size)
    struct.pack_into("<I", header, 100, 0)         # nombre de VLR
    header[104] = 2
    struct.pack_into("<H", header, 105, point_size)
    struct.pack_into("<I", header, 107, len(cloud.points))
    struct.pack_into("<3d", header, 131, scale, scale, scale)
    struct.pack_into("<3d", header, 155, 0.0, 0.0, 0.0)
    struct.pack_into("<6d", header, 179, box.max.x, box.min.x, box.max.y,
                     box.min.y, box.max.z, box.min.z)

    body = bytearray()
    for index, point in enumerate(cloud.points):
        body += struct.pack("<3i", int(round(point.x / scale)),
                            int(round(point.y / scale)),
                            int(round(point.z / scale)))
        intensity = int(cloud.intensities[index]) if index < len(cloud.intensities) else 0
        body += struct.pack("<H", max(0, min(65535, intensity)))
        # Retour, drapeaux, classification, angle de balayage, donnee
        # utilisateur, identifiant de source : 6 octets, comme l'exige le
        # format de point 0 dont herite le format 2.
        body += struct.pack("<BBbBH", 1, 0, 0, 0, 0)
        color = cloud.colors[index] if index < len(cloud.colors) else (0, 0, 0)
        body += struct.pack("<3H", *(min(65535, c << 8) for c in color))
    return bytes(header) + bytes(body)


def probe_las(data: bytes) -> Dict[str, Any]:
    if data[:4] != b"LASF":
        raise PointCloudError("signature LAS absente")
    return {"format": "LAS", "version": "%d.%d" % (data[24], data[25]),
            "format_point": data[104] & 0x3F,
            "points": struct.unpack_from("<I", data, 107)[0],
            "taille_octets": len(data)}
