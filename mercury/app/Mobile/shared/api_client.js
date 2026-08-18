/* Client API partage iOS / Android (livrable #63).
   Aucune logique metier : uniquement le transport, la file hors ligne et
   la gestion des erreurs. */
class MercuryClient {
  constructor(baseUrl, token) {
    if (!baseUrl) throw new Error("URL de l'API requise");
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.token = token || null;
    this.queue = [];
  }

  headers() {
    const h = { "Content-Type": "application/json" };
    if (this.token) h.Authorization = "Bearer " + this.token;
    return h;
  }

  async request(path, method = "GET", body = null) {
    const options = { method, headers: this.headers() };
    if (body) options.body = JSON.stringify(body);
    try {
      const response = await fetch(this.baseUrl + path, options);
      if (!response.ok) throw new Error("HTTP " + response.status);
      return await response.json();
    } catch (error) {
      if (method !== "GET") {
        this.queue.push({ path, method, body });   // renvoi differe
      }
      throw error;
    }
  }

  health() { return this.request("/health"); }
  projects() { return this.request("/api/v1/projects"); }
  project(id) { return this.request("/api/v1/projects/" + id); }
  takeoff(id) { return this.request("/api/v1/projects/" + id + "/takeoff"); }
  estimate(id) { return this.request("/api/v1/projects/" + id + "/estimate"); }
  twin(id) { return this.request("/api/v1/projects/" + id + "/twin"); }

  pushReadings(readings) {
    return this.request("/api/v1/iot/readings", "POST", { mesures: readings });
  }

  async flush() {
    const pending = this.queue.splice(0);
    const results = [];
    for (const item of pending) {
      try {
        results.push(await this.request(item.path, item.method, item.body));
      } catch (error) {
        this.queue.push(item);            // on garde pour le prochain essai
      }
    }
    return { envoyes: results.length, en_attente: this.queue.length };
  }
}

if (typeof module !== "undefined") module.exports = MercuryClient;
