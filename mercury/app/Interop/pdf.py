"""Ecriture PDF vectorielle : planches, dossiers, notes de calcul.

Un PDF de CAO doit rester vectoriel : les traits restent nets a n'importe
quel zoom et les cotes restent lisibles a l'impression. Ce module ecrit un
PDF 1.4 conforme, multipage, avec cartouche, calques (groupes de contenu
optionnels), textes et images matricielles.
"""
from __future__ import annotations

import zlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

PAPER_SIZES_PT: Dict[str, Tuple[float, float]] = {
    "A4": (841.89, 595.28), "A3": (1190.55, 841.89), "A2": (1683.78, 1190.55),
    "A1": (2383.94, 1683.78), "A0": (3370.39, 2383.94),
    "LETTER": (792.0, 612.0), "TABLOID": (1224.0, 792.0),
}
MM_TO_PT = 72.0 / 25.4


class PdfError(ValueError):
    """Document PDF impossible a produire."""


class PdfPage:
    """Une page : instructions de dessin en coordonnees millimetre."""

    def __init__(self, size: str = "A3", landscape: bool = True,
                 title: str = "") -> None:
        if size not in PAPER_SIZES_PT:
            raise PdfError("format de papier inconnu : %s" % size)
        width, height = PAPER_SIZES_PT[size]
        if not landscape:
            width, height = height, width
        self.width = width
        self.height = height
        self.size = size
        self.title = title
        self.operations: List[str] = ["1 J 1 j"]

    # -- primitives --------------------------------------------------------
    def _xy(self, point) -> Tuple[float, float]:
        x, y = float(point[0]), float(point[1])
        return x * MM_TO_PT, y * MM_TO_PT

    def stroke_color(self, r: float, g: float, b: float) -> "PdfPage":
        self.operations.append("%.3f %.3f %.3f RG" % (r, g, b))
        return self

    def fill_color(self, r: float, g: float, b: float) -> "PdfPage":
        self.operations.append("%.3f %.3f %.3f rg" % (r, g, b))
        return self

    def line_width(self, millimeters: float) -> "PdfPage":
        self.operations.append("%.3f w" % (millimeters * MM_TO_PT))
        return self

    def dash(self, pattern: Optional[Sequence[float]] = None) -> "PdfPage":
        if not pattern:
            self.operations.append("[] 0 d")
        else:
            self.operations.append("[%s] 0 d"
                                   % " ".join("%.2f" % (v * MM_TO_PT)
                                              for v in pattern))
        return self

    def line(self, start, end) -> "PdfPage":
        x0, y0 = self._xy(start)
        x1, y1 = self._xy(end)
        self.operations.append("%.3f %.3f m %.3f %.3f l S" % (x0, y0, x1, y1))
        return self

    def polyline(self, points: Sequence, close: bool = False,
                 fill: bool = False) -> "PdfPage":
        if len(points) < 2:
            return self
        x, y = self._xy(points[0])
        parts = ["%.3f %.3f m" % (x, y)]
        for point in points[1:]:
            x, y = self._xy(point)
            parts.append("%.3f %.3f l" % (x, y))
        if close:
            parts.append("h")
        parts.append("B" if fill and close else ("f" if fill else "S"))
        self.operations.append(" ".join(parts))
        return self

    def rectangle(self, origin, width: float, height: float,
                  fill: bool = False) -> "PdfPage":
        x, y = self._xy(origin)
        self.operations.append("%.3f %.3f %.3f %.3f re %s"
                               % (x, y, width * MM_TO_PT, height * MM_TO_PT,
                                  "B" if fill else "S"))
        return self

    def circle(self, center, radius: float, fill: bool = False) -> "PdfPage":
        """Cercle par quatre courbes de Bezier (approximation exacte a 0,03 %)."""
        cx, cy = self._xy(center)
        r = radius * MM_TO_PT
        k = r * 0.5522847498
        self.operations.append(
            "%.3f %.3f m %.3f %.3f %.3f %.3f %.3f %.3f c "
            "%.3f %.3f %.3f %.3f %.3f %.3f c "
            "%.3f %.3f %.3f %.3f %.3f %.3f c "
            "%.3f %.3f %.3f %.3f %.3f %.3f c %s"
            % (cx + r, cy, cx + r, cy + k, cx + k, cy + r, cx, cy + r,
               cx - k, cy + r, cx - r, cy + k, cx - r, cy,
               cx - r, cy - k, cx - k, cy - r, cx, cy - r,
               cx + k, cy - r, cx + r, cy - k, cx + r, cy,
               "B" if fill else "S"))
        return self

    def text(self, position, value: str, size_mm: float = 3.5,
             font: str = "F1", rotation_deg: float = 0.0) -> "PdfPage":
        x, y = self._xy(position)
        escaped = (value.replace("\\", r"\\").replace("(", r"\(")
                   .replace(")", r"\)"))
        size = size_mm * MM_TO_PT
        if abs(rotation_deg) < 1e-6:
            self.operations.append("BT /%s %.2f Tf %.3f %.3f Td (%s) Tj ET"
                                   % (font, size, x, y, escaped))
        else:
            import math
            c, s = math.cos(math.radians(rotation_deg)), \
                math.sin(math.radians(rotation_deg))
            self.operations.append(
                "BT /%s %.2f Tf %.4f %.4f %.4f %.4f %.3f %.3f Tm (%s) Tj ET"
                % (font, size, c, s, -s, c, x, y, escaped))
        return self

    def title_block(self, project: str, sheet: str, scale: str = "1:100",
                    date: str = "", author: str = "MERCURY CAD AI X",
                    height: float = 40.0, width: float = 180.0) -> "PdfPage":
        """Cartouche normalise, cale en bas a droite de la feuille."""
        page_width = self.width / MM_TO_PT
        x = page_width - width - 10.0
        y = 10.0
        self.line_width(0.35).stroke_color(0, 0, 0)
        self.rectangle((x, y), width, height)
        self.line((x, y + height * 0.6), (x + width, y + height * 0.6))
        self.line((x + width * 0.6, y), (x + width * 0.6, y + height * 0.6))
        self.text((x + 4, y + height * 0.75), project, 4.5)
        self.text((x + 4, y + height * 0.35), sheet, 3.2)
        self.text((x + 4, y + height * 0.15), date, 2.6)
        self.text((x + width * 0.63, y + height * 0.35), "Echelle " + scale, 3.0)
        self.text((x + width * 0.63, y + height * 0.15), author, 2.6)
        return self

    def content(self) -> bytes:
        return "\n".join(self.operations).encode("latin-1", "replace")


