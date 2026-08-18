"""Interpreteur de commandes compatible AutoCAD."""
from __future__ import annotations

import math

import pytest

from CAD_Core.commands import (CommandError, CommandInterpreter, catalog,
                               groups)


@pytest.fixture()
def cli():
    return CommandInterpreter()


def test_catalogue_complet():
    commandes = catalog()
    assert len(commandes) >= 90
    noms = {c["nom"] for c in commandes}
    for attendu in ("BOITE", "EXTRUSION", "REVOLUTION", "BALAYAGE", "LISSAGE",
                    "UNION", "SOUSTRACTION", "INTERSECTION", "RACCORDARETE",
                    "CHANFREINARETE", "GAINE", "COUPE", "SECTION", "RESEAU3D",
                    "MIROIR3D", "ALIGNER3D", "HACHURES", "COTLIN", "CALQUE",
                    "SCU", "RENDU", "EXPORTER"):
        assert attendu in noms
    assert len(groups()) >= 12
    assert all(c["resume"] for c in commandes)


def test_resolution_par_alias_et_anglais():
    assert CommandInterpreter.resolve("L").name == "LIGNE"
    assert CommandInterpreter.resolve("box").name == "BOITE"
    assert CommandInterpreter.resolve("EXT").name == "EXTRUSION"
    assert CommandInterpreter.resolve("subtract").name == "SOUSTRACTION"


def test_commande_inconnue_propose_une_correction():
    with pytest.raises(CommandError) as erreur:
        CommandInterpreter.resolve("BOIT")
    assert "BOITE" in str(erreur.value)


def test_analyse_dune_ligne():
    nom, arguments = CommandInterpreter.parse(
        "BOITE longueur=1000 origine=0,0,500 centre=vrai")
    assert nom == "BOITE"
    assert arguments["longueur"] == 1000
    assert arguments["origine"] == [0, 0, 500]
    assert arguments["centre"] is True
    with pytest.raises(CommandError):
        CommandInterpreter.parse("")


def test_creation_de_primitives(cli):
    resultat = cli.execute("BOITE longueur=2000 largeur=1000 hauteur=500")
    assert resultat["handle"] in cli.document.entities
    for ligne in ("CYLINDRE rayon=300 hauteur=2000", "SPHERE rayon=400",
                  "TORE rayon=500 rayon_tube=80", "PYRAMIDE rayon=400 cotes=6",
                  "BISEAU longueur=800 largeur=400 hauteur=600"):
        assert "handle" in cli.execute(ligne)
    assert len(cli.document.entities) == 6


def test_operations_booleennes(cli):
    a = cli.execute("BOITE longueur=1000 largeur=1000 hauteur=1000")["handle"]
    b = cli.execute("BOITE longueur=500 largeur=500 hauteur=2000 "
                    "origine=250,250,-500")["handle"]
    resultat = cli.execute("SOUSTRACTION", base=a, outils=[b])
    solide = cli.document.entities[resultat["handle"]].geometry
    assert solide.volume == pytest.approx(1e9 - 500 * 500 * 1000, rel=1e-6)
    assert a not in cli.document.entities


def test_soustraction_sans_selection_est_refusee(cli):
    with pytest.raises(CommandError):
        cli.execute("SOUSTRACTION")


def test_solides_issus_dun_profil(cli):
    cli.execute("EXTRUSION", profil=[[0, 0, 0], [1000, 0, 0], [1000, 600, 0],
                                     [0, 600, 0]], hauteur=300)
    cli.execute("REVOLUTION", profil=[[500, 0, 0], [800, 0, 0], [800, 0, 400],
                                      [500, 0, 400]], angle=270)
    cli.execute("BALAYAGE", profil=[[0, 0, 0], [100, 0, 0], [100, 100, 0]],
                trajectoire=[[0, 0, 0], [0, 0, 1500]])
    cli.execute("LISSAGE", sections=[
        [[0, 0, 0], [600, 0, 0], [600, 600, 0], [0, 600, 0]],
        [[150, 150, 900], [450, 150, 900], [450, 450, 900], [150, 450, 900]]])
    assert len(cli.document.entities) == 4


