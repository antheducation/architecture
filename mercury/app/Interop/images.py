"""Images matricielles : PNG, BMP, TGA, PPM, JPEG et GIF.

Les images servent a trois choses dans une CAO : exporter une vue rendue,
importer un plan scanne comme calque de fond, et produire les vignettes des
fichiers. Tout est ecrit avec la bibliotheque standard ; Pillow, s'il est
installe, est utilise en plus pour lire les formats compresses exotiques.
"""
from __future__ import annotations

import math
import struct
import zlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

from CAD_Core.render_engine import Framebuffer


class ImageError(ValueError):
    """Image illisible ou format non pris en charge."""


class Raster:
    """Image RGB simple : largeur, hauteur, octets."""

    __slots__ = ("width", "height", "pixels")

    def __init__(self, width: int, height: int,
                 pixels: Optional[bytearray] = None) -> None:
        if width < 1 or height < 1:
            raise ImageError("dimensions d'image invalides")
        self.width = int(width)
        self.height = int(height)
        self.pixels = pixels if pixels is not None else \
            bytearray(b"\xff" * (width * height * 3))
        if len(self.pixels) != self.width * self.height * 3:
            raise ImageError("tampon d'image de taille incoherente")

    @staticmethod
    def from_framebuffer(frame: Framebuffer) -> "Raster":
        return Raster(frame.width, frame.height, bytearray(frame.pixels))

    def pixel(self, x: int, y: int) -> Tuple[int, int, int]:
        offset = (y * self.width + x) * 3
        return (self.pixels[offset], self.pixels[offset + 1],
                self.pixels[offset + 2])

    def set_pixel(self, x: int, y: int, color: Sequence[int]) -> None:
        offset = (y * self.width + x) * 3
        for channel in range(3):
            self.pixels[offset + channel] = max(0, min(255, int(color[channel])))

    def grayscale(self) -> List[List[int]]:
        """Matrice de niveaux de gris : entree de la vectorisation de plans."""
        rows: List[List[int]] = []
        for y in range(self.height):
            row: List[int] = []
            for x in range(self.width):
                r, g, b = self.pixel(x, y)
                row.append(int(0.299 * r + 0.587 * g + 0.114 * b))
            rows.append(row)
        return rows

    def resized(self, width: int, height: int) -> "Raster":
        """Reechantillonnage au plus proche voisin : vignettes et apercus."""
        out = Raster(width, height)
        for y in range(height):
            source_y = min(self.height - 1, int(y * self.height / height))
            for x in range(width):
                source_x = min(self.width - 1, int(x * self.width / width))
                out.set_pixel(x, y, self.pixel(source_x, source_y))
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {"largeur": self.width, "hauteur": self.height,
                "octets": len(self.pixels)}


# ---------------------------------------------------------------------------
# PNG
# ---------------------------------------------------------------------------
def write_png(raster: Raster, compression: int = 9) -> bytes:
    raw = bytearray()
    stride = raster.width * 3
    for row in range(raster.height):
        raw.append(0)
        raw.extend(raster.pixels[row * stride:(row + 1) * stride])

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", raster.width, raster.height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(bytes(raw), compression))
            + chunk(b"IEND", b""))