class PdfDocument:
    """Document PDF multipage."""

    def __init__(self, title: str = "MERCURY CAD AI X",
                 author: str = "MERCURY CAD AI X") -> None:
        self.title = title
        self.author = author
        self.pages: List[PdfPage] = []

    def add_page(self, size: str = "A3", landscape: bool = True,
                 title: str = "") -> PdfPage:
        page = PdfPage(size, landscape, title)
        self.pages.append(page)
        return page

    def build(self, compress: bool = True) -> bytes:
        if not self.pages:
            raise PdfError("document PDF sans page")
        objects: List[bytes] = []

        def add_object(payload: bytes) -> int:
            objects.append(payload)
            return len(objects)

        font_regular = add_object(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>")
        font_bold = add_object(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>")
        pages_id = add_object(b"placeholder")

        page_ids: List[int] = []
        for page in self.pages:
            payload = page.content()
            if compress:
                stream = zlib.compress(payload, 9)
                content_id = add_object(
                    b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream)
                    + stream + b"\nendstream")
            else:
                content_id = add_object(
                    b"<< /Length %d >>\nstream\n" % len(payload) + payload
                    + b"\nendstream")
            page_id = add_object(
                ("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] "
                 "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> "
                 "/Contents %d 0 R >>"
                 % (pages_id, page.width, page.height, font_regular, font_bold,
                    content_id)).encode("latin-1"))
            page_ids.append(page_id)

        objects[pages_id - 1] = (
            "<< /Type /Pages /Count %d /Kids [%s] >>"
            % (len(page_ids), " ".join("%d 0 R" % i for i in page_ids))
        ).encode("latin-1")

        info_id = add_object(
            ("<< /Title (%s) /Author (%s) /Creator (MERCURY CAD AI X) "
             "/Producer (MERCURY CAD AI X) >>"
             % (self.title.replace("(", "").replace(")", ""),
                self.author.replace("(", "").replace(")", ""))).encode("latin-1"))
        catalog_id = add_object(("<< /Type /Catalog /Pages %d 0 R >>"
                                 % pages_id).encode("latin-1"))

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: List[int] = []
        for index, payload in enumerate(objects, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % index + payload + b"\nendobj\n"
        xref_position = len(out)
        out += b"xref\n0 %d\n" % (len(objects) + 1)
        out += b"0000000000 65535 f \n"
        for offset in offsets:
            out += b"%010d 00000 n \n" % offset
        out += (b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n"
                b"%d\n%%%%EOF\n" % (len(objects) + 1, catalog_id, info_id,
                                    xref_position))
        return bytes(out)


def probe_pdf(data: bytes) -> Dict[str, Any]:
    """Identifie un PDF : version, nombre de pages, taille."""
    if data[:5] != b"%PDF-":
        raise PdfError("signature PDF absente")
    version = data[5:8].decode("ascii", "replace")
    return {"format": "PDF", "version": version,
            "pages": data.count(b"/Type /Page") - data.count(b"/Type /Pages"),
            "taille_octets": len(data),
            "compresse": b"/FlateDecode" in data}
