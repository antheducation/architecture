# MODÈLE DE DOSSIER D'APPEL D'OFFRES — MERCURE SARL

Point de départ de **tout nouveau DAO**. Les règles de fond sont dans `../CLAUDE.md`.

## Marche à suivre

```bash
# 1. Créer le dossier du nouvel appel d'offres
cp -r DAO/_MODELE "DAO/2026-CLIENT-OBJET"
cd "DAO/2026-CLIENT-OBJET"

# 2. Déposer l'emblème du client (extrait des documents du DAO)
#    -> assets/logo_client.jpg

# 3. Renseigner en tête de page_de_garde.py :
#      NOM   = dénomination du client (3 lignes)
#      REF   = référence de l'appel d'offres (2 lignes)
#      OBJET = objet du marché (2 lignes)
python3 page_de_garde.py          # -> PAGE_DE_GARDE.pdf + page_de_garde.png

# 4. Rédiger les pièces (sommaire d'abord), puis générer les versions Word
python3 md2docx.py . ./docx
```

## Contenu du modèle

| Fichier | Rôle |
|---|---|
| `page_de_garde.py` | Génère la page de garde **sur la maquette MERCURE d'origine** — ne pas modifier la mise en page ni retirer les photos |
| `assets/maquette_mercure_source.jpg` | Maquette MERCURE de référence (dossier HKI – DAO NE-Sol132) — **ne jamais altérer** |
| `assets/entete_mercure.png` | En-tête MERCURE seul (site corrigé), utilisable sur les autres pièces |
| `FICHE_SOCIETE.md` | Données officielles de MERCURE SARL et liste des marchés similaires |
| `md2docx.py` | Convertisseur Markdown → Word (titres, tableaux, listes, gras/italique) |

## Extraire le logo du client depuis les documents du DAO

```python
from pypdf import PdfReader
for page in PdfReader("tdr.pdf").pages:
    for im in page.images:
        open(im.name, "wb").write(im.data)
```

## Rappel des pièces standard d'un dossier

**Enveloppe A — offre technique :** page de garde · sommaire numéroté · lettre de
soumission · formulaire d'information société · RCCM légalisé · NIF légalisé · ARF
légalisée · attestation de non-faillite · lettre d'engagement · tableau des expériences +
preuves · liste des marchés similaires · engagements délai de livraison et garantie ·
mémoire technique · déclarations sur l'honneur · attestation de chiffre d'affaires · RIB ·
pièce d'identité du DG.

**Enveloppe B — offre financière :** page de garde · lettre de soumission financière ·
devis quantitatif et estimatif · récapitulatif HT / ISB 2 % / net à percevoir.
