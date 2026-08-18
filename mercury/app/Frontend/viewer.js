/* Visionneuse 3D WebGL de MERCURY CAD AI X.
 *
 * Rendu temps reel du modele : faces ombrees, aretes, grille, axes du SCU,
 * orbite, panoramique et zoom. Aucune bibliotheque externe : le fichier est
 * autonome, ce qui evite toute dependance reseau au demarrage.
 */
(function (global) {
  "use strict";

  /* ---------------------------------------------------------------- maths */
  var M4 = {
    identity: function () {
      return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
    },
    multiply: function (a, b) {
      var out = new Float32Array(16), i, j, k, sum;
      for (i = 0; i < 4; i++) {
        for (j = 0; j < 4; j++) {
          sum = 0;
          for (k = 0; k < 4; k++) { sum += a[k * 4 + j] * b[i * 4 + k]; }
          out[i * 4 + j] = sum;
        }
      }
      return out;
    },
    perspective: function (fovy, aspect, near, far) {
      var f = 1 / Math.tan(fovy / 2), d = near - far;
      return new Float32Array([f / aspect,0,0,0, 0,f,0,0,
        0,0,(far + near) / d,-1, 0,0,(2 * far * near) / d,0]);
    },
    ortho: function (halfWidth, halfHeight, near, far) {
      var d = far - near;
      return new Float32Array([1 / halfWidth,0,0,0, 0,1 / halfHeight,0,0,
        0,0,-2 / d,0, 0,0,-(far + near) / d,1]);
    },
    lookAt: function (eye, target, up) {
      var z = normalize(sub(eye, target));
      var x = normalize(cross(up, z));
      var y = cross(z, x);
      return new Float32Array([
        x[0], y[0], z[0], 0,
        x[1], y[1], z[1], 0,
        x[2], y[2], z[2], 0,
        -dot(x, eye), -dot(y, eye), -dot(z, eye), 1]);
    }
  };

  function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
  function add(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; }
  function scale(a, k) { return [a[0] * k, a[1] * k, a[2] * k]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function cross(a, b) {
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]];
  }
  function length(a) { return Math.sqrt(dot(a, a)); }
  function normalize(a) {
    var n = length(a);
    return n < 1e-9 ? [0, 0, 0] : [a[0] / n, a[1] / n, a[2] / n];
  }

  /* --------------------------------------------------------------- nuances */
  var FACE_VERTEX = [
    "attribute vec3 aPosition;",
    "attribute vec3 aNormal;",
    "attribute vec3 aColor;",
    "uniform mat4 uProjection;",
    "uniform mat4 uView;",
    "varying vec3 vNormal;",
    "varying vec3 vColor;",
    "varying vec3 vWorld;",
    "void main() {",
    "  vNormal = aNormal;",
    "  vColor = aColor;",
    "  vWorld = aPosition;",
    "  gl_Position = uProjection * uView * vec4(aPosition, 1.0);",
    "}"
  ].join("\n");

  var FACE_FRAGMENT = [
    "precision mediump float;",
    "varying vec3 vNormal;",
    "varying vec3 vColor;",
    "varying vec3 vWorld;",
    "uniform vec3 uEye;",
    "uniform float uMode;",   /* 0 realiste, 1 conceptuel, 2 rayons X, 3 gris */
    "uniform float uOpacity;",
    "void main() {",
    "  vec3 n = normalize(vNormal);",
    "  vec3 key = normalize(vec3(0.45, 0.55, 0.75));",
    "  vec3 fill = normalize(vec3(-0.6, -0.35, 0.4));",
    "  float d = max(dot(n, key), 0.0) * 0.85 + max(dot(n, fill), 0.0) * 0.3;",
    "  vec3 base = vColor;",
    "  if (uMode > 2.5) { float g = dot(base, vec3(0.299, 0.587, 0.114));",
    "    base = vec3(g); }",
    "  vec3 color = base * (0.32 + d);",
    "  if (uMode > 0.5 && uMode < 1.5) {",
    "    float t = clamp(0.5 + 0.5 * dot(n, key), 0.0, 1.0);",
    "    color = mix(vec3(0.29, 0.38, 0.58), vec3(1.0, 0.84, 0.55), t);",
    "    color = mix(color, base, 0.35);",
    "  }",
    "  vec3 view = normalize(uEye - vWorld);",
    "  float rim = pow(1.0 - max(dot(n, view), 0.0), 3.0) * 0.25;",
    "  gl_FragColor = vec4(color + rim, uOpacity);",
    "}"
  ].join("\n");

  var LINE_VERTEX = [
    "attribute vec3 aPosition;",
    "attribute vec3 aColor;",
    "uniform mat4 uProjection;",
    "uniform mat4 uView;",
    "varying vec3 vColor;",
    "void main() {",
    "  vColor = aColor;",
    "  vec4 p = uProjection * uView * vec4(aPosition, 1.0);",
    "  p.z -= 0.0008 * p.w;",   /* les aretes passent devant les faces */
    "  gl_Position = p;",
    "}"
  ].join("\n");

  var LINE_FRAGMENT = [
    "precision mediump float;",
    "varying vec3 vColor;",
    "uniform float uOpacity;",
    "void main() { gl_FragColor = vec4(vColor, uOpacity); }"
  ].join("\n");

  var MATERIALS = {
    "default": [0.78, 0.78, 0.76], "maconnerie": [0.85, 0.82, 0.77],
    "cloison": [0.90, 0.89, 0.86], "beton": [0.72, 0.72, 0.70],
    "acier": [0.55, 0.59, 0.63], "bois": [0.66, 0.47, 0.28],
    "verre": [0.66, 0.80, 0.86], "isolant": [0.91, 0.80, 0.51],
    "mobilier": [0.55, 0.40, 0.28], "terre": [0.59, 0.48, 0.35],
    "metal": [0.67, 0.69, 0.71], "plastique": [0.78, 0.78, 0.82]
  };

  var STYLE_MODES = {
    "realiste": 0, "ombre_avec_aretes": 0, "conceptuel": 1, "cache": 0,
    "rayons_x": 2, "nuances_de_gris": 3, "esquisse": 0,
    "filaire_3d": 0, "filaire_2d": 0
  };

  /* ------------------------------------------------------------- visionneuse */
  function Viewer(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext("webgl", { antialias: true, alpha: false })
      || canvas.getContext("experimental-webgl", { antialias: true });
    if (!this.gl) { throw new Error("WebGL indisponible sur ce navigateur"); }
    this.target = [0, 0, 0];
    this.distance = 10000;
    this.azimuth = 315;
    this.elevation = 30;
    this.perspective = false;
    this.style = "ombre_avec_aretes";
    this.showGrid = true;
    this.showEdges = true;
    this.showAxes = true;
    this.selection = [];
    this.groups = [];
    this.box = null;
    this.counts = { faces: 0, edges: 0, grid: 0 };
    this._setup();
    this._bind();
  }

  Viewer.prototype._setup = function () {
    var gl = this.gl;
    this.faceProgram = buildProgram(gl, FACE_VERTEX, FACE_FRAGMENT);
    this.lineProgram = buildProgram(gl, LINE_VERTEX, LINE_FRAGMENT);
    this.buffers = {
      position: gl.createBuffer(), normal: gl.createBuffer(),
      color: gl.createBuffer(), edge: gl.createBuffer(),
      edgeColor: gl.createBuffer(), grid: gl.createBuffer(),
      gridColor: gl.createBuffer()
    };
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  };

  Viewer.prototype._bind = function () {
    var self = this, dragging = null, last = null;
    this.canvas.addEventListener("contextmenu", function (event) {
      event.preventDefault();
    });
    this.canvas.addEventListener("mousedown", function (event) {
      dragging = event.button === 0 && !event.shiftKey ? "orbite" : "pan";
      last = [event.clientX, event.clientY];
      event.preventDefault();
    });
    global.addEventListener("mouseup", function () { dragging = null; });
    global.addEventListener("mousemove", function (event) {
      if (!dragging || !last) { return; }
      var dx = event.clientX - last[0], dy = event.clientY - last[1];
      last = [event.clientX, event.clientY];
      if (dragging === "orbite") {
        self.azimuth = (self.azimuth - dx * 0.4 + 360) % 360;
        self.elevation = Math.max(-89, Math.min(89, self.elevation + dy * 0.4));
      } else {
        var factor = self.distance / Math.max(1, self.canvas.height);
        var frame = self.frame();
        self.target = add(self.target,
          add(scale(frame.right, -dx * factor), scale(frame.up, dy * factor)));
      }
      self.draw();
      if (self.onCameraChange) { self.onCameraChange(self.cameraState()); }
    });
    this.canvas.addEventListener("wheel", function (event) {
      event.preventDefault();
      self.distance *= event.deltaY > 0 ? 1.12 : 0.89;
      self.distance = Math.max(1, Math.min(1e8, self.distance));
      self.draw();
      if (self.onCameraChange) { self.onCameraChange(self.cameraState()); }
    }, { passive: false });
  };

  Viewer.prototype.frame = function () {
    var a = this.azimuth * Math.PI / 180, e = this.elevation * Math.PI / 180;
    var eye = add(this.target, [
      this.distance * Math.cos(e) * Math.cos(a),
      this.distance * Math.cos(e) * Math.sin(a),
      this.distance * Math.sin(e)]);
    var forward = normalize(sub(this.target, eye));
    var reference = Math.abs(forward[2]) > 0.999 ? [0, 1, 0] : [0, 0, 1];
    var right = normalize(cross(forward, reference));
    return { eye: eye, forward: forward, right: right,
             up: normalize(cross(right, forward)) };
  };

  Viewer.prototype.cameraState = function () {
    return { azimut: Math.round(this.azimuth * 10) / 10,
             elevation: Math.round(this.elevation * 10) / 10,
             distance: Math.round(this.distance) };
  };

  Viewer.prototype.setStandardView = function (name) {
    var views = {
      dessus: [0, 89.9], dessous: [0, -89.9], face: [270, 0], arriere: [90, 0],
      gauche: [180, 0], droite: [0, 0], iso_sud_ouest: [225, 35.264],
      iso_sud_est: [315, 35.264], iso_nord_est: [45, 35.264],
      iso_nord_ouest: [135, 35.264]
    };
    var view = views[name] || views.iso_sud_ouest;
    this.azimuth = view[0];
    this.elevation = view[1];
    this.draw();
  };

  Viewer.prototype.zoomExtents = function () {
    if (!this.box) { return; }
    var size = this.box.taille || [1000, 1000, 1000];
    this.target = this.box.centre || [0, 0, 0];
    var radius = Math.max(1, length(size) / 2);
    this.distance = radius * 2.6;
    this.draw();
  };

  Viewer.prototype.load = function (mesh) {
    var gl = this.gl;
    var positions = mesh.positions || [], normals = mesh.normales || [];
    var colors = new Float32Array(positions.length);
    this.groups = mesh.groupes || [];
    this.box = mesh.boite && !mesh.boite.vide ? mesh.boite : null;
    var index = 0, g, color, k;
    for (g = 0; g < this.groups.length; g++) {
      color = MATERIALS[this.groups[g].materiau] || MATERIALS["default"];
      for (k = 0; k < this.groups[g].sommets; k++) {
        colors[index * 3] = color[0];
        colors[index * 3 + 1] = color[1];
        colors[index * 3 + 2] = color[2];
        index += 1;
      }
    }
    while (index < positions.length / 3) {
      colors[index * 3] = 0.78;
      colors[index * 3 + 1] = 0.78;
      colors[index * 3 + 2] = 0.76;
      index += 1;
    }
    upload(gl, this.buffers.position, new Float32Array(positions));
    upload(gl, this.buffers.normal, new Float32Array(normals));
    upload(gl, this.buffers.color, colors);
    this.counts.faces = positions.length / 3;

    var edges = mesh.aretes || [];
    var edgeColors = new Float32Array(edges.length);
    for (k = 0; k < edges.length / 3; k++) {
      edgeColors[k * 3] = 0.09;
      edgeColors[k * 3 + 1] = 0.11;
      edgeColors[k * 3 + 2] = 0.14;
    }
    upload(gl, this.buffers.edge, new Float32Array(edges));
    upload(gl, this.buffers.edgeColor, edgeColors);
    this.counts.edges = edges.length / 3;
    this._buildGrid();
    this.draw();
  };

  Viewer.prototype.loadCurves = function (curves) {
    var points = [], colors = [], i, j, list;
    for (i = 0; i < curves.length; i++) {
      list = curves[i].points || [];
      for (j = 0; j + 1 < list.length; j++) {
        points.push(list[j][0], list[j][1], list[j][2]);
        points.push(list[j + 1][0], list[j + 1][1], list[j + 1][2]);
        colors.push(0.16, 0.42, 0.70, 0.16, 0.42, 0.70);
      }
      if (curves[i].ferme && list.length > 2) {
        points.push(list[list.length - 1][0], list[list.length - 1][1],
                    list[list.length - 1][2]);
        points.push(list[0][0], list[0][1], list[0][2]);
        colors.push(0.16, 0.42, 0.70, 0.16, 0.42, 0.70);
      }
    }
    this.curvePoints = new Float32Array(points);
    this.curveColors = new Float32Array(colors);
    if (!this.buffers.curve) {
      this.buffers.curve = this.gl.createBuffer();
      this.buffers.curveColor = this.gl.createBuffer();
    }
    upload(this.gl, this.buffers.curve, this.curvePoints);
    upload(this.gl, this.buffers.curveColor, this.curveColors);
    this.counts.curves = points.length / 3;
    this.draw();
  };

  Viewer.prototype._buildGrid = function () {
    var size = this.box ? Math.max(this.box.taille[0], this.box.taille[1]) : 5000;
    var step = Math.pow(10, Math.round(Math.log(size / 10) / Math.LN10));
    var extent = Math.max(step * 12, size * 1.5);
    var lines = [], colors = [], value, strong;
    for (value = -extent; value <= extent + 1e-6; value += step) {
      strong = Math.abs(value) < step * 0.5;
      lines.push(-extent, value, 0, extent, value, 0);
      lines.push(value, -extent, 0, value, extent, 0);
      var tone = strong ? [0.30, 0.34, 0.40] : [0.18, 0.20, 0.24];
      colors.push(tone[0], tone[1], tone[2], tone[0], tone[1], tone[2]);
      colors.push(tone[0], tone[1], tone[2], tone[0], tone[1], tone[2]);
    }
    if (this.showAxes) {
      var axis = extent * 0.25;
      lines.push(0, 0, 0, axis, 0, 0); colors.push(0.85, 0.24, 0.24, 0.85, 0.24, 0.24);
      lines.push(0, 0, 0, 0, axis, 0); colors.push(0.30, 0.75, 0.35, 0.30, 0.75, 0.35);
      lines.push(0, 0, 0, 0, 0, axis); colors.push(0.28, 0.52, 0.95, 0.28, 0.52, 0.95);
    }
    upload(this.gl, this.buffers.grid, new Float32Array(lines));
    upload(this.gl, this.buffers.gridColor, new Float32Array(colors));
    this.counts.grid = lines.length / 3;
    this.gridStep = step;
  };

  Viewer.prototype.resize = function () {
    var ratio = global.devicePixelRatio || 1;
    var width = Math.floor(this.canvas.clientWidth * ratio);
    var height = Math.floor(this.canvas.clientHeight * ratio);
    if (width < 1 || height < 1) { return; }
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    this.gl.viewport(0, 0, width, height);
  };

  Viewer.prototype.draw = function () {
    var gl = this.gl;
    this.resize();
    var aspect = this.canvas.width / Math.max(1, this.canvas.height);
    var frame = this.frame();
    var view = M4.lookAt(frame.eye, this.target, [0, 0, 1]);
    var near = Math.max(1, this.distance * 0.002);
    var far = this.distance * 40;
    var projection = this.perspective
      ? M4.perspective(45 * Math.PI / 180, aspect, near, far)
      : M4.ortho(this.distance * 0.5 * aspect, this.distance * 0.5, -far, far);

    var background = this.style === "esquisse" ? [0.99, 0.98, 0.96, 1]
      : (this.style === "cache" || this.style === "filaire_2d"
         || this.style === "nuances_de_gris")
        ? [0.96, 0.96, 0.97, 1] : [0.09, 0.11, 0.14, 1];
    gl.clearColor(background[0], background[1], background[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    if (this.showGrid && this.counts.grid) {
      this._drawLines(this.buffers.grid, this.buffers.gridColor,
                      this.counts.grid, projection, view, 0.75);
    }
    var wireframe = this.style === "filaire_3d" || this.style === "filaire_2d";
    if (!wireframe && this.counts.faces) {
      gl.useProgram(this.faceProgram);
      bindAttribute(gl, this.faceProgram, "aPosition", this.buffers.position, 3);
      bindAttribute(gl, this.faceProgram, "aNormal", this.buffers.normal, 3);
      bindAttribute(gl, this.faceProgram, "aColor", this.buffers.color, 3);
      gl.uniformMatrix4fv(uniform(gl, this.faceProgram, "uProjection"), false,
                          projection);
      gl.uniformMatrix4fv(uniform(gl, this.faceProgram, "uView"), false, view);
      gl.uniform3fv(uniform(gl, this.faceProgram, "uEye"),
                    new Float32Array(frame.eye));
      gl.uniform1f(uniform(gl, this.faceProgram, "uMode"),
                   STYLE_MODES[this.style] || 0);
      gl.uniform1f(uniform(gl, this.faceProgram, "uOpacity"),
                   this.style === "rayons_x" ? 0.45 : 1.0);
      if (this.style === "rayons_x") { gl.disable(gl.CULL_FACE); }
      gl.drawArrays(gl.TRIANGLES, 0, this.counts.faces);
      if (this.style === "rayons_x") { gl.enable(gl.CULL_FACE); }
    }
    if ((this.showEdges || wireframe) && this.counts.edges) {
      this._drawLines(this.buffers.edge, this.buffers.edgeColor,
                      this.counts.edges, projection, view,
                      wireframe ? 1.0 : 0.55);
    }
    if (this.counts.curves) {
      this._drawLines(this.buffers.curve, this.buffers.curveColor,
                      this.counts.curves, projection, view, 1.0);
    }
  };

  Viewer.prototype._drawLines = function (buffer, colorBuffer, count,
                                          projection, view, opacity) {
    var gl = this.gl;
    gl.useProgram(this.lineProgram);
    bindAttribute(gl, this.lineProgram, "aPosition", buffer, 3);
    bindAttribute(gl, this.lineProgram, "aColor", colorBuffer, 3);
    gl.uniformMatrix4fv(uniform(gl, this.lineProgram, "uProjection"), false,
                        projection);
    gl.uniformMatrix4fv(uniform(gl, this.lineProgram, "uView"), false, view);
    gl.uniform1f(uniform(gl, this.lineProgram, "uOpacity"), opacity);
    gl.drawArrays(gl.LINES, 0, count);
  };

  /* ------------------------------------------------------------ utilitaires */
  function buildProgram(gl, vertexSource, fragmentSource) {
    var program = gl.createProgram();
    gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, vertexSource));
    gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, fragmentSource));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error("edition de liens WebGL : " + gl.getProgramInfoLog(program));
    }
    return program;
  }

  function compile(gl, type, source) {
    var shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      throw new Error("compilation WebGL : " + gl.getShaderInfoLog(shader));
    }
    return shader;
  }

  function upload(gl, buffer, data) {
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
  }

  function bindAttribute(gl, program, name, buffer, size) {
    var location = gl.getAttribLocation(program, name);
    if (location < 0) { return; }
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.enableVertexAttribArray(location);
    gl.vertexAttribPointer(location, size, gl.FLOAT, false, 0, 0);
  }

  var uniformCache = new WeakMap();
  function uniform(gl, program, name) {
    var table = uniformCache.get(program);
    if (!table) { table = {}; uniformCache.set(program, table); }
    if (!(name in table)) { table[name] = gl.getUniformLocation(program, name); }
    return table[name];
  }

  global.MercuryViewer = Viewer;
}(window));