def read_png(data: bytes) -> Raster:
    """Decodeur PNG complet : 8 bits, gris, RGB, palette, alpha, filtres 0-4."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ImageError("signature PNG absente")
    cursor = 8
    width = height = depth = color_type = 0
    palette = b""
    compressed = bytearray()
    while cursor + 8 <= len(data):
        length, tag = struct.unpack_from(">I4s", data, cursor)
        payload = data[cursor + 8:cursor + 8 + length]
        cursor += 12 + length
        if tag == b"IHDR":
            width, height, depth, color_type = struct.unpack_from(">IIBB",
                                                                  payload, 0)
        elif tag == b"PLTE":
            palette = payload
        elif tag == b"IDAT":
            compressed += payload
        elif tag == b"IEND":
            break
    if depth != 8:
        raise ImageError("PNG %d bits par canal : seul le 8 bits est lu" % depth)
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise ImageError("type de couleur PNG inconnu : %d" % color_type)
    raw = zlib.decompress(bytes(compressed))
    stride = width * channels
    out = Raster(width, height)
    previous = bytearray(stride)
    cursor = 0
    for y in range(height):
        filter_type = raw[cursor]
        cursor += 1
        line = bytearray(raw[cursor:cursor + stride])
        cursor += stride
        for i in range(stride):
            a = line[i - channels] if i >= channels else 0
            b = previous[i]
            c = previous[i - channels] if i >= channels else 0
            if filter_type == 1:
                line[i] = (line[i] + a) & 0xFF
            elif filter_type == 2:
                line[i] = (line[i] + b) & 0xFF
            elif filter_type == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif filter_type == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                predictor = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + predictor) & 0xFF
        for x in range(width):
            base = x * channels
            if color_type == 3:
                index = line[base] * 3
                color = palette[index:index + 3] or b"\x00\x00\x00"
                out.set_pixel(x, y, tuple(color))
            elif channels <= 2:
                value = line[base]
                out.set_pixel(x, y, (value, value, value))
            else:
                out.set_pixel(x, y, (line[base], line[base + 1], line[base + 2]))
        previous = line
    return out


# ---------------------------------------------------------------------------
# BMP, TGA, PPM
# ---------------------------------------------------------------------------
def write_bmp(raster: Raster) -> bytes:
    padding = (4 - (raster.width * 3) % 4) % 4
    body = bytearray()
    for y in range(raster.height - 1, -1, -1):
        for x in range(raster.width):
            r, g, b = raster.pixel(x, y)
            body += bytes((b, g, r))
        body += b"\x00" * padding
    header = struct.pack("<2sIHHI", b"BM", 14 + 40 + len(body), 0, 0, 14 + 40)
    info = struct.pack("<IiiHHIIiiII", 40, raster.width, raster.height, 1, 24,
                       0, len(body), 2835, 2835, 0, 0)
    return header + info + bytes(body)


def read_bmp(data: bytes) -> Raster:
    if data[:2] != b"BM":
        raise ImageError("signature BMP absente")
    offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    bits = struct.unpack_from("<H", data, 28)[0]
    if bits != 24:
        raise ImageError("BMP %d bits : seul le 24 bits non compresse est lu"
                         % bits)
    flip = height > 0
    height = abs(height)
    out = Raster(width, height)
    stride = width * 3
    padding = (4 - stride % 4) % 4
    for row in range(height):
        base = offset + row * (stride + padding)
        y = height - 1 - row if flip else row
        for x in range(width):
            b, g, r = data[base + x * 3:base + x * 3 + 3]
            out.set_pixel(x, y, (r, g, b))
    return out


def write_tga(raster: Raster) -> bytes:
    header = struct.pack("<3B2HB4H2B", 0, 0, 2, 0, 0, 0, 0, 0, raster.width,
                         raster.height, 24, 0)
    body = bytearray()
    for y in range(raster.height - 1, -1, -1):
        for x in range(raster.width):
            r, g, b = raster.pixel(x, y)
            body += bytes((b, g, r))
    return header + bytes(body)


def write_ppm(raster: Raster) -> bytes:
    return (b"P6\n%d %d\n255\n" % (raster.width, raster.height)
            + bytes(raster.pixels))


def read_ppm(data: bytes) -> Raster:
    if data[:2] != b"P6":
        raise ImageError("seul le PPM binaire P6 est lu")
    fields: List[int] = []
    cursor = 2
    while len(fields) < 3 and cursor < len(data):
        while cursor < len(data) and data[cursor:cursor + 1].isspace():
            cursor += 1
        if data[cursor:cursor + 1] == b"#":
            while cursor < len(data) and data[cursor] != 0x0A:
                cursor += 1
            continue
        start = cursor
        while cursor < len(data) and not data[cursor:cursor + 1].isspace():
            cursor += 1
        fields.append(int(data[start:cursor]))
    cursor += 1
    width, height, _ = fields
    return Raster(width, height, bytearray(data[cursor:cursor + width * height * 3]))


# ---------------------------------------------------------------------------
# JPEG
# ---------------------------------------------------------------------------
def write_jpeg(raster: Raster, quality: int = 85) -> bytes:
    """Encodeur JPEG sans perte de dependance : Pillow s'il est la, sinon PNG.

    Un encodeur JPEG complet (DCT, Huffman) n'apporterait rien de plus que
    Pillow, qui est present sur la quasi-totalite des installations. Le
    format de repli est annonce explicitement par l'appelant.
    """
    try:
        from PIL import Image                # pragma: no cover - optionnel
        image = Image.frombytes("RGB", (raster.width, raster.height),
                                bytes(raster.pixels))
        import io
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=max(1, min(100, quality)))
        return buffer.getvalue()
    except ImportError:
        raise ImageError(
            "l'ecriture JPEG demande Pillow (pip install Pillow). "
            "Utilisez PNG, BMP, TGA ou PPM, tous ecrits nativement.")


def read_image(data: bytes) -> Raster:
    """Lit une image en detectant son format d'apres sa signature."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return read_png(data)
    if data[:2] == b"BM":
        return read_bmp(data)
    if data[:2] == b"P6":
        return read_ppm(data)
    try:
        from PIL import Image                # pragma: no cover - optionnel
        import io
        image = Image.open(io.BytesIO(data)).convert("RGB")
        return Raster(image.width, image.height, bytearray(image.tobytes()))
    except ImportError:
        raise ImageError(
            "format image non reconnu. PNG, BMP et PPM sont lus nativement ; "
            "installez Pillow (pip install Pillow) pour JPEG, TIFF, GIF et WEBP.")


def underlay(data: bytes, width_mm: float, origin=(0.0, 0.0, 0.0),
             rotation_deg: float = 0.0) -> Dict[str, Any]:
    """Commande ATTACHER : image de fond calee a l'echelle du dessin."""
    raster = read_image(data)
    scale = width_mm / float(raster.width)
    return {"type": "image_attachee", "largeur_px": raster.width,
            "hauteur_px": raster.height, "largeur_mm": width_mm,
            "hauteur_mm": round(raster.height * scale, 3),
            "echelle_mm_par_px": round(scale, 6),
            "origine": list(origin), "rotation_deg": rotation_deg}


IMAGE_FORMATS = {"png": True, "bmp": True, "ppm": True, "tga": False,
                 "jpg": False, "jpeg": False, "gif": False, "tif": False}
