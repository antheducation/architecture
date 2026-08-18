# Les 70 livrables — état réel

Trois états, sans complaisance :

- **livré** — code fonctionnel, testé, exposé par l'API
- **esquissé** — module en place, interfaces définies, moteur à approfondir
- **documenté** — livrable non logiciel (marché, juridique, lancement)

| N° | Livrable | Groupe | Module | État |
|---|---|---|---|---|
| 01 | Vision et architecture globale | CORE | `docs` | livre |
| 02 | Analyse marche CAO BIM Construction Tech | BUSINESS | `docs` | documente |
| 03 | Moteur IA Design Generatif | CORE | `AI_Engine.generative_design` | livre |
| 04 | Assistant conversationnel IA ingenierie | CORE | `AI_Engine.nlp_assistant` | livre |
| 05 | Lecture automatique PDF et plans | CORE | `AI_Engine.vision_ai` | livre |
| 06 | Vision AI reconnaissance plans | CORE | `AI_Engine.vision_ai` | livre |
| 07 | Conversion 2D vers 3D | CORE | `CAD_Core.engine_3d` | livre |
| 08 | Interface CAO nouvelle generation | CORE | `Frontend` | livre |
| 09 | Rendu 3D temps reel | CORE | `CAD_Core.rendering` | livre |
| 10 | MVP initial | CORE | `API.main` | livre |
| 11 | BIM Engine | BIM | `BIM_Engine.models` | livre |
| 12 | Objets BIM intelligents | BIM | `BIM_Engine.object_library` | livre |
| 13 | Bibliotheque BIM | BIM | `BIM_Engine.object_library` | livre |
| 14 | Standards IFC | BIM | `BIM_Engine.ifc_handler` | livre |
| 15 | BIM Cloud Collaboration | COLLAB | `BIM_Engine.collaboration` | livre |
| 16 | Architecture Professional Module | BIM | `CAD_Core.engine_2d` | livre |
| 17 | Structure Engineering Module | BIM | `BIM_Engine.structure` | esquisse |
| 18 | MEP Engineering Module | BIM | `BIM_Engine.mep` | esquisse |
| 19 | Documentation automatique | BIM | `CAD_Core.documentation` | livre |
| 20 | Assistant ingenieur BIM IA | CORE | `AI_Engine.nlp_assistant` | livre |
| 21 | Gestion versions projet | COLLAB | `Database.repository` | livre |
| 22 | Marketplace BIM | BIM | `BIM_Engine.object_library` | esquisse |
| 23 | Fabricants materiaux | BIM | `BIM_Engine.object_library` | esquisse |
| 24 | API BIM | CORE | `API.main` | livre |
| 25 | Enterprise BIM Platform | COLLAB | `Security.rbac` | livre |
| 26 | Construction AI Platform | CONSTRUCTION | `Construction.platform` | esquisse |
| 27 | Planning chantier IA | CONSTRUCTION | `Construction.planning` | livre |
| 28 | Suivi avancement chantier | CONSTRUCTION | `Construction.progress` | esquisse |
| 29 | Vision IA qualite | CONSTRUCTION | `AI_Engine.vision_ai` | esquisse |
| 30 | Securite chantier IA | CONSTRUCTION | `Construction.safety` | esquisse |
| 31 | Drone chantier | CONSTRUCTION | `Construction.drone` | esquisse |
| 32 | Comparaison BIM reel | CONSTRUCTION | `Construction.progress` | esquisse |
| 33 | Gestion ressources | CONSTRUCTION | `Construction.resources` | esquisse |
| 34 | Gestion fournisseurs | CONSTRUCTION | `Construction.resources` | esquisse |
| 35 | Rapports automatiques | CONSTRUCTION | `CAD_Core.documentation` | livre |
| 36 | Cost AI | COST | `Estimating.cost_ai` | livre |
| 37 | Metres automatiques | COST | `Estimating.takeoff` | livre |
| 38 | Devis IA | COST | `Estimating.cost_ai` | livre |
| 39 | Optimisation budget | COST | `Estimating.cost_ai` | esquisse |
| 40 | Project Management Enterprise | COLLAB | `Construction.planning` | esquisse |
| 41 | Digital Twin Platform | TWIN | `Cloud_Platform.digital_twin` | livre |
| 42 | Smart Building OS | TWIN | `Cloud_Platform.digital_twin` | esquisse |
| 43 | IoT Integration | TWIN | `Cloud_Platform.iot` | livre |
| 44 | Maintenance predictive | TWIN | `Cloud_Platform.predictive` | livre |
| 45 | Energy Intelligence | GREEN | `Sustainability.energy` | livre |
| 46 | Solar Microgrid | GREEN | `Sustainability.energy` | esquisse |
| 47 | Performance batiment | GREEN | `Sustainability.energy` | livre |
| 48 | AR Maintenance | MOBILE | `Mobile.ar` | esquisse |
| 49 | Drone Inspection Digital Twin | TWIN | `Construction.drone` | esquisse |
| 50 | Cycle de vie batiment | GREEN | `Sustainability.carbon` | livre |
| 51 | Green Building AI | GREEN | `Sustainability.carbon` | livre |
| 52 | Calcul carbone | GREEN | `Sustainability.carbon` | livre |
| 53 | Materiaux durables | GREEN | `Sustainability.carbon` | livre |
| 54 | Simulation energetique | GREEN | `Sustainability.energy` | livre |
| 55 | Certification verte | GREEN | `Sustainability.certification` | livre |
| 56 | Adaptation climatique | GREEN | `Sustainability.energy` | esquisse |
| 57 | Smart Village Platform | CITY | `Cloud_Platform.city` | esquisse |
| 58 | Digital Twin Smart City | CITY | `Cloud_Platform.city` | esquisse |
| 59 | GIS Topography Drone | CITY | `Cloud_Platform.city` | esquisse |
| 60 | Finance Projet AI | BUSINESS | `Estimating.cost_ai` | esquisse |
| 61 | Sustainability AI | GREEN | `Sustainability.carbon` | livre |
| 62 | Topography Integration | CITY | `Cloud_Platform.city` | esquisse |
| 63 | Mobile Tablet Platform | MOBILE | `Mobile` | livre |
| 64 | Expansion internationale | BUSINESS | `docs` | documente |
| 65 | Legal Corporate Governance | BUSINESS | `docs` | documente |
| 66 | Investor Package | BUSINESS | `docs/INVESTOR_DECK.md` | documente |
| 67 | Documentation technique | BUSINESS | `docs` | livre |
| 68 | Beta Testing Program | BUSINESS | `docs` | documente |
| 69 | Global Launch Plan | BUSINESS | `docs` | documente |
| 70 | Master Plan 2030 | BUSINESS | `docs/ROADMAP_2030.md` | documente |

---

## Lecture par groupe

| Groupe | Description | Livré | Esquissé | Documenté |
|---|---|---|---|---|
| CORE | Systeme central : CAO, IA, interface, MVP | 11 | 0 | 0 |
| BIM | Moteur BIM, objets, standards IFC, metiers | 6 | 4 | 0 |
| COLLAB | Collaboration, versions, entreprise | 3 | 1 | 0 |
| CONSTRUCTION | Chantier : planning, suivi, qualite, securite | 2 | 8 | 0 |
| COST | Economie : metres, couts, devis | 3 | 1 | 0 |
| TWIN | Jumeau numerique, IoT, maintenance | 3 | 2 | 0 |
| GREEN | Environnement : carbone, energie, certification | 9 | 2 | 0 |
| CITY | Territoire : village et ville intelligents | 0 | 4 | 0 |
| MOBILE | Terrain : tablette, mobile, realite augmentee | 1 | 1 | 0 |
| BUSINESS | Marche, juridique, investisseurs, lancement | 1 | 1 | 7 |

Registre interrogeable : `GET /api/v1/deliverables?groupe=CORE`
