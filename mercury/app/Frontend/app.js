/* Application MERCURY CAD AI X.
 *
 * Le ruban est construit a partir du catalogue de commandes servi par l'API :
 * ajouter une commande cote serveur la fait apparaitre dans l'interface sans
 * toucher a ce fichier. Toutes les actions passent par le meme point d'entree
 * que la ligne de commande et que les scripts.
 */
(function () {
  "use strict";

  var API = window.location.origin;
  var etat = {
    document: null, catalogue: [], capacites: null, formats: [],
    calques: [], objets: [], selection: [], onglet: null, outil: null,
    historique: [], indexHistorique: 0
  };
  var viewer = null;

  /* Regroupement des commandes en onglets de ruban, a la maniere d'AutoCAD. */
  var ONGLETS = [
    { cle: "solide", titre: "Solide",
      groupes: ["solides_primitifs", "solides_profil", "booleens"] },
    { cle: "modification", titre: "Modification",
      groupes: ["edition_solides", "transformations"] },
    { cle: "surface", titre: "Surface et maillage",
      groupes: ["surfaces", "maillages", "courbes"] },
    { cle: "dessin", titre: "Dessin 2D", groupes: ["dessin_2d"] },
    { cle: "annoter", titre: "Annoter", groupes: ["annotation", "mesures"] },
    { cle: "vue", titre: "Vue", groupes: ["vues"] },
    { cle: "gerer", titre: "Gerer",
      groupes: ["organisation", "aides", "fichiers", "general"] }
  ];

  var GLYPHES = {
    BOITE: "▧", BISEAU: "◺", CYLINDRE: "▮", CONE: "▲", SPHERE: "●", TORE: "◎",
    PYRAMIDE: "◭", POLYSOLIDE: "▤", HELICE: "➰", EXTRUSION: "⇧",
    REVOLUTION: "↻", BALAYAGE: "➤", LISSAGE: "◈", APPUYERTIRER: "⇕",
    EPAISSIR: "▥", UNION: "∪", SOUSTRACTION: "∖", INTERSECTION: "∩",
    INTERFERENCE: "⚠", RACCORDARETE: "◜", CHANFREINARETE: "◹", GAINE: "▢",
    COUPE: "✂", SECTION: "▬", DEPOUILLE: "◣", DECALAGE: "⧉", SEPARER: "⋔",
    EMPREINTE: "◫", XARETES: "▦", VERIFSOLIDE: "✓", PROPMECA: "⚖",
    DEPLACER3D: "✥", ROTATION3D: "⟳", ECHELLE: "⤢", MIROIR3D: "⇋",
    ALIGNER3D: "⊹", COPIER: "⧉", RESEAU3D: "⋮⋮", RESEAUPOLAIRE: "❋",
    RESEAUCHEMIN: "⇝", EFFACER: "🗑", LIGNE: "╱", POLYLIGNE: "⌇", CERCLE: "○",
    ARC: "◜", RECTANG: "▭", POLYGONE: "⬡", ELLIPSE: "⬭", SPLINE: "∿",
    POINT: "•", COTLIN: "↔", COTALI: "⤢", COTANG: "∠", COTRAYON: "⌀",
    COTDIA: "⌀", TEXTMULT: "T", LIGNEDEREPERE: "➘", HACHURES: "▨",
    TABLEAU: "▤", NUAGEREV: "☁", CALQUE: "≡", BLOC: "▣", INSERER: "⊕",
    SCU: "⌐", PRESENTATION: "🗎", VUEPOINT: "◱", ORBITE3D: "🜛", ZOOM: "🔍",
    PAN: "✋", STYLESVISUELS: "◐", RENDU: "☀", MASQUE: "◑", VUE: "👁",
    EXPORTER: "⇩", IMPORTER: "⇧", MESURER: "📏", LISSERMAILLE: "≈",
    AFFINERMAILLE: "⁘", TRIANGULER: "△", SOUDER: "⛓"
  };

  /* ------------------------------------------------------------- reseau */
  function requete(chemin, options) {
    options = options || {};
    var init = { method: options.method || "GET", headers: {} };
    if (options.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(options.body);
    }
    if (options.form) { init.body = options.form; delete init.headers["Content-Type"]; }
    return fetch(API + chemin, init).then(function (reponse) {
      if (options.brut) {
        if (!reponse.ok) { return reponse.text().then(function (t) { throw new Error(t); }); }
        return reponse.blob();
      }
      return reponse.json().then(function (donnees) {
        if (!reponse.ok) {
          throw new Error(donnees.detail || ("erreur HTTP " + reponse.status));
        }
        return donnees;
      });
    });
  }

  /* ----------------------------------------------------------- journal */
  function journaliser(texte, genre) {
    var conteneur = document.getElementById("journal");
    var ligne = document.createElement("div");
    ligne.className = "entree-journal" + (genre ? " " + genre : "");
    var horodatage = new Date().toLocaleTimeString();
    ligne.textContent = horodatage + "  " + texte;
    conteneur.insertBefore(ligne, conteneur.firstChild);
    while (conteneur.childElementCount > 200) {
      conteneur.removeChild(conteneur.lastChild);
    }
    document.getElementById("message").textContent = texte;
  }

  /* ------------------------------------------------------------- ruban */
  function construireOnglets() {
    var barre = document.getElementById("onglets");
    barre.innerHTML = "";
    ONGLETS.forEach(function (onglet) {
      var bouton = document.createElement("button");
      bouton.textContent = onglet.titre;
      bouton.dataset.onglet = onglet.cle;
      bouton.addEventListener("click", function () { activerOnglet(onglet.cle); });
      barre.appendChild(bouton);
    });
    activerOnglet(ONGLETS[0].cle);
  }

  function activerOnglet(cle) {
    etat.onglet = cle;
    Array.prototype.forEach.call(
      document.querySelectorAll("#onglets button"), function (bouton) {
        bouton.classList.toggle("actif", bouton.dataset.onglet === cle);
      });
    var definition = ONGLETS.filter(function (o) { return o.cle === cle; })[0];
    var ruban = document.getElementById("ruban");
    ruban.innerHTML = "";
    definition.groupes.forEach(function (groupe) {
      var commandes = etat.catalogue.filter(function (c) {
        return c.groupe === groupe;
      });
      if (!commandes.length) { return; }
      var bloc = document.createElement("div");
      bloc.className = "groupe-ruban";
      var outils = document.createElement("div");
      outils.className = "outils";
      commandes.forEach(function (commande) {
        outils.appendChild(construireOutil(commande));
      });
      var titre = document.createElement("div");
      titre.className = "titre-groupe";
      titre.textContent = groupe.replace(/_/g, " ");
      bloc.appendChild(outils);
      bloc.appendChild(titre);
      ruban.appendChild(bloc);
    });
  }

  function construireOutil(commande) {
    var bouton = document.createElement("button");
    bouton.className = "outil";
    bouton.title = commande.resume + " (" + commande.nom
      + (commande.anglais ? " / " + commande.anglais : "") + ")";
    var glyphe = document.createElement("span");
    glyphe.className = "glyphe";
    glyphe.textContent = GLYPHES[commande.nom] || "◇";
    var libelle = document.createElement("span");
    libelle.className = "libelle";
    libelle.textContent = commande.nom.toLowerCase();
    bouton.appendChild(glyphe);
    bouton.appendChild(libelle);
    bouton.addEventListener("click", function () { choisirOutil(commande); });
    return bouton;
  }

  /* --------------------------------------------- parametres d'un outil */
  function choisirOutil(commande) {
    etat.outil = commande;
    var panneau = document.getElementById("parametres-outil");
    panneau.innerHTML = "";
    var titre = document.createElement("div");
    titre.innerHTML = "<b>" + commande.nom + "</b> <span class=\"indication\">"
      + (commande.anglais || "") + "</span><p class=\"indication\">"
      + commande.resume + "</p>";
    panneau.appendChild(titre);
    var champs = {};
    Object.keys(commande.parametres).forEach(function (nom) {
      var ligne = document.createElement("div");
      ligne.className = "champ";
      var etiquette = document.createElement("label");
      etiquette.textContent = nom;
      var saisie = document.createElement("input");
      saisie.type = "text";
      saisie.placeholder = commande.parametres[nom];
      champs[nom] = saisie;
      ligne.appendChild(etiquette);
      ligne.appendChild(saisie);
      panneau.appendChild(ligne);
    });
    var lancer = document.createElement("button");
    lancer.textContent = "Executer " + commande.nom;
    lancer.className = "primaire";
    lancer.style.cssText = "margin-top:8px;width:100%;background:var(--accent);"
      + "color:#1a1206;border:none;border-radius:4px;padding:7px;cursor:pointer;"
      + "font-weight:600";
    lancer.addEventListener("click", function () {
      var parametres = {};
      Object.keys(champs).forEach(function (nom) {
        var valeur = champs[nom].value.trim();
        if (valeur !== "") { parametres[nom] = convertir(valeur); }
      });
      if (etat.selection.length) { parametres.handles = etat.selection; }
      executer(commande.nom, parametres);
    });
    panneau.appendChild(lancer);
  }

  function convertir(texte) {
    var minuscule = texte.toLowerCase();
    if (minuscule === "vrai" || minuscule === "true") { return true; }
    if (minuscule === "faux" || minuscule === "false") { return false; }
    if (texte.indexOf(",") >= 0) {
      return texte.split(",").map(function (part) { return convertir(part.trim()); });
    }
    var nombre = Number(texte);
    return texte !== "" && !isNaN(nombre) ? nombre : texte;
  }

  /* -------------------------------------------------------- commandes */
  function executer(nom, parametres) {
    if (!etat.document) { journaliser("aucun document ouvert", "erreur"); return; }
    return requete("/api/v1/cad/documents/" + etat.document + "/command", {
      method: "POST", body: { commande: nom, parametres: parametres || {} }
    }).then(function (reponse) {
      journaliser(nom + " : " + resumer(reponse.resultat), "succes");
      appliquerEtat(reponse.etat);
      return rafraichirScene();
    }).catch(function (erreur) {
      journaliser(nom + " — " + erreur.message, "erreur");
    });
  }

  function resumer(resultat) {
    var cles = Object.keys(resultat).filter(function (cle) {
      return ["commande", "groupe", "objet", "camera", "etat"].indexOf(cle) < 0;
    });
    if (!cles.length) { return "termine"; }
    return cles.slice(0, 4).map(function (cle) {
      var valeur = resultat[cle];
      if (valeur && typeof valeur === "object") {
        valeur = Array.isArray(valeur) ? valeur.length + " element(s)" : "…";
      }
      return cle + "=" + valeur;
    }).join(", ");
  }

  function executerLigne() {
    var champ = document.getElementById("commande");
    var ligne = champ.value.trim();
    if (!ligne) { return; }
    etat.historique.push(ligne);
    etat.indexHistorique = etat.historique.length;
    champ.value = "";
    requete("/api/v1/cad/documents/" + etat.document + "/script", {
      method: "POST", body: { script: ligne }
    }).then(function (reponse) {
      reponse.resultats.forEach(function (resultat) {
        journaliser(resultat.commande + " : " + resumer(resultat), "succes");
      });
      appliquerEtat(reponse.etat);
      return rafraichirScene();
    }).catch(function (erreur) {
      journaliser(erreur.message, "erreur");
    });
  }

  /* ------------------------------------------------------------- scene */
  function rafraichirScene() {
    if (!etat.document) { return Promise.resolve(); }
    var base = "/api/v1/cad/documents/" + etat.document;
    return Promise.all([requete(base + "/mesh"), requete(base + "/curves"),
                        requete(base)])
      .then(function (reponses) {
        viewer.load(reponses[0]);
        viewer.loadCurves(reponses[1].courbes || []);
        etat.calques = reponses[2].calques || [];
        dessinerCalques();
        return requete(base + "/entities?limit=400");
      })
      .then(function (reponse) {
        etat.objets = reponse.objets || [];
        dessinerObjets();
        majInfoVue();
      });
  }

  function appliquerEtat(statistiques) {
    if (!statistiques) { return; }
    document.getElementById("statistiques").textContent =
      statistiques.objets + " objet(s) · " + statistiques.calques + " calque(s) · "
      + (statistiques.volume_total_mm3 / 1e9).toFixed(3) + " m³";
  }

  function majInfoVue() {
    var camera = viewer.cameraState();
    document.getElementById("info-vue").textContent =
      "azimut " + camera.azimut + "°  elevation " + camera.elevation + "°\n"
      + "distance " + camera.distance + " mm\n"
      + "grille " + (viewer.gridStep || 0) + " mm";
  }

  function dessinerCalques() {
    var conteneur = document.getElementById("calques");
    conteneur.innerHTML = "";
    if (!etat.calques.length) {
      conteneur.innerHTML = "<p class=\"vide\">Aucun calque.</p>";
      return;
    }
    etat.calques.forEach(function (calque) {
      var ligne = document.createElement("div");
      ligne.className = "ligne-calque";
      var puce = document.createElement("span");
      puce.className = "puce-couleur";
      puce.style.background = "rgb(" + (calque.rvb || [200, 200, 200]).join(",") + ")";
      var nom = document.createElement("span");
      nom.className = "nom-calque";
      nom.textContent = calque.nom;
      var oeil = document.createElement("button");
      oeil.className = "bascule-calque" + (calque.actif ? "" : " eteint");
      oeil.textContent = "👁";
      oeil.title = "Activer ou desactiver le calque";
      oeil.addEventListener("click", function (event) {
        event.stopPropagation();
        executer("CALQUE", { nom: calque.nom, couleur: calque.couleur,
                             courant: true });
      });
      ligne.appendChild(puce);
      ligne.appendChild(nom);
      ligne.appendChild(oeil);
      ligne.addEventListener("click", function () {
        executer("SELECTIONNER", { calque: calque.nom });
      });
      conteneur.appendChild(ligne);
    });
  }

  function dessinerObjets() {
    var conteneur = document.getElementById("objets");
    conteneur.innerHTML = "";
    if (!etat.objets.length) {
      conteneur.innerHTML = "<p class=\"vide\">Document vide.</p>";
      return;
    }
    etat.objets.forEach(function (objet) {
      var ligne = document.createElement("div");
      ligne.className = "ligne-objet"
        + (etat.selection.indexOf(objet.handle) >= 0 ? " selectionne" : "");
      ligne.innerHTML = "<span class=\"nom-objet\">" + objet.nom
        + "</span><span class=\"compteur\">" + objet.type + "</span>";
      ligne.addEventListener("click", function (event) {
        if (event.shiftKey) {
          if (etat.selection.indexOf(objet.handle) < 0) {
            etat.selection.push(objet.handle);
          }
        } else {
          etat.selection = [objet.handle];
        }
        dessinerObjets();
        afficherProprietes(objet);
      });
      conteneur.appendChild(ligne);
    });
  }

  function afficherProprietes(objet) {
    var panneau = document.getElementById("proprietes");
    var lignes = [
      ["Identifiant", objet.handle], ["Nom", objet.nom], ["Type", objet.type],
      ["Calque", objet.calque], ["Materiau", objet.materiau]
    ];
    if (objet.geometrie) {
      Object.keys(objet.geometrie).forEach(function (cle) {
        var valeur = objet.geometrie[cle];
        if (valeur !== null && typeof valeur === "object") { return; }
        lignes.push([cle.replace(/_/g, " "), valeur]);
      });
    }
    if (objet.boite && objet.boite.taille) {
      lignes.push(["encombrement", objet.boite.taille.map(function (v) {
        return Math.round(v);
      }).join(" × ") + " mm"]);
    }
    panneau.innerHTML = "<table class=\"proprietes\">" + lignes.map(function (l) {
      return "<tr><td>" + l[0] + "</td><td>" + l[1] + "</td></tr>";
    }).join("") + "</table>";
  }

  /* --------------------------------------------------------- dialogues */
  function ouvrirDialogue(titre, contenu, actions) {
    document.getElementById("dialogue-titre").textContent = titre;
    var corps = document.getElementById("dialogue-corps");
    corps.innerHTML = "";
    corps.appendChild(contenu);
    var pied = document.getElementById("dialogue-pied");
    pied.innerHTML = "";
    (actions || []).forEach(function (action) {
      var bouton = document.createElement("button");
      bouton.textContent = action.libelle;
      if (action.primaire) { bouton.className = "primaire"; }
      bouton.addEventListener("click", action.action);
      pied.appendChild(bouton);
    });
    document.getElementById("voile").hidden = false;
  }

  function fermerDialogue() { document.getElementById("voile").hidden = true; }

  function dialogueExport() {
    var grille = document.createElement("div");
    grille.className = "grille-formats";
    etat.formats.filter(function (format) { return format.ecriture; })
      .forEach(function (format) {
        var carte = document.createElement("div");
        carte.className = "carte-format";
        carte.innerHTML = "<b>" + format.libelle + "</b><span>"
          + format.extensions.join(" ") + " · " + format.categorie + "</span>";
        carte.addEventListener("click", function () {
          fermerDialogue();
          telecharger(format.cle, format.extensions[0]);
        });
        grille.appendChild(carte);
      });
    ouvrirDialogue("Exporter le document", grille,
                   [{ libelle: "Annuler", action: fermerDialogue }]);
  }

  function telecharger(format, extension) {
    journaliser("export " + format + " en cours…");
    requete("/api/v1/cad/documents/" + etat.document + "/export", {
      method: "POST", body: { format: format, options: {} }, brut: true
    }).then(function (blob) {
      var lien = document.createElement("a");
      lien.href = URL.createObjectURL(blob);
      lien.download = (etat.nomDocument || "mercury") + extension;
      lien.click();
      URL.revokeObjectURL(lien.href);
      journaliser("export " + format + " termine (" + blob.size + " octets)",
                  "succes");
    }).catch(function (erreur) {
      journaliser("export " + format + " impossible — " + erreur.message,
                  "erreur");
    });
  }

  function dialogueConversion() {
    var conteneur = document.createElement("div");
    var champFichier = document.createElement("input");
    champFichier.type = "file";
    var selection = document.createElement("select");
    etat.formats.filter(function (f) { return f.ecriture; })
      .forEach(function (format) {
        var option = document.createElement("option");
        option.value = format.cle;
        option.textContent = format.libelle + " (" + format.extensions[0] + ")";
        selection.appendChild(option);
      });
    conteneur.innerHTML = "<p class=\"indication\">Convertit un fichier sans "
      + "l'ouvrir : DWG, DXF, IFC, STEP, STL, OBJ, glTF, PLY, 3MF, nuages de "
      + "points et images.</p>";
    var ligne1 = document.createElement("div");
    ligne1.className = "champ";
    ligne1.innerHTML = "<label>Fichier source</label>";
    ligne1.appendChild(champFichier);
    var ligne2 = document.createElement("div");
    ligne2.className = "champ";
    ligne2.innerHTML = "<label>Format cible</label>";
    ligne2.appendChild(selection);
    conteneur.appendChild(ligne1);
    conteneur.appendChild(ligne2);
    ouvrirDialogue("Convertir un fichier", conteneur, [
      { libelle: "Annuler", action: fermerDialogue },
      { libelle: "Convertir", primaire: true, action: function () {
        if (!champFichier.files.length) { return; }
        var donnees = new FormData();
        donnees.append("fichier", champFichier.files[0]);
        fermerDialogue();
        journaliser("conversion en cours…");
        fetch(API + "/api/v1/cad/files/convert?cible=" + selection.value,
              { method: "POST", body: donnees })
          .then(function (reponse) {
            if (!reponse.ok) { return reponse.json().then(function (e) {
              throw new Error(e.detail || "conversion impossible"); }); }
            return reponse.blob();
          })
          .then(function (blob) {
            var lien = document.createElement("a");
            lien.href = URL.createObjectURL(blob);
            lien.download = "converti." + selection.value;
            lien.click();
            journaliser("conversion terminee (" + blob.size + " octets)",
                        "succes");
          })
          .catch(function (erreur) {
            journaliser("conversion — " + erreur.message, "erreur");
          });
      } }
    ]);
  }

  function ouvrirFichier() {
    var champ = document.getElementById("fichier-cache");
    champ.value = "";
    champ.onchange = function () {
      if (!champ.files.length) { return; }
      var donnees = new FormData();
      donnees.append("fichier", champ.files[0]);
      journaliser("ouverture de " + champ.files[0].name + "…");
      fetch(API + "/api/v1/cad/files/open", { method: "POST", body: donnees })
        .then(function (reponse) { return reponse.json().then(function (data) {
          if (!reponse.ok) { throw new Error(data.detail || "ouverture impossible"); }
          return data;
        }); })
        .then(function (reponse) {
          etat.document = reponse.document;
          etat.nomDocument = champ.files[0].name.replace(/\.[^.]+$/, "");
          document.getElementById("titre-document").textContent = champ.files[0].name;
          journaliser("fichier " + reponse.format + " ouvert", "succes");
          appliquerEtat(reponse.etat);
          return rafraichirScene().then(function () { viewer.zoomExtents(); });
        })
        .catch(function (erreur) {
          journaliser("ouverture — " + erreur.message, "erreur");
        });
    };
    champ.click();
  }

  function nouveauDocument(nom) {
    return requete("/api/v1/cad/documents", {
      method: "POST", body: { nom: nom || "SansTitre", unites: "mm" }
    }).then(function (reponse) {
      etat.document = reponse.document;
      etat.nomDocument = nom || "SansTitre";
      etat.selection = [];
      document.getElementById("titre-document").textContent =
        (nom || "SansTitre") + ".json";
      appliquerEtat(reponse.etat);
      journaliser("nouveau document " + reponse.document, "succes");
      return rafraichirScene();
    });
  }

  /* ------------------------------------------------------- demarrage */
  function brancherInterface() {
    document.getElementById("executer").addEventListener("click", executerLigne);
    var champCommande = document.getElementById("commande");
    champCommande.addEventListener("keydown", function (event) {
      if (event.key === "Enter") { executerLigne(); }
      if (event.key === "ArrowUp" && etat.indexHistorique > 0) {
        etat.indexHistorique -= 1;
        champCommande.value = etat.historique[etat.indexHistorique] || "";
      }
      if (event.key === "ArrowDown") {
        etat.indexHistorique = Math.min(etat.historique.length,
                                        etat.indexHistorique + 1);
        champCommande.value = etat.historique[etat.indexHistorique] || "";
      }
    });

    Array.prototype.forEach.call(document.querySelectorAll("[data-fichier]"),
      function (bouton) {
        bouton.addEventListener("click", function () {
          var action = bouton.dataset.fichier;
          if (action === "nouveau") { nouveauDocument("SansTitre"); }
          if (action === "ouvrir") { ouvrirFichier(); }
          if (action === "enregistrer") { telecharger("json", ".json"); }
          if (action === "exporter") { dialogueExport(); }
          if (action === "convertir") { dialogueConversion(); }
        });
      });

    Array.prototype.forEach.call(document.querySelectorAll("[data-vue]"),
      function (bouton) {
        bouton.addEventListener("click", function () {
          viewer.setStandardView(bouton.dataset.vue);
          viewer.zoomExtents();
          majInfoVue();
        });
      });

    Array.prototype.forEach.call(document.querySelectorAll(".bascule"),
      function (bouton) {
        bouton.addEventListener("click", function () {
          var actif = !bouton.classList.contains("active");
          bouton.classList.toggle("active", actif);
          var variable = bouton.dataset.variable;
          if (variable === "GRILLE") { viewer.showGrid = actif; viewer.draw(); }
          if (variable === "ARETES") { viewer.showEdges = actif; viewer.draw(); }
          if (variable === "PERSPECTIVE") {
            viewer.perspective = actif; viewer.draw();
          }
          if (variable === "ORTHO") { executer("ORTHO", { actif: actif }); }
          if (variable === "RESOL") { executer("RESOL", { actif: actif }); }
        });
      });

    document.getElementById("style-visuel").addEventListener("change",
      function (event) {
        viewer.style = event.target.value;
        viewer.draw();
        journaliser("style visuel : " + event.target.value);
      });

    document.getElementById("ajouter-calque").addEventListener("click",
      function () {
        var nom = window.prompt("Nom du nouveau calque", "CALQUE1");
        if (nom) { executer("CALQUE", { nom: nom, couleur: 3 }); }
      });

    document.getElementById("fermer-dialogue")
      .addEventListener("click", fermerDialogue);
    window.addEventListener("resize", function () { viewer.draw(); });
  }

  function demarrer() {
    try {
      viewer = new window.MercuryViewer(document.getElementById("vue3d"));
    } catch (erreur) {
      journaliser("visionneuse 3D indisponible : " + erreur.message, "erreur");
      return;
    }
    viewer.onCameraChange = majInfoVue;
    brancherInterface();

    requete("/health").then(function (sante) {
      var pastille = document.getElementById("etat-api");
      pastille.textContent = "API " + sante.version;
      pastille.className = "pastille ok";
    }).catch(function () {
      var pastille = document.getElementById("etat-api");
      pastille.textContent = "API injoignable";
      pastille.className = "pastille ko";
    });

    Promise.all([requete("/api/v1/cad/commands"),
                 requete("/api/v1/cad/capabilities"),
                 requete("/api/v1/cad/formats")])
      .then(function (reponses) {
        etat.catalogue = reponses[0].commandes;
        etat.capacites = reponses[1];
        etat.formats = reponses[2].formats;
        var selecteur = document.getElementById("style-visuel");
        etat.capacites.styles_visuels.forEach(function (style) {
          var option = document.createElement("option");
          option.value = style;
          option.textContent = style.replace(/_/g, " ");
          if (style === "ombre_avec_aretes") { option.selected = true; }
          selecteur.appendChild(option);
        });
        construireOnglets();
        journaliser(etat.catalogue.length + " commandes et "
                    + etat.formats.length + " formats de fichiers charges",
                    "succes");
        return nouveauDocument("SansTitre");
      })
      .then(function () {
        return executer("BOITE", { longueur: 4000, largeur: 3000, hauteur: 2700 });
      })
      .then(function () { viewer.zoomExtents(); majInfoVue(); })
      .catch(function (erreur) {
        journaliser("demarrage — " + erreur.message, "erreur");
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }
}());