def test_edition_de_solides(cli):
    handle = cli.execute("BOITE longueur=600 largeur=600 hauteur=600")["handle"]
    avant = cli.document.entities[handle].geometry.volume
    resultat = cli.execute("RACCORDARETE rayon=60 segments=8", handles=[handle])
    assert resultat["volume_mm3"] < avant
    autre = cli.execute("BOITE longueur=800 largeur=800 hauteur=800 "
                        "origine=2000,0,0")["handle"]
    creuse = cli.execute("GAINE epaisseur=50", handles=[autre])
    assert creuse["volume_mm3"] == pytest.approx(800 ** 3 - 700 ** 3, rel=1e-6)
    coupe = cli.execute("COUPE point=2400,400,400 normale=0,0,1",
                        handles=[autre])
    assert coupe["morceaux"] == 2


def test_section_et_mesures(cli):
    handle = cli.execute("BOITE longueur=500 largeur=500 hauteur=500")["handle"]
    section = cli.execute("SECTION point=250,250,250 normale=0,0,1",
                          handles=[handle])
    assert section["aire_mm2"] == pytest.approx(250000, rel=1e-6)
    assert cli.execute("MESURER type=distance",
                       points=[[0, 0, 0], [300, 400, 0]])["distance_mm"] == 500.0
    assert cli.execute("MESURER type=angle",
                       points=[[1, 0, 0], [0, 0, 0], [0, 1, 0]])["angle_deg"] \
        == pytest.approx(90.0)
    assert cli.execute("MESURER type=volume", handles=[handle])["volume_mm3"] \
        == pytest.approx(1.25e8)
    with pytest.raises(CommandError):
        cli.execute("MESURER type=poids", handles=[handle])
    assert cli.execute("VERIFSOLIDE", handles=[handle])["controle"]["ferme"]
    assert cli.execute("PROPMECA", handles=[handle])["proprietes"][0]["masse_kg"] > 0


def test_transformations(cli):
    handle = cli.execute("BOITE longueur=100 largeur=100 hauteur=100")["handle"]
    assert cli.execute("COPIER vecteur=500,0,0 copies=2",
                       handles=[handle])["copies"] == 2
    assert cli.execute("RESEAU3D colonnes=3 rangees=2 niveaux=1 pas_colonne=200 "
                       "pas_rangee=200", handles=[handle])["occurrences"] == 6
    assert cli.execute("RESEAUPOLAIRE nombre=6",
                       handles=[handle])["occurrences"] == 6
    assert cli.execute("RESEAUCHEMIN", trajectoire=[[0, 0, 0], [1000, 0, 0]],
                       nombre=4, handles=[handle])["occurrences"] == 4
    cli.execute("DEPLACER3D vecteur=0,0,100", handles=[handle])
    cli.execute("ROTATION3D axe=0,0,1 angle=45", handles=[handle])
    assert cli.execute("MIROIR3D point=0,0,0 normale=1,0,0",
                       handles=[handle])["copies"] == 1


def test_dessin_2d_et_annotation(cli):
    for ligne in ("LIGNE depart=0,0,0 arrivee=2000,0,0",
                  "CERCLE centre=1000,1000,0 rayon=400",
                  "ARC centre=0,0,0 rayon=800 depart=0 arrivee=120",
                  "RECTANG largeur=1200 profondeur=800 raccord=100",
                  "POLYGONE cotes=8 rayon=500",
                  "ELLIPSE rayon_x=900 rayon_y=400", "POINT position=1,2,3"):
        assert "handle" in cli.execute(ligne)
    assert cli.execute("COTLIN depart=0,0,0 arrivee=2000,0,0")["mesure_mm"] \
        == 2000.0
    assert cli.execute("COTANG sommet=0,0,0 premier=1000,0,0 "
                       "second=0,1000,0")["mesure_deg"] == pytest.approx(90.0)
    assert cli.execute("COTRAYON rayon=400 diametre=vrai")["texte"] == "Ø800"
    assert cli.execute("TEXTMULT texte=Plan hauteur=50")["texte"] == "Plan"
    assert cli.execute("HACHURES", profil=[[0, 0, 0], [1000, 0, 0],
                                           [1000, 800, 0], [0, 800, 0]],
                       motif="ANSI31", echelle=8)["aire_mm2"] == 800000.0
    assert cli.execute("TABLEAU", lignes=[["Lot", "Qte"], ["Beton", "12"]],
                       titre="METRE")["colonnes"] == 2


