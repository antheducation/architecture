"""Support du format DWG natif d'AutoCAD.

Le DWG est un format binaire proprietaire dont la specification n'est pas
publiee : aucun logiciel tiers ne l'ecrit sans passer par une bibliotheque
dediee. MERCURY procede donc en deux temps, comme tous les outils non
Autodesk :

1. Lecture native de l'en-tete : version exacte (R12 a AutoCAD 2018-2021),
   page de codes, table des sections, image d'apercu. Cela suffit a
   identifier, trier, indexer et previsualiser un DWG sans outil externe.
2. Conversion geometrique par un moteur installe sur la machine : ODA File
   Converter, LibreDWG (dwg2dxf / dxf2dwg) ou ezdxf. Le DWG est traduit en
   DXF, puis lu par le lecteur DXF integre ; l'ecriture suit le chemin
   inverse.

Quand aucun moteur n'est disponible, l'erreur levee dit exactement quoi
installer : jamais de silence ni de resultat approximatif.
"""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from CAD_Core.document import CadDocument

from .dxf import DEFAULT_VERSION, DxfError, read_dxf, write_dxf

# Code de version stocke dans les six premiers octets d'un DWG.
DWG_VERSIONS: Dict[str, str] = {
    "AC1006": "R10", "AC1009": "R11/R12", "AC1012": "R13", "AC1014": "R14",
    "AC1015": "AutoCAD 2000-2002", "AC1018": "AutoCAD 2004-2006",
    "AC1021": "AutoCAD 2007-2009", "AC1024": "AutoCAD 2010-2012",
    "AC1027": "AutoCAD 2013-2017", "AC1032": "AutoCAD 2018-2021",
}

# Versions cibles acceptees par les convertisseurs, du plus ancien au recent.
DWG_TARGETS = ["ACAD12", "ACAD2000", "ACAD2004", "ACAD2007", "ACAD2010",
               "ACAD2013", "ACAD2018"]


class DwgError(ValueError):
    """DWG illisible, ou conversion impossible faute de moteur installe."""


# ---------------------------------------------------------------------------
# Lecture native de l'en-tete
# ---------------------------------------------------------------------------
def probe_dwg(data: bytes) -> Dict[str, Any]:
    """Identifie un DWG sans aucune dependance : version, sections, apercu."""
    if len(data) < 128:
        raise DwgError("fichier trop court pour un DWG")
    signature = data[:6].decode("ascii", "replace")
    if not signature.startswith("AC10") and not signature.startswith("AC1"):
        raise DwgError("signature DWG absente (%r)" % signature)
    release = DWG_VERSIONS.get(signature, "version inconnue")
    codepage = struct.unpack_from("<H", data, 0x13)[0] if len(data) > 0x15 else 0
    image_seeker = struct.unpack_from("<I", data, 0x0D)[0] if len(data) > 0x11 else 0
    sections = 0
    if len(data) > 0x1D:
        try:
            sections = struct.unpack_from("<I", data, 0x15)[0]
        except struct.error:
            sections = 0
    preview = _preview_offset(data, image_seeker)
    return {
        "format": "DWG", "version": signature, "release": release,
        "taille_octets": len(data), "page_de_codes": codepage,
        "sections": sections if 0 < sections < 64 else 0,
        "apercu_disponible": preview is not None,
        "lisible_nativement": False,
        "conversion": describe_backends(),
    }


def _preview_offset(data: bytes, seeker: int) -> Optional[int]:
    if not (0 < seeker < len(data) - 32):
        return None
    return seeker


def extract_preview(data: bytes) -> Optional[bytes]:
    """Extrait la vignette BMP ou PNG stockee dans le DWG, si elle existe.

    L'apercu est la seule geometrie exploitable sans convertisseur : il sert
    a alimenter la galerie de fichiers et les listes de projets.
    """
    try:
        seeker = struct.unpack_from("<I", data, 0x0D)[0]
    except struct.error:
        return None
    if not (0 < seeker < len(data) - 32):
        return None
    try:
        count = data[seeker + 16]
    except IndexError:
        return None
    for index in range(min(count, 8)):
        base = seeker + 17 + index * 9
        if base + 9 > len(data):
            break
        kind = data[base]
        start, size = struct.unpack_from("<II", data, base + 1)
        if size <= 0 or start + size > len(data):
            continue
        payload = data[start:start + size]
        if kind == 2:                        # image BMP sans en-tete de fichier
            header = b"BM" + struct.pack("<IHHI", 14 + size, 0, 0, 14 + 40 + 1024)
            return header + payload
        if kind == 3 and payload[:8] == b"\x89PNG\r\n\x1a\n":
            return payload
        if payload[:2] == b"BM":
            return payload
    return None


