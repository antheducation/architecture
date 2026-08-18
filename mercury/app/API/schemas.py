"""Schemas d'entree et de sortie de l'API.

Pydantic est utilise s'il est present (validation stricte et documentation
OpenAPI). Sinon, des classes de repli fournissent la meme interface, ce qui
permet d'importer le module dans un environnement minimal.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
    PYDANTIC = True
except Exception:  # pragma: no cover - environnement minimal
    PYDANTIC = False

    class BaseModel:  # type: ignore
        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self) -> Dict[str, Any]:
            return self.__dict__

    def Field(default: Any = None, **_: Any) -> Any:  # type: ignore
        return default


class ProjectCreate(BaseModel):
    name: str = Field("Nouveau projet", description="Nom du projet")
    building_type: str = Field("inconnu", description="Typologie")


class GenerateRequest(BaseModel):
    typologie: str = Field("maison", description="maison, villa, bureau, restaurant")
    surface: float = Field(110.0, gt=15, lt=5000, description="Surface utile en m2")
    chambres: int = Field(3, ge=0, le=20)
    salles_de_bain: int = Field(1, ge=0, le=10)
    variantes: int = Field(3, ge=1, le=8)
    iterations: int = Field(2500, ge=300, le=20000)
    graine: int = Field(0, description="Graine : a valeur egale, resultat identique")


class WallCreate(BaseModel):
    start: List[float] = Field([0.0, 0.0])
    end: List[float] = Field([4000.0, 0.0])
    thickness: float = Field(200.0, gt=0)
    height: float = Field(2700.0, gt=0)
    exterior: bool = Field(False)


class OpeningCreate(BaseModel):
    wall_id: str
    type: str = Field("porte")
    offset: float = Field(1000.0, ge=0)
    width: float = Field(900.0, gt=0)
    height: float = Field(2100.0, gt=0)
    sill: float = Field(0.0, ge=0)


class CommandRequest(BaseModel):
    message: str = Field(..., description="Demande en langage naturel")


class SensorCreate(BaseModel):
    id: str
    grandeur: str = Field("temperature")
    projet: str
    piece: Optional[str] = None
    nom: str = ""


class ReadingBatch(BaseModel):
    mesures: List[Dict[str, Any]] = Field(default_factory=list)


class EnergyQuery(BaseModel):
    isolation: str = Field("neuf")
    climat: str = Field("oceanique")
