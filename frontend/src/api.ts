const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export function token() {
  return localStorage.getItem("soc_token") || "";
}

async function request(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${token()}`);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res.json();
}

async function downloadFile(path: string, filename: string) {
  const res = await fetch(`${API}${path}`, {
    headers: {
      Authorization: `Bearer ${token()}`,
    },
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}

export const api = {
  login: (username: string, password: string) =>
    fetch(`${API}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    }).then(async (res) => {
      if (!res.ok) {
        throw new Error("Invalid credentials");
      }
      return res.json();
    }),

  summary: () => request("/api/dashboard/summary"),

  events: () => request("/api/events?limit=100"),

  alerts: () => request("/api/alerts"),

  incidents: () => request("/api/incidents"),

  rules: () => request("/api/rules"),

  acknowledge: (id: number) =>
    request(`/api/alerts/${id}/ack`, { method: "POST" }),

  closeAlert: (id: number) =>
    request(`/api/alerts/${id}/close`, { method: "POST" }),

  createIncident: (data: unknown) =>
    request("/api/incidents", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  threatIP: (ip: string) =>
    request(`/api/threat-intel/ip/${encodeURIComponent(ip)}`),

  // Download a PDF report for one security event
  eventReport: (id: number) =>
    downloadFile(
      `/api/events/${id}/report`,
      `SOC_Event_${id}_Report.pdf`,
    ),
};

export const WS =
  import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000";
  