# ---------------------------------------------------------------------------
# Moteurs de conversion
# ---------------------------------------------------------------------------
def _which(*names: str) -> Optional[str]:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def available_backends() -> List[Dict[str, Any]]:
    """Liste les moteurs de conversion DWG detectes sur la machine."""
    backends: List[Dict[str, Any]] = []
    oda = _which("ODAFileConverter", "ODAFileConverter.exe", "TeighaFileConverter")
    if oda:
        backends.append({"nom": "ODA File Converter", "commande": oda,
                         "lecture": True, "ecriture": True,
                         "source": "https://www.opendesign.com/guestfiles/oda_file_converter"})
    dwg2dxf = _which("dwg2dxf")
    if dwg2dxf:
        backends.append({"nom": "LibreDWG dwg2dxf", "commande": dwg2dxf,
                         "lecture": True, "ecriture": bool(_which("dxf2dwg")),
                         "source": "https://www.gnu.org/software/libredwg/"})
    try:
        import ezdxf                          # noqa: F401
        from ezdxf.addons import odafc
        # ezdxf expose toujours le module odafc ; seul `is_installed` dit si
        # le convertisseur ODA est reellement present. Sans ce controle, le
        # rapport de capacites annoncerait une lecture DWG qui echouerait.
        if not hasattr(odafc, "is_installed") or odafc.is_installed():
            backends.append({"nom": "ezdxf + odafc", "commande": "python:ezdxf",
                             "lecture": True, "ecriture": True,
                             "source": "https://ezdxf.mozman.at/"})
    except Exception:
        pass
    return backends


def describe_backends() -> Dict[str, Any]:
    backends = available_backends()
    return {
        "moteurs_detectes": [b["nom"] for b in backends],
        "lecture_dwg": any(b["lecture"] for b in backends),
        "ecriture_dwg": any(b["ecriture"] for b in backends),
        "installation": (
            "Installez l'un de ces moteurs pour convertir la geometrie DWG : "
            "ODA File Converter (gratuit, Windows/Linux/macOS), "
            "LibreDWG (paquet libredwg-tools), ou "
            "pip install ezdxf[odafc]. L'identification, l'apercu et tous "
            "les autres formats fonctionnent sans eux."),
    }


def _run(command: List[str], timeout: int = 300) -> Tuple[int, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout)
        return result.returncode, (result.stdout + result.stderr)[-2000:]
    except FileNotFoundError as error:
        return 127, str(error)
    except subprocess.TimeoutExpired:
        return 124, "conversion interrompue : delai depasse"


def dwg_to_dxf(path: str, version: str = "ACAD2018") -> str:
    """Convertit un DWG en texte DXF a l'aide du premier moteur disponible."""
    if not os.path.isfile(path):
        raise DwgError("fichier introuvable : %s" % path)
    backends = available_backends()
    if not backends:
        raise DwgError(
            "aucun moteur de conversion DWG installe.\n"
            + describe_backends()["installation"])
    errors: List[str] = []
    for backend in backends:
        name = backend["nom"]
        with tempfile.TemporaryDirectory() as workspace:
            output = os.path.join(workspace, "sortie")
            os.makedirs(output, exist_ok=True)
            if name.startswith("ODA"):
                source = os.path.join(workspace, "entree")
                os.makedirs(source, exist_ok=True)
                shutil.copy(path, source)
                code, log = _run([backend["commande"], source, output,
                                  version, "DXF", "0", "1"])
            elif name.startswith("LibreDWG"):
                target = os.path.join(output, "sortie.dxf")
                code, log = _run([backend["commande"], "-o", target, path])
            else:
                try:
                    from ezdxf.addons import odafc
                    document = odafc.readfile(path)
                    target = os.path.join(output, "sortie.dxf")
                    document.saveas(target)
                    code, log = 0, ""
                except Exception as error:    # moteur present mais en echec
                    code, log = 1, str(error)
            if code == 0:
                for entry in sorted(os.listdir(output)):
                    if entry.lower().endswith(".dxf"):
                        with open(os.path.join(output, entry), "r",
                                  encoding="utf-8", errors="replace") as handle:
                            return handle.read()
                code, log = 1, "aucun DXF produit"
            errors.append("%s : %s" % (name, log.strip()[:300]))
    raise DwgError("la conversion DWG a echoue :\n  " + "\n  ".join(errors))


