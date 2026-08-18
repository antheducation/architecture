"""Algebre lineaire 3D du noyau CAO : points, vecteurs, matrices, plans.

Toutes les operations de modelisation (primitives, extrusion, revolution,
tableaux, alignements) reposent sur ce module. Il ne depend de rien : le
noyau doit rester utilisable dans un worker, une tache batch ou un test.

Convention : matrices 4x4 en ligne-majeure, transformation d'un point par
`Mat4.apply(point)`, composition par `a * b` qui applique `b` puis `a`,
comme en algebre classique.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

EPS = 1e-9
TOL = 1e-7


@dataclass(frozen=True)
class Vec3:
    """Point ou vecteur de l'espace."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, k: float) -> "Vec3":
        return Vec3(self.x * k, self.y * k, self.z * k)

    __rmul__ = __mul__

    def __truediv__(self, k: float) -> "Vec3":
        if abs(k) < EPS:
            raise ZeroDivisionError("division d'un vecteur par zero")
        return Vec3(self.x / k, self.y / k, self.z / k)

    def __neg__(self) -> "Vec3":
        return Vec3(-self.x, -self.y, -self.z)

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __getitem__(self, i: int) -> float:
        return (self.x, self.y, self.z)[i]

    def dot(self, o: "Vec3") -> float:
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: "Vec3") -> "Vec3":
        return Vec3(self.y * o.z - self.z * o.y,
                    self.z * o.x - self.x * o.z,
                    self.x * o.y - self.y * o.x)

    def norm(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def norm2(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def unit(self) -> "Vec3":
        n = self.norm()
        if n < EPS:
            return Vec3(0.0, 0.0, 0.0)
        return Vec3(self.x / n, self.y / n, self.z / n)

    def distance_to(self, o: "Vec3") -> float:
        return (self - o).norm()

    def lerp(self, o: "Vec3", t: float) -> "Vec3":
        return Vec3(self.x + (o.x - self.x) * t,
                    self.y + (o.y - self.y) * t,
                    self.z + (o.z - self.z) * t)

    def any_perpendicular(self) -> "Vec3":
        """Un vecteur unitaire quelconque orthogonal a self (self non nul)."""
        reference = Vec3(0.0, 0.0, 1.0)
        if abs(self.unit().dot(reference)) > 0.9:
            reference = Vec3(1.0, 0.0, 0.0)
        return self.cross(reference).unit()

    def angle_to(self, o: "Vec3") -> float:
        """Angle non oriente en radians entre deux vecteurs."""
        a, b = self.unit(), o.unit()
        return math.acos(max(-1.0, min(1.0, a.dot(b))))

    def rounded(self, digits: int = 6) -> Tuple[float, float, float]:
        return (round(self.x, digits), round(self.y, digits), round(self.z, digits))

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @staticmethod
    def of(value) -> "Vec3":
        """Accepte Vec3, tuple, liste ou dict et renvoie un Vec3."""
        if isinstance(value, Vec3):
            return value
        if isinstance(value, dict):
            return Vec3(float(value.get("x", 0.0)), float(value.get("y", 0.0)),
                        float(value.get("z", 0.0)))
        seq = list(value)
        while len(seq) < 3:
            seq.append(0.0)
        return Vec3(float(seq[0]), float(seq[1]), float(seq[2]))


ORIGIN = Vec3(0.0, 0.0, 0.0)
X_AXIS = Vec3(1.0, 0.0, 0.0)
Y_AXIS = Vec3(0.0, 1.0, 0.0)
Z_AXIS = Vec3(0.0, 0.0, 1.0)


class Mat4:
    """Matrice homogene 4x4, stockee en 16 flottants ligne-majeure."""

    __slots__ = ("m",)

    def __init__(self, values: Sequence[float] = None) -> None:
        if values is None:
            self.m: Tuple[float, ...] = (1.0, 0.0, 0.0, 0.0,
                                         0.0, 1.0, 0.0, 0.0,
                                         0.0, 0.0, 1.0, 0.0,
                                         0.0, 0.0, 0.0, 1.0)
        else:
            values = tuple(float(v) for v in values)
            if len(values) != 16:
                raise ValueError("une matrice 4x4 exige 16 valeurs")
            self.m = values

    # -- constructeurs -----------------------------------------------------
    @staticmethod
    def identity() -> "Mat4":
        return Mat4()

    @staticmethod
    def translation(v) -> "Mat4":
        t = Vec3.of(v)
        return Mat4((1, 0, 0, t.x, 0, 1, 0, t.y, 0, 0, 1, t.z, 0, 0, 0, 1))

    @staticmethod
    def scaling(factor, base=ORIGIN) -> "Mat4":
        """Echelle uniforme ou non, autour d'un point de base."""
        if isinstance(factor, (int, float)):
            s = Vec3(float(factor), float(factor), float(factor))
        else:
            s = Vec3.of(factor)
        base = Vec3.of(base)
        core = Mat4((s.x, 0, 0, 0, 0, s.y, 0, 0, 0, 0, s.z, 0, 0, 0, 0, 1))
        return Mat4.translation(base) * core * Mat4.translation(-base)

    @staticmethod
    def rotation(axis, angle: float, base=ORIGIN) -> "Mat4":
        """Rotation d'angle (radians) autour d'un axe passant par `base`."""
        a = Vec3.of(axis).unit()
        if a.norm() < EPS:
            raise ValueError("axe de rotation nul")
        base = Vec3.of(base)
        c, s = math.cos(angle), math.sin(angle)
        t = 1.0 - c
        x, y, z = a.x, a.y, a.z
        core = Mat4((t * x * x + c, t * x * y - s * z, t * x * z + s * y, 0,
                     t * x * y + s * z, t * y * y + c, t * y * z - s * x, 0,
                     t * x * z - s * y, t * y * z + s * x, t * z * z + c, 0,
                     0, 0, 0, 1))
        return Mat4.translation(base) * core * Mat4.translation(-base)

    @staticmethod
    def rotation_x(angle: float) -> "Mat4":
        return Mat4.rotation(X_AXIS, angle)

    @staticmethod
    def rotation_y(angle: float) -> "Mat4":
        return Mat4.rotation(Y_AXIS, angle)

    @staticmethod
    def rotation_z(angle: float) -> "Mat4":
        return Mat4.rotation(Z_AXIS, angle)

    @staticmethod
    def mirror(plane: "Plane") -> "Mat4":
        """Symetrie par rapport a un plan (commande MIROIR3D)."""
        n = plane.normal.unit()
        d = plane.offset
        x, y, z = n.x, n.y, n.z
        return Mat4((1 - 2 * x * x, -2 * x * y, -2 * x * z, 2 * d * x,
                     -2 * x * y, 1 - 2 * y * y, -2 * y * z, 2 * d * y,
                     -2 * x * z, -2 * y * z, 1 - 2 * z * z, 2 * d * z,
                     0, 0, 0, 1))

    @staticmethod
    def frame(origin, x_axis, y_axis, z_axis) -> "Mat4":
        """Matrice qui envoie le repere global sur le repere donne."""
        o, ax, ay, az = (Vec3.of(origin), Vec3.of(x_axis).unit(),
                         Vec3.of(y_axis).unit(), Vec3.of(z_axis).unit())
        return Mat4((ax.x, ay.x, az.x, o.x,
                     ax.y, ay.y, az.y, o.y,
                     ax.z, ay.z, az.z, o.z,
                     0, 0, 0, 1))

    @staticmethod
    def align(src_points: Sequence, dst_points: Sequence) -> "Mat4":
        """Aligne un triedre source sur un triedre cible (commande ALIGNER3D).

        Un, deux ou trois couples de points sont acceptes, exactement comme
        dans AutoCAD : translation pure, puis rotation, puis mise a plat.
        """
        src = [Vec3.of(p) for p in src_points]
        dst = [Vec3.of(p) for p in dst_points]
        if not src or len(src) != len(dst):
            raise ValueError("ALIGNER3D exige autant de points source que cible")
        if len(src) == 1:
            return Mat4.translation(dst[0] - src[0])

        def basis(points: List[Vec3]) -> Tuple[Vec3, Vec3, Vec3]:
            ex = (points[1] - points[0]).unit()
            if len(points) >= 3:
                temp = points[2] - points[0]
                ez = ex.cross(temp)
                if ez.norm() < TOL:
                    ez = ex.any_perpendicular()
                ez = ez.unit()
            else:
                ez = ex.any_perpendicular()
            ey = ez.cross(ex).unit()
            return ex, ey, ez

        sx, sy, sz = basis(src)
        dx, dy, dz = basis(dst)
        to_origin = Mat4.translation(-src[0])
        rotate = Mat4.frame(ORIGIN, dx, dy, dz) * Mat4.frame(ORIGIN, sx, sy, sz).transposed()
        return Mat4.translation(dst[0]) * rotate * to_origin

    # -- algebre -----------------------------------------------------------
    def __mul__(self, other):
        if isinstance(other, Mat4):
            a, b = self.m, other.m
            out = []
            for row in range(4):
                for col in range(4):
                    out.append(sum(a[row * 4 + k] * b[k * 4 + col]
                                   for k in range(4)))
            return Mat4(out)
        if isinstance(other, Vec3):
            return self.apply(other)
        raise TypeError("produit matriciel non supporte avec %r" % type(other))

    def __eq__(self, other) -> bool:
        return (isinstance(other, Mat4)
                and all(abs(a - b) < 1e-9 for a, b in zip(self.m, other.m)))

    def __repr__(self) -> str:
        rows = ["[%s]" % ", ".join("%.4f" % v for v in self.m[i * 4:i * 4 + 4])
                for i in range(4)]
        return "Mat4(%s)" % ", ".join(rows)

    def apply(self, point) -> Vec3:
        """Transforme un point (composante homogene w = 1)."""
        p = Vec3.of(point)
        m = self.m
        w = m[12] * p.x + m[13] * p.y + m[14] * p.z + m[15]
        if abs(w) < EPS:
            w = 1.0
        return Vec3((m[0] * p.x + m[1] * p.y + m[2] * p.z + m[3]) / w,
                    (m[4] * p.x + m[5] * p.y + m[6] * p.z + m[7]) / w,
                    (m[8] * p.x + m[9] * p.y + m[10] * p.z + m[11]) / w)

    def apply_vector(self, vector) -> Vec3:
        """Transforme une direction : la translation est ignoree."""
        v = Vec3.of(vector)
        m = self.m
        return Vec3(m[0] * v.x + m[1] * v.y + m[2] * v.z,
                    m[4] * v.x + m[5] * v.y + m[6] * v.z,
                    m[8] * v.x + m[9] * v.y + m[10] * v.z)

    def transposed(self) -> "Mat4":
        m = self.m
        return Mat4([m[i + 4 * j] for i in range(4) for j in range(4)])

    def determinant(self) -> float:
        m = self.m

        def minor(r0, r1, r2, c0, c1, c2):
            return (m[r0 * 4 + c0] * (m[r1 * 4 + c1] * m[r2 * 4 + c2]
                                      - m[r1 * 4 + c2] * m[r2 * 4 + c1])
                    - m[r0 * 4 + c1] * (m[r1 * 4 + c0] * m[r2 * 4 + c2]
                                        - m[r1 * 4 + c2] * m[r2 * 4 + c0])
                    + m[r0 * 4 + c2] * (m[r1 * 4 + c0] * m[r2 * 4 + c1]
                                        - m[r1 * 4 + c1] * m[r2 * 4 + c0]))

        return (m[0] * minor(1, 2, 3, 1, 2, 3) - m[1] * minor(1, 2, 3, 0, 2, 3)
                + m[2] * minor(1, 2, 3, 0, 1, 3) - m[3] * minor(1, 2, 3, 0, 1, 2))

    def inverse(self) -> "Mat4":
        """Inverse par Gauss-Jordan. Leve ValueError si la matrice est singuliere."""
        size = 4
        rows = [[self.m[r * 4 + c] for c in range(size)]
                + [1.0 if r == c else 0.0 for c in range(size)]
                for r in range(size)]
        for col in range(size):
            pivot = max(range(col, size), key=lambda r: abs(rows[r][col]))
            if abs(rows[pivot][col]) < 1e-12:
                raise ValueError("matrice singuliere : inversion impossible")
            rows[col], rows[pivot] = rows[pivot], rows[col]
            factor = rows[col][col]
            rows[col] = [v / factor for v in rows[col]]
            for r in range(size):
                if r == col:
                    continue
                k = rows[r][col]
                if k:
                    rows[r] = [v - k * w for v, w in zip(rows[r], rows[col])]
        return Mat4([rows[r][size + c] for r in range(size) for c in range(size)])

    def normal_matrix(self) -> "Mat4":
        """Matrice a appliquer aux normales (inverse transposee)."""
        return self.inverse().transposed()

    def is_mirroring(self) -> bool:
        """Vrai si la transformation inverse l'orientation des faces."""
        return self.determinant() < 0.0

    def to_list(self) -> List[float]:
        return list(self.m)

    def to_column_major(self) -> List[float]:
        """Format attendu par WebGL et glTF."""
        return self.transposed().to_list()


@dataclass(frozen=True)
class Plane:
    """Plan oriente : normal . p = offset."""

    normal: Vec3
    offset: float

    @staticmethod
    def from_point_normal(point, normal) -> "Plane":
        n = Vec3.of(normal).unit()
        if n.norm() < EPS:
            raise ValueError("normale de plan nulle")
        return Plane(n, n.dot(Vec3.of(point)))

    @staticmethod
    def from_points(a, b, c) -> "Plane":
        a, b, c = Vec3.of(a), Vec3.of(b), Vec3.of(c)
        n = (b - a).cross(c - a)
        if n.norm() < TOL:
            raise ValueError("trois points alignes ne definissent pas un plan")
        return Plane.from_point_normal(a, n)

    @property
    def origin(self) -> Vec3:
        return self.normal * self.offset

    def signed_distance(self, point) -> float:
        return self.normal.dot(Vec3.of(point)) - self.offset

    def project(self, point) -> Vec3:
        p = Vec3.of(point)
        return p - self.normal * self.signed_distance(p)

    def flipped(self) -> "Plane":
        return Plane(-self.normal, -self.offset)

    def basis(self) -> Tuple[Vec3, Vec3]:
        """Repere orthonorme du plan (u, v).

        Applique l'algorithme d'axe arbitraire de la norme DXF : le repere
        obtenu est celui qu'attendent AutoCAD et tous les lecteurs DXF, ce
        qui garantit qu'un cercle exporte revient au meme endroit.
        """
        n = self.normal.unit()
        if abs(n.x) < 1.0 / 64.0 and abs(n.y) < 1.0 / 64.0:
            u = Y_AXIS.cross(n).unit()
        else:
            u = Z_AXIS.cross(n).unit()
        if u.norm() < EPS:
            u = n.any_perpendicular()
        return u, n.cross(u).unit()

    def to_world(self, u: float, v: float) -> Vec3:
        bu, bv = self.basis()
        return self.origin + bu * u + bv * v

    def to_local(self, point) -> Tuple[float, float]:
        bu, bv = self.basis()
        d = Vec3.of(point) - self.origin
        return d.dot(bu), d.dot(bv)

    def line_intersection(self, a, b):
        """Point d'intersection du segment [a, b] avec le plan, sinon None."""
        a, b = Vec3.of(a), Vec3.of(b)
        da, db = self.signed_distance(a), self.signed_distance(b)
        if abs(da - db) < EPS:
            return None
        t = da / (da - db)
        if t < -TOL or t > 1.0 + TOL:
            return None
        return a.lerp(b, t)


XY_PLANE = Plane(Z_AXIS, 0.0)
XZ_PLANE = Plane(Y_AXIS, 0.0)
YZ_PLANE = Plane(X_AXIS, 0.0)


@dataclass
class BBox3:
    """Boite englobante alignee sur les axes."""

    min: Vec3 = Vec3(math.inf, math.inf, math.inf)
    max: Vec3 = Vec3(-math.inf, -math.inf, -math.inf)

    @staticmethod
    def of(points: Iterable) -> "BBox3":
        box = BBox3()
        for p in points:
            box.add(p)
        return box

    def add(self, point) -> "BBox3":
        p = Vec3.of(point)
        self.min = Vec3(min(self.min.x, p.x), min(self.min.y, p.y),
                        min(self.min.z, p.z))
        self.max = Vec3(max(self.max.x, p.x), max(self.max.y, p.y),
                        max(self.max.z, p.z))
        return self

    @property
    def valid(self) -> bool:
        return (self.min.x <= self.max.x and self.min.y <= self.max.y
                and self.min.z <= self.max.z)

    @property
    def center(self) -> Vec3:
        return (self.min + self.max) * 0.5 if self.valid else ORIGIN

    @property
    def size(self) -> Vec3:
        return self.max - self.min if self.valid else ORIGIN

    @property
    def diagonal(self) -> float:
        return self.size.norm() if self.valid else 0.0

    def expanded(self, margin: float) -> "BBox3":
        d = Vec3(margin, margin, margin)
        return BBox3(self.min - d, self.max + d)

    def intersects(self, other: "BBox3", tol: float = TOL) -> bool:
        if not (self.valid and other.valid):
            return False
        return not (self.max.x < other.min.x - tol or other.max.x < self.min.x - tol
                    or self.max.y < other.min.y - tol or other.max.y < self.min.y - tol
                    or self.max.z < other.min.z - tol or other.max.z < self.min.z - tol)

    def contains(self, point, tol: float = TOL) -> bool:
        p = Vec3.of(point)
        return (self.min.x - tol <= p.x <= self.max.x + tol
                and self.min.y - tol <= p.y <= self.max.y + tol
                and self.min.z - tol <= p.z <= self.max.z + tol)

    def to_dict(self):
        if not self.valid:
            return {"vide": True}
        return {"min": list(self.min), "max": list(self.max),
                "taille": list(self.size), "centre": list(self.center)}


def polygon_normal(points: Sequence) -> Vec3:
    """Normale d'un polygone gauche par la formule de Newell."""
    pts = [Vec3.of(p) for p in points]
    n = Vec3()
    count = len(pts)
    for i in range(count):
        a, b = pts[i], pts[(i + 1) % count]
        n = n + Vec3((a.y - b.y) * (a.z + b.z),
                     (a.z - b.z) * (a.x + b.x),
                     (a.x - b.x) * (a.y + b.y))
    return n.unit()


def polygon_area_3d(points: Sequence) -> float:
    """Aire d'un polygone plan quelconque de l'espace.

    Ecrite sans allocation : ce calcul est appele des centaines de milliers
    de fois par les operations booleennes.
    """
    count = len(points)
    if count < 3:
        return 0.0
    if not isinstance(points[0], Vec3):
        points = [Vec3.of(p) for p in points]
    sx = sy = sz = 0.0
    previous = points[-1]
    for current in points:
        sx += previous.y * current.z - previous.z * current.y
        sy += previous.z * current.x - previous.x * current.z
        sz += previous.x * current.y - previous.y * current.x
        previous = current
    return math.sqrt(sx * sx + sy * sy + sz * sz) / 2.0
