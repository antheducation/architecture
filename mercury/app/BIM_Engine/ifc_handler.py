"""Export IFC4 au format STEP (livrable #14).

Ecrivain autonome couvrant ce qui compte pour l'echange : projet, site,
batiment, etage, murs avec leurs quantites de base et espaces. C'est le
sous-ensemble lu par tous les visualiseurs et par Revit, ArchiCAD, Tekla.
"""
from __future__ import annotations

import base64
import datetime
import hashlib
from typing import List


class IFCHandler:
    """Serialise un projet BIM en fichier IFC4."""

    def __init__(self) -> None:
        self._lines: List[str] = []
        self._counter = 0

    def _add(self, body: str) -> str:
        self._counter += 1
        reference = "#%d" % self._counter
        self._lines.append("%s= %s;" % (reference, body))
        return reference

    @staticmethod
    def _guid(seed: str) -> str:
        digest = hashlib.md5(seed.encode("utf-8")).digest()
        encoded = base64.b64encode(digest).decode()
        return encoded.replace("+", "_").replace("/", "$")[:22]

    @staticmethod
    def _escape(text: str) -> str:
        return (text or "").replace("'", "''").replace("\\", "")

    def export(self, project) -> str:
        self._lines, self._counter = [], 0
        org = self._add("IFCORGANIZATION($,'Mercury',$,$,$)")
        app = self._add("IFCAPPLICATION(%s,'1.0','MERCURY CAD AI X','MERCURY')" % org)
        person = self._add("IFCPERSON($,'Mercury','User',$,$,$,$,$)")
        po = self._add("IFCPERSONANDORGANIZATION(%s,%s,$)" % (person, org))
        stamp = int(datetime.datetime.now().timestamp())
        owner = self._add("IFCOWNERHISTORY(%s,%s,$,.ADDED.,%d,%s,%s,%d)"
                          % (po, app, stamp, po, app, stamp))

        dz = self._add("IFCDIRECTION((0.,0.,1.))")
        dx = self._add("IFCDIRECTION((1.,0.,0.))")
        origin = self._add("IFCCARTESIANPOINT((0.,0.,0.))")
        axis = self._add("IFCAXIS2PLACEMENT3D(%s,%s,%s)" % (origin, dz, dx))
        context = self._add(
            "IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,%s,$)" % axis)
        length_unit = self._add("IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.)")
        area_unit = self._add("IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.)")
        angle_unit = self._add("IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.)")
        units = self._add("IFCUNITASSIGNMENT((%s,%s,%s))"
                          % (length_unit, area_unit, angle_unit))
        placement = self._add("IFCLOCALPLACEMENT($,%s)" % axis)

        proj = self._add("IFCPROJECT('%s',%s,'%s',$,$,$,$,(%s),%s)"
                         % (self._guid(project.id), owner,
                            self._escape(project.name), context, units))
        site = self._add("IFCSITE('%s',%s,'Terrain',$,$,%s,$,$,.ELEMENT.,$,$,$,$,$)"
                         % (self._guid(project.id + "site"), owner, placement))
        building = self._add(
            "IFCBUILDING('%s',%s,'%s',$,$,%s,$,$,.ELEMENT.,$,$,$)"
            % (self._guid(project.id + "bld"), owner,
               self._escape(project.name), placement))
        storey = self._add(
            "IFCBUILDINGSTOREY('%s',%s,'%s',$,$,%s,$,$,.ELEMENT.,0.)"
            % (self._guid(project.levels[0].id), owner,
               self._escape(project.levels[0].name), placement))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid("a1"), owner, proj, site))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid("a2"), owner, site, building))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid("a3"), owner, building, storey))

        contained: List[str] = []
        for wall in project.walls:
            reference = self._wall(wall, owner, placement, context, dz)
            if reference:
                contained.append(reference)
        for room in project.rooms:
            reference = self._space(room, owner, placement, context, dz)
            if reference:
                contained.append(reference)
        if contained:
            self._add("IFCRELCONTAINEDINSPATIALSTRUCTURE('%s',%s,$,$,(%s),%s)"
                      % (self._guid("c1"), owner, ",".join(contained), storey))
        return self._dump(project.name)

    def _wall(self, wall, owner: str, placement: str, context: str, dz: str):
        length = wall.length
        if length < 1.0:
            return None
        ux = (wall.end[0] - wall.start[0]) / length
        uy = (wall.end[1] - wall.start[1]) / length
        p0 = self._add("IFCCARTESIANPOINT((%.3f,%.3f,0.))"
                       % (wall.start[0], wall.start[1]))
        direction = self._add("IFCDIRECTION((%.6f,%.6f,0.))" % (ux, uy))
        axis = self._add("IFCAXIS2PLACEMENT3D(%s,%s,%s)" % (p0, dz, direction))
        local = self._add("IFCLOCALPLACEMENT(%s,%s)" % (placement, axis))
        centre = self._add("IFCCARTESIANPOINT((%.3f,0.))" % (length / 2.0))
        d2 = self._add("IFCDIRECTION((1.,0.))")
        axis2 = self._add("IFCAXIS2PLACEMENT2D(%s,%s)" % (centre, d2))
        profile = self._add("IFCRECTANGLEPROFILEDEF(.AREA.,'mur',%s,%.3f,%.3f)"
                            % (axis2, length, wall.thickness))
        solid = self._add("IFCEXTRUDEDAREASOLID(%s,%s,%s,%.3f)"
                          % (profile, axis, dz, wall.height))
        shape = self._add("IFCSHAPEREPRESENTATION(%s,'Body','SweptSolid',(%s))"
                          % (context, solid))
        product = self._add("IFCPRODUCTDEFINITIONSHAPE($,$,(%s))" % shape)
        reference = self._add(
            "IFCWALLSTANDARDCASE('%s',%s,'Mur',$,$,%s,%s,$,$)"
            % (self._guid(wall.id), owner, local, product))
        self._quantities(wall, owner, reference)
        return reference

    def _quantities(self, wall, owner: str, reference: str) -> None:
        length = self._add("IFCQUANTITYLENGTH('Length',$,$,%.1f,$)" % wall.length)
        area = self._add("IFCQUANTITYAREA('NetSideArea',$,$,%.3f,$)"
                         % wall.net_area_m2)
        volume = self._add(
            "IFCQUANTITYVOLUME('NetVolume',$,$,%.3f,$)"
            % (wall.net_area_m2 * wall.thickness / 1000.0))
        quantity = self._add(
            "IFCELEMENTQUANTITY('%s',%s,'Qto_WallBaseQuantities',$,$,(%s,%s,%s))"
            % (self._guid(wall.id + "q"), owner, length, area, volume))
        self._add("IFCRELDEFINESBYPROPERTIES('%s',%s,$,$,(%s),%s)"
                  % (self._guid(wall.id + "r"), owner, reference, quantity))

    def _space(self, room, owner: str, placement: str, context: str, dz: str):
        if len(room.outline) < 3:
            return None
        points = [self._add("IFCCARTESIANPOINT((%.3f,%.3f))" % (p[0], p[1]))
                  for p in room.outline]
        polyline = self._add("IFCPOLYLINE((%s))" % ",".join(points + [points[0]]))
        profile = self._add("IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,$,%s)" % polyline)
        p0 = self._add("IFCCARTESIANPOINT((0.,0.,0.))")
        dx = self._add("IFCDIRECTION((1.,0.,0.))")
        axis = self._add("IFCAXIS2PLACEMENT3D(%s,%s,%s)" % (p0, dz, dx))
        local = self._add("IFCLOCALPLACEMENT(%s,%s)" % (placement, axis))
        solid = self._add("IFCEXTRUDEDAREASOLID(%s,%s,%s,%.3f)"
                          % (profile, axis, dz, room.height))
        shape = self._add("IFCSHAPEREPRESENTATION(%s,'Body','SweptSolid',(%s))"
                          % (context, solid))
        product = self._add("IFCPRODUCTDEFINITIONSHAPE($,$,(%s))" % shape)
        return self._add(
            "IFCSPACE('%s',%s,'%s',$,$,%s,%s,$,.ELEMENT.,$)"
            % (self._guid(room.id), owner, self._escape(room.name), local, product))

    def _dump(self, name: str) -> str:
        stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        header = (
            "ISO-10303-21;\nHEADER;\n"
            "FILE_DESCRIPTION((''),'2;1');\n"
            "FILE_NAME('%s','%s',(''),(''),'MERCURY CAD AI X','1.0','');\n"
            "FILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n" % (self._escape(name), stamp)
        )
        return header + "\n".join(self._lines) + "\nENDSEC;\nEND-ISO-10303-21;\n"

    # -----------------------------------------------------------------
    # Solides libres : passerelle avec le noyau CAO (module Interop)
    # -----------------------------------------------------------------
    def export_solids(self, solids, name: str = "MAQUETTE") -> str:
        """Ecrit des solides quelconques en IFC4, par faces (IfcFacetedBrep).

        Complete `export`, qui traite le modele BIM structure. Ici la
        geometrie vient du noyau CAO : murs modelises a la main, ouvrages
        d'art, pieces mecaniques, terrain. Tout devient un IfcBuildingElement
        proxy porteur d'une representation Brep, ce que lisent Revit,
        ArchiCAD, Tekla, Solibri et les visualiseurs IFC.
        """
        self._lines, self._counter = [], 0
        org = self._add("IFCORGANIZATION($,'Mercury',$,$,$)")
        person = self._add("IFCPERSON($,$,'MERCURY',$,$,$,$,$)")
        person_org = self._add("IFCPERSONANDORGANIZATION(%s,%s,$)"
                               % (person, org))
        application = self._add(
            "IFCAPPLICATION(%s,'1.0','MERCURY CAD AI X','MERCURY')" % org)
        stamp = int(datetime.datetime.now().timestamp())
        owner = self._add("IFCOWNERHISTORY(%s,%s,$,.ADDED.,$,$,$,%d)"
                          % (person_org, application, stamp))
        origin = self._add("IFCCARTESIANPOINT((0.,0.,0.))")
        axis = self._add("IFCDIRECTION((0.,0.,1.))")
        reference = self._add("IFCDIRECTION((1.,0.,0.))")
        placement = self._add("IFCAXIS2PLACEMENT3D(%s,%s,%s)"
                              % (origin, axis, reference))
        local = self._add("IFCLOCALPLACEMENT($,%s)" % placement)
        length_unit = self._add("IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.)")
        area_unit = self._add("IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.)")
        volume_unit = self._add("IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.)")
        units = self._add("IFCUNITASSIGNMENT((%s,%s,%s))"
                          % (length_unit, area_unit, volume_unit))
        context = self._add(
            "IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,%s,$)"
            % placement)
        project = self._add("IFCPROJECT('%s',%s,'%s',$,$,$,$,(%s),%s)"
                            % (self._guid(name), owner, self._escape(name),
                               context, units))
        site = self._add("IFCSITE('%s',%s,'Site',$,$,%s,$,$,.ELEMENT.,$,$,$,$,$)"
                         % (self._guid(name + "site"), owner, local))
        building = self._add(
            "IFCBUILDING('%s',%s,'Batiment',$,$,%s,$,$,.ELEMENT.,$,$,$)"
            % (self._guid(name + "bat"), owner, local))
        storey = self._add(
            "IFCBUILDINGSTOREY('%s',%s,'Niveau 0',$,$,%s,$,$,.ELEMENT.,0.)"
            % (self._guid(name + "niv"), owner, local))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid(name + "ra1"), owner, project, site))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid(name + "ra2"), owner, site, building))
        self._add("IFCRELAGGREGATES('%s',%s,$,$,%s,(%s))"
                  % (self._guid(name + "ra3"), owner, building, storey))

        products: List[str] = []
        for order, solid in enumerate(solids):
            brep = self._faceted_brep(solid)
            representation = self._add(
                "IFCSHAPEREPRESENTATION(%s,'Body','Brep',(%s))"
                % (context, brep))
            shape = self._add("IFCPRODUCTDEFINITIONSHAPE($,$,(%s))"
                              % representation)
            label = self._escape(getattr(solid, "name", "") or "Solide%d" % order)
            products.append(self._add(
                "IFCBUILDINGELEMENTPROXY('%s',%s,'%s',$,$,%s,%s,$,$)"
                % (self._guid("%s-%d" % (name, order)), owner, label, local,
                   shape)))
        if products:
            self._add("IFCRELCONTAINEDINSPATIALSTRUCTURE('%s',%s,$,$,(%s),%s)"
                      % (self._guid(name + "rel"), owner, ",".join(products),
                         storey))
        return self._dump(name)

    def _faceted_brep(self, solid) -> str:
        """Traduit un solide facettise en IFCFACETEDBREP."""
        points: dict = {}
        faces: List[str] = []
        for polygon in solid.polygons:
            if polygon.is_degenerate():
                continue
            references: List[str] = []
            for vertex in polygon.vertices:
                key = vertex.rounded(5)
                if key not in points:
                    points[key] = self._add(
                        "IFCCARTESIANPOINT((%.5f,%.5f,%.5f))"
                        % (vertex.x, vertex.y, vertex.z))
                references.append(points[key])
            loop = self._add("IFCPOLYLOOP((%s))" % ",".join(references))
            bound = self._add("IFCFACEOUTERBOUND(%s,.T.)" % loop)
            faces.append(self._add("IFCFACE((%s))" % bound))
        shell = self._add("IFCCLOSEDSHELL((%s))" % ",".join(faces))
        return self._add("IFCFACETEDBREP(%s)" % shell)

    def read_solids(self, text: str, name: str = "ifc"):
        """Relit les volumes d'un IFC facettise (IFCFACETEDBREP).

        Couvre les fichiers produits par `export_solids` ainsi que les IFC
        exportes en representation Brep par les logiciels BIM courants. Les
        representations parametriques (extrusions, revolutions) sont
        signalees mais non reconstruites.
        """
        import re as _re

        from CAD_Core.math3d import Vec3
        from CAD_Core.solid import Polygon, Solid

        body = text.split("DATA;", 1)[1] if "DATA;" in text else text
        entities: dict = {}
        for statement in body.split(";"):
            match = _re.match(r"\s*#(\d+)\s*=\s*([A-Z0-9]+)\s*\((.*)\)\s*$",
                              statement.replace("\n", " "), _re.IGNORECASE | _re.S)
            if match:
                entities[int(match.group(1))] = (match.group(2).upper(),
                                                 match.group(3))
        points = {}
        for key, (kind, payload) in entities.items():
            if kind == "IFCCARTESIANPOINT":
                numbers = _re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", payload)
                if len(numbers) >= 3:
                    points[key] = Vec3(float(numbers[0]), float(numbers[1]),
                                       float(numbers[2]))
        loops = {}
        for key, (kind, payload) in entities.items():
            if kind == "IFCPOLYLOOP":
                refs = [int(r) for r in _re.findall(r"#(\d+)", payload)]
                ring = [points[r] for r in refs if r in points]
                if len(ring) >= 3:
                    loops[key] = ring
        polygons = []
        for key, (kind, payload) in entities.items():
            if kind in ("IFCFACEOUTERBOUND", "IFCFACEBOUND"):
                for ref in (int(r) for r in _re.findall(r"#(\d+)", payload)):
                    if ref in loops:
                        polygons.append(Polygon(list(loops[ref])))
                        break
        if not polygons:
            extruded = sum(1 for kind, _ in entities.values()
                           if kind == "IFCEXTRUDEDAREASOLID")
            raise ValueError(
                "cet IFC decrit %d volumes en representation parametrique ; "
                "MERCURY relit les representations Brep. Reexportez avec "
                "l'option Brep, ou utilisez l'import du modele BIM structure."
                % extruded if extruded else
                "aucune geometrie Brep exploitable dans cet IFC")
        return [Solid.from_polygons(polygons, name=name).heal()]