def dxf_to_dwg(dxf_text: str, target_path: str,
               version: str = "ACAD2018") -> str:
    """Ecrit un DWG a partir d'un DXF, via un moteur de conversion."""
    if version not in DWG_TARGETS:
        raise DwgError("version DWG cible inconnue : %s" % version)
    backends = [b for b in available_backends() if b["ecriture"]]
    if not backends:
        raise DwgError(
            "aucun moteur capable d'ecrire du DWG n'est installe.\n"
            + describe_backends()["installation"])
    errors: List[str] = []
    for backend in backends:
        name = backend["nom"]
        with tempfile.TemporaryDirectory() as workspace:
            source = os.path.join(workspace, "entree")
            output = os.path.join(workspace, "sortie")
            os.makedirs(source, exist_ok=True)
            os.makedirs(output, exist_ok=True)
            dxf_path = os.path.join(source, "dessin.dxf")
            with open(dxf_path, "w", encoding="utf-8") as handle:
                handle.write(dxf_text)
            if name.startswith("ODA"):
                code, log = _run([backend["commande"], source, output,
                                  version, "DWG", "0", "1"])
            elif name.startswith("LibreDWG"):
                produced = os.path.join(output, "dessin.dwg")
                code, log = _run([_which("dxf2dwg") or "dxf2dwg", "-o",
                                  produced, dxf_path])
            else:
                try:
                    import ezdxf
                    from ezdxf.addons import odafc
                    document = ezdxf.readfile(dxf_path)
                    odafc.export_dwg(document,
                                     os.path.join(output, "dessin.dwg"),
                                     version=version)
                    code, log = 0, ""
                except Exception as error:
                    code, log = 1, str(error)
            if code == 0:
                for entry in sorted(os.listdir(output)):
                    if entry.lower().endswith(".dwg"):
                        shutil.copy(os.path.join(output, entry), target_path)
                        return target_path
                code, log = 1, "aucun DWG produit"
            errors.append("%s : %s" % (name, log.strip()[:300]))
    raise DwgError("l'ecriture DWG a echoue :\n  " + "\n  ".join(errors))


# ---------------------------------------------------------------------------
# Interface haut niveau
# ---------------------------------------------------------------------------
def read_dwg(path: str, name: Optional[str] = None) -> CadDocument:
    """Lit un DWG et renvoie un document CAO complet."""
    return read_dxf(dwg_to_dxf(path), name or os.path.basename(path))


def write_dwg(document: CadDocument, path: str,
              version: str = "ACAD2018") -> str:
    """Ecrit un document en DWG. Le DXF equivalent est conserve a cote."""
    dxf_text = write_dxf(document, DEFAULT_VERSION)
    fallback = os.path.splitext(path)[0] + ".dxf"
    with open(fallback, "w", encoding="utf-8") as handle:
        handle.write(dxf_text)
    return dxf_to_dwg(dxf_text, path, version)


def inspect(path: str) -> Dict[str, Any]:
    """Fiche d'identite d'un DWG : ce que sait dire MERCURY sans convertisseur."""
    with open(path, "rb") as handle:
        data = handle.read(4096)
    with open(path, "rb") as handle:
        full = handle.read()
    report = probe_dwg(data)
    report["taille_octets"] = len(full)
    report["fichier"] = os.path.basename(path)
    preview = extract_preview(full)
    report["apercu_octets"] = len(preview) if preview else 0
    return report
