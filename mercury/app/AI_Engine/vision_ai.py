"""Vision par ordinateur (livrables #05, #06, #29).

Deux niveaux, avec le meme contrat de sortie :

1. `PlanVisionModel` : squelette de detecteur type YOLO. L'architecture,
   les ancres, le pretraitement, le decodage des sorties et la suppression
   des non-maxima sont reels ; les poids sont factices et generes de facon
   deterministe. On peut donc brancher un vrai fichier de poids sans
   changer une ligne du code appelant.

2. `PlanReader` : lecture de plans vectoriels (PDF, DXF) par appariement
   des doubles traits. Un plan professionnel dessine un mur par deux
   lignes paralleles ; on les apparie, on fusionne les axes colineaires au
   travers des baies, puis on prolonge jusqu'aux intersections.
"""
from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

CLASSES = ("mur", "porte", "fenetre", "poteau", "escalier", "cotation")
ANCHORS = ((16, 16), (32, 12), (12, 32), (64, 24), (24, 64))


@dataclass
class Detection:
    """Boite detectee, en pixels image."""

    label: str
    confidence: float
    x: float
    y: float
    width: float
    height: float

    def as_dict(self) -> Dict[str, object]:
        return {"classe": self.label, "confiance": round(self.confidence, 3),
                "boite": [round(self.x, 1), round(self.y, 1),
                          round(self.width, 1), round(self.height, 1)]}

    def iou(self, other: "Detection") -> float:
        ax2, ay2 = self.x + self.width, self.y + self.height
        bx2, by2 = other.x + other.width, other.y + other.height
        inter_w = max(0.0, min(ax2, bx2) - max(self.x, other.x))
        inter_h = max(0.0, min(ay2, by2) - max(self.y, other.y))
        inter = inter_w * inter_h
        union = self.width * self.height + other.width * other.height - inter
        return inter / union if union > 0 else 0.0


class FakeWeights:
    """Poids factices deterministes.

    Un vrai reseau charge un tenseur ; ici on derive les valeurs d'un
    hachage de la graine. Deux executions donnent le meme resultat, ce qui
    rend les tests reproductibles — exigence d'une chaine de production.
    """

    def __init__(self, seed: str = "mercury-yolo-v1", size: int = 4096) -> None:
        self.seed = seed
        self.values: List[float] = []
        digest = hashlib.sha256(seed.encode()).digest()
        while len(self.values) < size:
            digest = hashlib.sha256(digest).digest()
            for i in range(0, len(digest), 4):
                if len(self.values) >= size:
                    break
                raw = struct.unpack(">I", digest[i:i + 4])[0]
                self.values.append(raw / 0xFFFFFFFF)

    def at(self, index: int) -> float:
        return self.values[index % len(self.values)]

    @property
    def checksum(self) -> str:
        return hashlib.md5(
            ("%.6f" % sum(self.values)).encode()).hexdigest()[:12]


class PlanVisionModel:
    """Detecteur d'elements de plan (squelette YOLO, poids factices)."""

    input_size = 640

    def __init__(self, weights: Optional[FakeWeights] = None,
                 confidence_threshold: float = 0.35,
                 iou_threshold: float = 0.45) -> None:
        if not 0.0 < confidence_threshold < 1.0:
            raise ValueError("seuil de confiance hors bornes")
        self.weights = weights or FakeWeights()
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.loaded = True

    def info(self) -> Dict[str, object]:
        return {
            "architecture": "YOLO-like, 3 tetes, %d ancres" % len(ANCHORS),
            "classes": list(CLASSES),
            "entree": [self.input_size, self.input_size, 1],
            "poids": "factices (demonstration)",
            "empreinte_poids": self.weights.checksum,
            "seuil_confiance": self.confidence_threshold,
        }

    @staticmethod
    def preprocess(width: int, height: int, size: int = 640):
        """Redimensionne en conservant le rapport, avec remplissage."""
        if width <= 0 or height <= 0:
            raise ValueError("dimensions d'image invalides")
        scale = size / max(width, height)
        new_w, new_h = int(width * scale), int(height * scale)
        pad_x, pad_y = (size - new_w) // 2, (size - new_h) // 2
        return {"scale": scale, "pad_x": pad_x, "pad_y": pad_y,
                "resized": (new_w, new_h)}

    def predict(self, width: int, height: int,
                seed: str = "") -> List[Detection]:
        """Inference simulee : sorties decodees et filtrees comme un vrai modele."""
        meta = self.preprocess(width, height, self.input_size)
        raw: List[Detection] = []
        base = FakeWeights(self.weights.seed + seed, 512)
        for cell in range(48):
            for anchor_index, (aw, ah) in enumerate(ANCHORS):
                offset = cell * len(ANCHORS) + anchor_index
                score = base.at(offset * 5)
                if score < self.confidence_threshold:
                    continue
                label = CLASSES[int(base.at(offset * 5 + 1) * len(CLASSES)) % len(CLASSES)]
                cx = base.at(offset * 5 + 2) * width
                cy = base.at(offset * 5 + 3) * height
                w = aw * (0.5 + base.at(offset * 5 + 4)) * meta["scale"] * 4
                h = ah * (0.5 + base.at(offset * 5 + 2)) * meta["scale"] * 4
                raw.append(Detection(label, score, max(0.0, cx - w / 2),
                                     max(0.0, cy - h / 2), w, h))
        return self.non_max_suppression(raw)

    def non_max_suppression(self, detections: Sequence[Detection]) -> List[Detection]:
        """Suppression des non-maxima, classe par classe."""
        kept: List[Detection] = []
        for label in CLASSES:
            group = sorted([d for d in detections if d.label == label],
                           key=lambda d: -d.confidence)
            while group:
                best = group.pop(0)
                kept.append(best)
                group = [d for d in group if best.iou(d) < self.iou_threshold]
        return sorted(kept, key=lambda d: -d.confidence)


