"""Point d'entree du noyau CAO en ligne de commande.

    python -m CAD_Core.main demo          genere un plan et affiche le resume
    python -m CAD_Core.main export --ifc  ecrit projet.ifc dans le repertoire
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AI_Engine.generative_design import GenerativeDesigner, build_program
from BIM_Engine.ifc_handler import IFCHandler
from CAD_Core.documentation import DocumentGenerator
from CAD_Core.engine_3d import Engine3D
from CAD_Core.rendering import Renderer
from Estimating.cost_ai import CostEstimator
from Estimating.takeoff import QuantityTakeoff
from Sustainability.carbon import CarbonAnalyzer
from Sustainability.energy import EnergySimulator


def build_demo(typology: str = "maison", surface: float = 110.0,
               bedrooms: int = 3, seed: int = 7):
    """Genere un projet de demonstration complet."""
    program = build_program(typology, surface, bedrooms)
    return GenerativeDesigner().generate(program, variants=2,
                                         iterations=1500, seed=seed)[0], program


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Noyau CAO MERCURY")
    parser.add_argument("commande", choices=["demo", "export"], nargs="?",
                        default="demo")
    parser.add_argument("--typologie", default="maison")
    parser.add_argument("--surface", type=float, default=110.0)
    parser.add_argument("--chambres", type=int, default=3)
    parser.add_argument("--ifc", action="store_true", help="ecrit projet.ifc")
    parser.add_argument("--obj", action="store_true", help="ecrit projet.obj")
    args = parser.parse_args(argv)

    project, program = build_demo(args.typologie, args.surface, args.chambres)
    report = DocumentGenerator().project_report(project)
    estimate = CostEstimator().estimate(project)
    carbon = CarbonAnalyzer().analyze(project)
    energy = EnergySimulator().simulate(project)

    print("Programme  :", program.describe())
    print("Rapport    :", json.dumps(report, ensure_ascii=False))
    print("Devis      : %.0f EUR HT (%.0f EUR/m2)"
          % (estimate["total_ht"], estimate["ratio_eur_m2"]))
    print("Carbone    : %.1f t CO2e, etiquette %s"
          % (carbon["total_t_co2e"], carbon["etiquette"]))
    print("Energie    : %.1f kWh/m2/an, etiquette %s"
          % (energy["kwh_m2_an"], energy["etiquette"]))
    print("Maillage   :", Engine3D().build(project).stats)

    if args.commande == "export" or args.ifc:
        with open("projet.ifc", "w", encoding="utf-8") as handle:
            handle.write(IFCHandler().export(project))
        print("Ecrit      : projet.ifc")
    if args.obj:
        mesh = Engine3D().build(project)
        with open("projet.obj", "w", encoding="utf-8") as handle:
            handle.write(Renderer().to_obj(mesh))
        print("Ecrit      : projet.obj")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
