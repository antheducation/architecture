"""Noyau de conception assistee par ordinateur.

Deux couches se completent :

- la couche historique (`geometry`, `engine_2d`, `engine_3d`, `rendering`)
  qui transforme un modele BIM en plans et en maillages ;
- le noyau de modelisation 3D (`math3d`, `solid`, `primitives`, `modeling`,
  `solid_edit`, `transform3d`, `mesh_tools`) qui offre les outils volumiques
  d'un logiciel de CAO, avec son document, ses accrochages, ses annotations,
  ses vues et son interpreteur de commandes.
"""
from .documentation import DocumentGenerator
from .engine_2d import Engine2D
from .engine_3d import Engine3D
from .geometry import Vec2, Segment, polygon_area, polygon_centroid
from .math3d import BBox3, Mat4, Plane, Vec3
from .profiles import Curve, Profile
from .rendering import Renderer
from .solid import Polygon, Solid, intersect_all, subtract_all, union_all

__all__ = [
    "Vec2", "Segment", "polygon_area", "polygon_centroid",
    "Engine2D", "Engine3D", "Renderer", "DocumentGenerator",
    "Vec3", "Mat4", "Plane", "BBox3", "Profile", "Curve",
    "Solid", "Polygon", "union_all", "subtract_all", "intersect_all",
]