def test_organisation_et_annulation(cli):
    handle = cli.execute("BOITE longueur=100 largeur=100 hauteur=100")["handle"]
    assert cli.execute("CALQUE nom=STRUCTURE couleur=1")["courant"] == "STRUCTURE"
    assert cli.execute("BLOC nom=POTEAU", handles=[handle])["bloc"]["nom"] \
        == "POTEAU"
    assert cli.execute("INSERER nom=POTEAU position=5000,0,0")["objets"] == 1
    assert cli.execute("SCU nom=CHANTIER origine=100,200,0")["scu"]["nom"] \
        == "CHANTIER"
    assert cli.execute("PRESENTATION nom=PLANCHE format=A1")["presentation"][
        "format"] == "A1"
    assert cli.execute("SELECTIONNER tout=vrai")["objets"] >= 2
    avant = len(cli.document.entities)
    cli.execute("BOITE longueur=10 largeur=10 hauteur=10")
    assert len(cli.document.entities) == avant + 1
    assert cli.execute("ANNULER")["annule"]
    assert len(cli.document.entities) == avant
    assert cli.execute("RETABLIR")["retabli"]
    assert cli.execute("ETAT")["etat"]["objets"] >= 1


def test_aides_au_dessin(cli):
    cli.execute("BOITE longueur=1000 largeur=1000 hauteur=1000")
    assert cli.execute("ACCROBJ modes=4143")["accrochages"]["osmode"] == 4143
    accroche = cli.execute("ACCROCHER curseur=5,5,5")["accrochage"]
    assert accroche["mode"] == "extremite"
    assert cli.execute("ORTHO actif=vrai")["ortho"] is True
    assert cli.execute("RESOL actif=vrai pas=250")["pas_mm"] == 250.0


def test_vues_et_rendu(cli):
    cli.execute("BOITE longueur=1000 largeur=1000 hauteur=1000")
    assert cli.execute("VUEPOINT vue=dessus")["commande"] == "VUEPOINT"
    cli.execute("ORBITE3D azimut=25 elevation=10")
    cli.execute("ZOOM etendu=vrai")
    cli.execute("PAN dx=100 dy=50")
    assert cli.execute("STYLESVISUELS style=conceptuel")["commande"] == \
        "STYLESVISUELS"
    with pytest.raises(CommandError):
        cli.execute("STYLESVISUELS style=aquarelle")
    rendu = cli.execute("RENDU largeur=160 hauteur=120")
    assert rendu["image_png_octets"] > 100
    assert cli.execute("MASQUE largeur=160 hauteur=120")["svg_octets"] > 100
    assert "cible" in cli.execute("VUE nom=Perspective1")["vue"]


def test_exports_depuis_la_ligne_de_commande(cli):
    cli.execute("BOITE longueur=1000 largeur=1000 hauteur=1000")
    for format_cible in ("dxf", "step", "stl", "gltf", "pdf", "ifc", "json",
                         "svg", "obj"):
        resultat = cli.execute("EXPORTER format=%s" % format_cible)
        assert resultat["octets"] > 0
    assert cli.execute("FORMATS")["capacites"]["formats"] >= 25


def test_script_de_commandes(cli):
    resultats = cli.run_script(
        "BOITE longueur=100 largeur=100 hauteur=100\n"
        "CERCLE rayon=50 ; un commentaire ignore\n"
        "ETAT")
    assert [r["commande"] for r in resultats] == ["BOITE", "CERCLE", "ETAT"]
    assert len(cli.history) == 3


def test_aide_en_ligne(cli):
    assert cli.execute("AIDE commande=BOITE")["aide"]["nom"] == "BOITE"
    assert len(cli.execute("AIDE")["commandes"]) >= 90


def test_parametres_invalides(cli):
    with pytest.raises(CommandError):
        cli.execute("BOITE", parametre_inexistant=1)
    with pytest.raises(CommandError):
        cli.execute("EXTRUSION", profil=None)
    with pytest.raises(CommandError):
        cli.execute("RACCORDARETE rayon=10", handles=["INCONNU"])
