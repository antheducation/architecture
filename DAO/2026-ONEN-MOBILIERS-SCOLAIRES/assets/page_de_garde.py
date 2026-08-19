"""Page de garde MERCURE SARL — maquette d'origine conservee (photos incluses).
Seuls sont remplaces : le logo du client, la reference du DAO et son objet."""
from PIL import Image, ImageDraw, ImageFont

SCAN = "maquette_mercure_source.jpg"          # maquette MERCURE (dossier HKI NE-Sol132)
LOGO = "logo_onen.jpg"                       # embleme du client
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ENCRE = (58, 58, 62)
BLEU = (41, 122, 205)

REF = ["NIGER – APPEL D’OFFRES OUVERT", "N° 007/2026/ONEN/FONDATION STROMME/DO"]
OBJET = ["CONFECTION DE MOBILIERS SCOLAIRES",
         "AU PROFIT DES CENTRES SSA/P DE KOYGOLO ET DE SOKORBÉ"]

page = Image.open(SCAN).convert("RGB")
d = ImageDraw.Draw(page)

# 1. Site web : www.mercure-sarl.com -> www.mercure-sarl.org
d.rectangle([360, 180, 700, 213], fill="white")
f = ImageFont.truetype(SANS, 21)
site = "www.mercure-sarl.org"
d.text(((1275 - d.textlength(site, font=f)) / 2 - 105, 184), site, font=f, fill=BLEU)

# 2. Zone libre entre les deux bandeaux de photos : logo client + reference + objet
d.rectangle([40, 514, 1240, 797], fill="white")

logo = Image.open(LOGO).convert("RGB")
h = 118
logo = logo.resize((int(logo.width * h / logo.height), h), Image.LANCZOS)


def texte(t, x, y, taille, couleur=ENCRE, police=SANS):
    d.text((x, y), t, font=ImageFont.truetype(police, taille), fill=couleur)


def largeur(t, taille, police=SANS):
    return d.textlength(t, font=ImageFont.truetype(police, taille))


# Bloc client : embleme + denomination, a la place du logo Helen Keller Intl
NOM = ["ORGANISATION NIGÉRIENNE DES", "ÉDUCATEURS NOVATEURS", "ONG – ONEN"]
bloc = max(largeur(NOM[0], 23), largeur(NOM[1], 23), largeur(NOM[2], 26))
total = logo.width + 18 + bloc
x0 = int((1275 - total) / 2)
page.paste(logo, (x0, 514))
xt = x0 + logo.width + 18
texte(NOM[0], xt, 528, 23, (13, 61, 107))
texte(NOM[1], xt, 558, 23, (13, 61, 107))
texte(NOM[2], xt, 592, 26, (13, 61, 107))


def ligne(t, y, taille, largeur_max=1150, police=SERIF):
    """Ecrit une ligne centree, en reduisant la taille si elle deborde."""
    while taille > 12:
        fnt = ImageFont.truetype(police, taille)
        if d.textlength(t, font=fnt) <= largeur_max:
            break
        taille -= 1
    d.text(((1275 - d.textlength(t, font=fnt)) / 2, y), t, font=fnt, fill=ENCRE)


ligne(REF[0], 644, 31)
ligne(REF[1], 682, 29)
ligne(OBJET[0], 720, 30)
ligne(OBJET[1], 758, 23)

page.save("page_de_garde.png")

# 3. Mise en page A4 (150 dpi) et export PDF
A4 = (1240, 1754)
ech = A4[0] / page.width
corps = page.resize((A4[0], int(page.height * ech)), Image.LANCZOS)
feuille = Image.new("RGB", A4, "white")
feuille.paste(corps, (0, max(0, (A4[1] - corps.height) // 2)))
feuille.save("../PAGE_DE_GARDE.pdf", "PDF", resolution=150.0)
print("page_de_garde.png +", "PAGE_DE_GARDE.pdf")