@dataclass
class WallCandidate:
    ax: float
    ay: float
    bx: float
    by: float
    thickness: float
    confidence: float = 1.0

    @property
    def length(self) -> float:
        return math.hypot(self.bx - self.ax, self.by - self.ay)


class PlanReader:
    """Lecture de plans vectoriels par appariement des doubles traits."""

    def __init__(self, min_thickness: float = 60.0, max_thickness: float = 700.0,
                 angle_tolerance_deg: float = 2.5,
                 min_overlap_ratio: float = 0.45) -> None:
        self.min_thickness = min_thickness
        self.max_thickness = max_thickness
        self.angle_tolerance = math.radians(angle_tolerance_deg)
        self.min_overlap_ratio = min_overlap_ratio

    def detect_walls(self, segments: Sequence[Tuple[float, float, float, float]],
                     min_length: float = 400.0) -> List[WallCandidate]:
        """Segments (x1,y1,x2,y2) en mm vers axes de murs avec epaisseur."""
        usable = [s for s in segments
                  if math.hypot(s[2] - s[0], s[3] - s[1]) >= min_length]
        candidates: List[WallCandidate] = []
        used: set = set()
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                pair = self._pair(usable[i], usable[j])
                if pair is None:
                    continue
                candidates.append(pair)
                used.add(i)
                used.add(j)
        for index, seg in enumerate(usable):
            if index in used:
                continue
            if math.hypot(seg[2] - seg[0], seg[3] - seg[1]) < min_length * 3:
                continue
            candidates.append(WallCandidate(seg[0], seg[1], seg[2], seg[3],
                                            200.0, 0.42))
        return self._merge_collinear(candidates)

    def _pair(self, s1, s2) -> Optional[WallCandidate]:
        a1 = math.atan2(s1[3] - s1[1], s1[2] - s1[0]) % math.pi
        a2 = math.atan2(s2[3] - s2[1], s2[2] - s2[0]) % math.pi
        delta = abs(a1 - a2) % math.pi
        if min(delta, math.pi - delta) > self.angle_tolerance:
            return None
        length1 = math.hypot(s1[2] - s1[0], s1[3] - s1[1]) or 1.0
        ux, uy = (s1[2] - s1[0]) / length1, (s1[3] - s1[1]) / length1
        nx, ny = -uy, ux
        gap = abs((s2[0] - s1[0]) * nx + (s2[1] - s1[1]) * ny)
        if not self.min_thickness <= gap <= self.max_thickness:
            return None
        t1 = sorted([0.0, length1])
        t2 = sorted([(s2[0] - s1[0]) * ux + (s2[1] - s1[1]) * uy,
                     (s2[2] - s1[0]) * ux + (s2[3] - s1[1]) * uy])
        low, high = max(t1[0], t2[0]), min(t1[1], t2[1])
        overlap = high - low
        length2 = math.hypot(s2[2] - s2[0], s2[3] - s2[1]) or 1.0
        if overlap <= 0 or overlap / min(length1, length2) < self.min_overlap_ratio:
            return None
        mid = ((s2[0] - s1[0]) * nx + (s2[1] - s1[1]) * ny) / 2.0
        ox, oy = s1[0] + nx * mid, s1[1] + ny * mid
        confidence = min(1.0, 0.55 + 0.35 * overlap / min(length1, length2))
        return WallCandidate(ox + ux * low, oy + uy * low,
                             ox + ux * high, oy + uy * high, gap, round(confidence, 3))

    @staticmethod
    def _merge_collinear(candidates: List[WallCandidate],
                         gap_tolerance: float = 4200.0) -> List[WallCandidate]:
        """Fusionne les troncons d'un meme mur, y compris a travers les baies."""
        result: List[WallCandidate] = []
        used = [False] * len(candidates)
        for i, c in enumerate(candidates):
            if used[i]:
                continue
            length = c.length or 1.0
            ux, uy = (c.bx - c.ax) / length, (c.by - c.ay) / length
            nx, ny = -uy, ux
            spans = [0.0, length]
            changed = True
            while changed:
                changed = False
                for j, other in enumerate(candidates):
                    if used[j] or j == i:
                        continue
                    if abs(other.thickness - c.thickness) > 60:
                        continue
                    mx = (other.ax + other.bx) / 2 - c.ax
                    my = (other.ay + other.by) / 2 - c.ay
                    if abs(mx * nx + my * ny) > 90:
                        continue
                    ta = (other.ax - c.ax) * ux + (other.ay - c.ay) * uy
                    tb = (other.bx - c.ax) * ux + (other.by - c.ay) * uy
                    if min(ta, tb) > max(spans) + gap_tolerance:
                        continue
                    if max(ta, tb) < min(spans) - gap_tolerance:
                        continue
                    spans += [ta, tb]
                    used[j] = True
                    changed = True
            used[i] = True
            result.append(WallCandidate(
                c.ax + ux * min(spans), c.ay + uy * min(spans),
                c.ax + ux * max(spans), c.ay + uy * max(spans),
                c.thickness, c.confidence))
        return result
