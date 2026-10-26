async function request(path, options) {
  const res = await fetch(`/api${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  listIncidents: (filters) => {
    const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v));
    return request(`/incidents?${params}`);
  },
  getIncident: (id) => request(`/incidents/${id}`),
  getSuggestions: (id) => request(`/incidents/${id}/suggestions`),
  acknowledge: (id) => request(`/incidents/${id}/acknowledge`, { method: "POST" }),
  resolve: (id) => request(`/incidents/${id}/resolve`, { method: "POST" }),
  stats: () => request("/stats"),
};
