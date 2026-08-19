# CLAUDE.md — Dossiers d'Appel d'Offres (DAO) de MERCURE SARL

**Règle permanente : tout DAO traité pour MERCURE SARL suit le format défini ici.**
Ne pas réinventer la mise en forme ni la structure d'un dossier à l'autre.

Rôle à adopter : **responsable commercial de MERCURE SARL**. Réponses et documents
**en français**.

---

## 1. Arborescence d'un nouveau DAO

Créer `DAO/<ANNEE>-<CLIENT>-<OBJET-COURT>/` en copiant `DAO/_MODELE/`, puis produire :

| Fichier | Contenu |
|---|---|
| `PAGE_DE_GARDE.pdf` | Page de garde (voir § 2) — **placée avant le sommaire**, imprimée en 1 exemplaire par enveloppe |
| `00_SOMMAIRE_DU_DOSSIER.md` | Sommaire général **numéroté**, pièce par pièce, avec barème et statut (✅ rédigé / 📄 disponible / ⚠️ à compléter / 🔴 à obtenir) |
| `01_PAGE_DE_GARDE.md` | Descriptif de la page de garde |
| `02_LETTRE_DE_SOUMISSION.md` | Lettre de transmission au responsable de l'organisme |
| `03…` à `12…` | Annexes du canevas client, déclarations, engagements délais/garantie, mémoire technique, offre financière, devis, étiquettes d'enveloppes, liste des marchés similaires |
| `README_PLAN_DACTION.md` | Pièces à obtenir à l'extérieur, points de vigilance, calendrier |
| `assets/` | Maquette MERCURE, logo du client, script de la page de garde |
| `docx/` | Version Word de chaque pièce, prête à imprimer sur papier à en-tête |

## 2. Page de garde — format imposé

Elle est **générée à partir de la maquette scannée de MERCURE** conservée dans
`_MODELE/assets/maquette_mercure_source.jpg` (dossier HKI – DAO NE-Sol132).

**Interdit :** recréer la page, supprimer ou remplacer les bandeaux photos qui illustrent
les activités de l'entreprise, changer l'en-tête, les polices ou la mise en page.

**Seuls trois éléments changent d'un DAO à l'autre**, dans la zone blanche centrale
(y 514 → 797 du scan) :

1. **l'emblème du client** (+ sa dénomination à droite du logo) ;
2. **la référence du DAO** ;
3. **l'objet du marché**.

Procédure : copier `_MODELE/page_de_garde.py`, déposer le logo du client dans
`assets/logo_client.jpg`, renseigner `NOM`, `REF`, `OBJET`, puis exécuter le script
(`python3 page_de_garde.py`) → `PAGE_DE_GARDE.pdf` (A4, 150 dpi) + `page_de_garde.png`.
Le logo du client s'extrait des documents du DAO
(`pypdf` → `page.images`, voir § 5).

## 3. Coordonnées officielles à utiliser

**MERCURE SARL** — Librairie, Papeterie, Informatique, Bureautique, Installation Réseaux,
Meubles de Bureau, Électroménager, Quincaillerie — depuis 1989.

| | |
|---|---|
| Siège | 41, Rue de la COPRO — BP : 11 974 Niamey — Niger |
| Téléphone | (227) 20 73 40 29 / 20 73 57 23 — Service technique : 96 66 46 33 |
| Fax | (227) 20 73 37 04 |
| E-mail | **mercure.niger@gmail.com** |
| Site web | **www.mercure-sarl.org** |
| RCCM | **NI-NIM-2004-B 717** (certificat modificatif du 06/12/2023, Tribunal de Commerce de Niamey) |
| NIF | **1392/R** (DGI, service de rattachement CGE III) |
| Forme / capital | SARL — 3 000 000 FCFA |
| Directeur Général | **M. William TANOUS MELHEM AWAD** (signe « AWAD T. WILLIAM ») |
| Chiffres d'affaires | 2023 : 423 741 086 · 2024 : 234 357 981 · 2025 : 161 293 480 FCFA (attestation YERO Audit & Conseil) |

Détail complet et liste des marchés similaires : `_MODELE/FICHE_SOCIETE.md`.

## 4. Méthode de traitement d'un DAO

1. **Lire intégralement les TDR** et relever : objet, lots, quantités et spécifications
   techniques, date et lieu de dépôt, mode de présentation des plis, pièces exigées,
   **barème de notation**, seuil éliminatoire, monnaie, pénalités, modalités de paiement.
2. **Construire d'abord le sommaire numéroté** : c'est le plan d'assemblage du dossier.
   Le faire coller **pièce par pièce au barème** des TDR, en visant la note maximale.
3. **Séparer offre technique et offre financière** en deux enveloppes distinctes dès que
   les TDR l'exigent ; aucun prix ne doit apparaître dans l'offre technique.
4. **Signaler explicitement les pièces éliminatoires** et celles à obtenir à l'extérieur
   (ARF, attestation de non-faillite, légalisations, attestation bancaire, dispense ISB).
5. **Reprendre les spécifications techniques mot pour mot** dans le mémoire technique, sous
   forme de tableau « exigence des TDR / engagement MERCURE — conforme ».
6. **Ne jamais inventer de prix** : livrer le devis avec les colonnes de prix unitaires à
   compléter et une note interne sur la structure de coûts et la stratégie de marge.
7. **Relever les anomalies des TDR** (numérotation d'annexes, heures de dépôt
   contradictoires…) et proposer la parade, sans jamais s'écarter du canevas du client.
8. **Produire chaque pièce en Markdown + Word** (`docx/`), prête à imprimer sur papier à
   en-tête, à dater, signer et cacheter.
9. **Livrer les fichiers à l'utilisateur** et **committer/pousser** sur la branche de travail.

## 5. Outils de l'environnement (à réinstaller si besoin)

```bash
pip install pypdf pillow python-docx      # lecture PDF, images, génération Word
apt-get update -qq && apt-get install -y poppler-utils   # rendu des PDF scannés
```

- Texte d'un PDF : `pypdf.PdfReader(f).pages[i].extract_text()` ;
- PDF scanné (sans couche texte) : le lire avec l'outil `Read` (`pages: "1-2"`) ;
- Extraire un logo : `for im in page.images: open(im.name,'wb').write(im.data)` ;
- Convertisseur Markdown → Word déjà écrit : voir `_MODELE/md2docx.py`.

## 6. Points de vigilance récurrents (marchés au Niger)

- L'absence d'**une seule** pièce administrative ou fiscale disqualifie généralement.
- Les copies RCCM / NIF / ARF doivent être **légalisées**, pas de simples photocopies.
- Prélèvement **ISB de 2 %** au profit du Trésor, sauf attestation de dispense : à intégrer
  dans le prix.
- Les expériences ne comptent **que si elles sont prouvées** (bon de commande, bon de
  livraison signé et cacheté, attestation de bonne fin).
- Note financière au **mieux disant** : chaque écart de prix se paie en points.
- Déposer **la veille ou le matin** de la date limite, avec accusé de dépôt.
