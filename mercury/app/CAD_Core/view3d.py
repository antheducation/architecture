"""Vues 3D : camera, vues normalisees, styles visuels, orbite, plans de coupe.

Regroupe VUEPOINT, ORBITE3D, VUEDYN, STYLESVISUELS, ZOOM et PAN. La camera
produit les matrices de vue et de projection consommees aussi bien par le
moteur de rendu du serveur que par la visionneuse WebGL du navigateur.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .math3d import BBox3, Mat4, ORIGIN, Plane, TOL, Vec3, X_AXIS, Y_AXIS, Z_AXIS

# Vues normalisees du ruban Vue (VUEPOINT), en direction de visee.
STANDARD_VIEWS: Dict[str, Tuple[float, float, float]] = {
    "dessus": (0.0, 0.0, -1.0), "dessous": (0.0, 0.0, 1.0),
    "face": (0.0, 1.0, 0.0), "arriere": (0.0, -1.0, 0.0),
    "gauche": (1.0, 0.0, 0.0), "droite": (-1.0, 0.0, 0.0),
    "iso_sud_ouest": (1.0, 1.0, -1.0), "iso_sud_est": (-1.0, 1.0, -1.0),
    "iso_nord_est": (-1.0, -1.0, -1.0), "iso_nord_ouest": (1.0, -1.0, -1.0),
}

VISUAL_STYLES = {
    "filaire_2d": {"faces": False, "aretes": True, "ombrage": "aucun",
                   "arriere_plan": [255, 255, 255]},
    "filaire_3d": {"faces": False, "aretes": True, "ombrage": "aucun",
                   "arriere_plan": [33, 40, 48]},
    "cache": {"faces": True, "aretes": True, "ombrage": "uniforme",
              "arriere_plan": [255, 255, 255]},
    "realiste": {"faces": True, "aretes": False, "ombrage": "lisse",
                 "arriere_plan": [24, 28, 34]},
    "conceptuel": {"faces": True, "aretes": True, "ombrage": "gooch",
                   "arriere_plan": [30, 36, 44]},
    "ombre_avec_aretes": {"faces": True, "aretes": True, "ombrage": "lisse",
                          "arriere_plan": [30, 36, 44]},
    "nuances_de_gris": {"faces": True, "aretes": True, "ombrage": "gris",
                        "arriere_plan": [240, 240, 240]},
    "esquisse": {"faces": True, "aretes": True, "ombrage": "uniforme",
                 "arriere_plan": [252, 250, 244]},
    "rayons_x": {"faces": True, "aretes": True, "ombrage": "transparent",
                 "arriere_plan": [20, 24, 30]},
}


@dataclass
class Light:
    """Source lumineuse : distante (soleil), ponctuelle ou projecteur."""

    kind: str = "distante"
    direction: Vec3 = Vec3(-0.4, -0.6, -0.7)
    position: Vec3 = Vec3(0.0, 0.0, 10000.0)
    intensity: float = 1.0
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    cone_deg: float = 45.0

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.kind, "direction": list(self.direction),
                "position": list(self.position), "intensite": self.intensity,
                "couleur": list(self.color), "cone_deg": self.cone_deg}


@dataclass
class Camera:
    """Camera de la fenetre courante."""

    target: Vec3 = ORIGIN
    distance: float = 10000.0
    azimuth_deg: float = 315.0             # rotation autour de Z
    elevation_deg: float = 35.264          # isometrique par defaut
    up: Vec3 = Z_AXIS
    perspective: bool = False
    field_of_view_deg: float = 45.0
    width: int = 1600
    height: int = 900
    near: float = 1.0
    far: float = 1e7
    zoom: float = 1.0
    clip_planes: List[Plane] = field(default_factory=list)

    # -- position ----------------------------------------------------------
    @property
    def position(self) -> Vec3:
        azimuth = math.radians(self.azimuth_deg)
        elevation = math.radians(max(-89.9, min(89.9, self.elevation_deg)))
        radius = self.distance * math.cos(elevation)
        return self.target + Vec3(radius * math.cos(azimuth),
                                  radius * math.sin(azimuth),
                                  self.distance * math.sin(elevation))

    @property
    def direction(self) -> Vec3:
        return (self.target - self.position).unit()

    @property
    def aspect(self) -> float:
        return max(0.01, self.width / float(max(1, self.height)))

    def basis(self) -> Tuple[Vec3, Vec3, Vec3]:
        """Repere de la camera : droite, haut, avant."""
        forward = self.direction
        reference = self.up if abs(forward.dot(self.up)) < 0.999 else Y_AXIS
        right = forward.cross(reference).unit()
        up = right.cross(forward).unit()
        return right, up, forward

    def view_matrix(self) -> Mat4:
        right, up, forward = self.basis()
        eye = self.position
        return Mat4((right.x, right.y, right.z, -right.dot(eye),
                     up.x, up.y, up.z, -up.dot(eye),
                     -forward.x, -forward.y, -forward.z, forward.dot(eye),
                     0.0, 0.0, 0.0, 1.0))

    def projection_matrix(self) -> Mat4:
        if self.perspective:
            f = 1.0 / math.tan(math.radians(self.field_of_view_deg) / 2.0)
            depth = self.near - self.far
            return Mat4((f / self.aspect, 0, 0, 0,
                         0, f, 0, 0,
                         0, 0, (self.far + self.near) / depth,
                         2 * self.far * self.near / depth,
                         0, 0, -1, 0))
        half_height = self.distance * 0.5 / max(TOL, self.zoom)
        half_width = half_height * self.aspect
        depth = self.far - self.near
        return Mat4((1.0 / half_width, 0, 0, 0,
                     0, 1.0 / half_height, 0, 0,
                     0, 0, -2.0 / depth, -(self.far + self.near) / depth,
                     0, 0, 0, 1))

    def view_projection(self) -> Mat4:
        return self.projection_matrix() * self.view_matrix()

    def project(self, point) -> Tuple[float, float, float]:
        """Point du monde vers pixel ecran ; z est la profondeur normalisee."""
        clip = self.view_projection().apply(point)
        x = (clip.x * 0.5 + 0.5) * self.width
        y = (0.5 - clip.y * 0.5) * self.height
        return x, y, clip.z

    # -- commandes de navigation -------------------------------------------
    def orbit(self, delta_azimuth: float, delta_elevation: float) -> "Camera":
        """Commande ORBITE3D."""
        self.azimuth_deg = (self.azimuth_deg + delta_azimuth) % 360.0
        self.elevation_deg = max(-89.9, min(89.9,
                                            self.elevation_deg + delta_elevation))
        return self

    def pan(self, dx: float, dy: float) -> "Camera":
        """Commande PAN : deplacement dans le plan de l'ecran."""
        right, up, _ = self.basis()
        self.target = self.target + right * dx + up * dy
        return self

    def dolly(self, factor: float) -> "Camera":
        """Commande ZOOM : rapprochement ou eloignement."""
        if factor <= 0:
            raise ValueError("ZOOM : facteur invalide")
        self.distance = max(1.0, self.distance / factor)
        return self

    def zoom_extents(self, box: BBox3, margin: float = 1.2) -> "Camera":
        """Commande ZOOM Etendu : cadre tout le modele."""
        if not box.valid:
            return self
        self.target = box.center
        radius = max(box.diagonal * 0.5, 1.0)
        if self.perspective:
            half = math.radians(self.field_of_view_deg) / 2.0
            self.distance = radius * margin / max(1e-3, math.sin(half))
        else:
            self.distance = radius * 2.0 * margin
        self.near = max(1.0, self.distance - radius * 4.0)
        self.far = self.distance + radius * 8.0
        return self

    def set_standard_view(self, name: str) -> "Camera":
        """Commande VUEPOINT : dessus, face, gauche, isometriques."""
        if name not in STANDARD_VIEWS:
            raise ValueError("vue normalisee inconnue : %s" % name)
        direction = Vec3.of(STANDARD_VIEWS[name]).unit()
        eye = -direction
        planar = math.hypot(eye.x, eye.y)
        self.azimuth_deg = math.degrees(math.atan2(eye.y, eye.x)) % 360.0
        self.elevation_deg = math.degrees(math.atan2(eye.z, planar)) \
            if planar > TOL else (89.9 if eye.z > 0 else -89.9)
        return self

    def look_at(self, target, distance: Optional[float] = None) -> "Camera":
        self.target = Vec3.of(target)
        if distance:
            self.distance = distance
        return self

    def add_clip_plane(self, plane: Plane) -> "Camera":
        """Commande PLANDECOUPE : masque la matiere devant un plan."""
        self.clip_planes.append(plane)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"cible": list(self.target), "position": list(self.position),
                "distance": round(self.distance, 3),
                "azimut_deg": round(self.azimuth_deg, 3),
                "elevation_deg": round(self.elevation_deg, 3),
                "perspective": self.perspective,
                "champ_deg": self.field_of_view_deg,
                "largeur": self.width, "hauteur": self.height,
                "zoom": self.zoom, "plans_de_coupe": len(self.clip_planes),
                "matrice_vue": self.view_matrix().to_column_major(),
                "matrice_projection": self.projection_matrix().to_column_major()}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Camera":
        camera = Camera()
        camera.target = Vec3.of(data.get("cible", [0, 0, 0]))
        camera.distance = float(data.get("distance", 10000.0))
        camera.azimuth_deg = float(data.get("azimut_deg", 315.0))
        camera.elevation_deg = float(data.get("elevation_deg", 35.264))
        camera.perspective = bool(data.get("perspective", False))
        camera.width = int(data.get("largeur", 1600))
        camera.height = int(data.get("hauteur", 900))
        camera.zoom = float(data.get("zoom", 1.0))
        return camera


@dataclass
class Viewport:
    """Fenetre : une camera, un style visuel, des calques geles."""

    name: str = "Fenetre1"
    camera: Camera = field(default_factory=Camera)
    visual_style: str = "ombre_avec_aretes"
    frozen_layers: List[str] = field(default_factory=list)
    scale: float = 0.01
    locked: bool = False

    def set_style(self, name: str) -> "Viewport":
        """Commande STYLESVISUELS."""
        if name not in VISUAL_STYLES:
            raise ValueError("style visuel inconnu : %s" % name)
        self.visual_style = name
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"nom": self.name, "camera": self.camera.to_dict(),
                "style": self.visual_style, "style_detail":
                    VISUAL_STYLES[self.visual_style],
                "calques_geles": list(self.frozen_layers),
                "echelle": self.scale, "verrouillee": self.locked}


DEFAULT_LIGHTS = [
    Light("distante", Vec3(-0.4, -0.5, -0.75), intensity=0.9),
    Light("distante", Vec3(0.6, 0.3, -0.4), intensity=0.35,
          color=(0.85, 0.9, 1.0)),
]
