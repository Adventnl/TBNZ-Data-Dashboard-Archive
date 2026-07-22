const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

async function request(url, options = {}) {
  const isFormData = options.body instanceof FormData;

  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

function toQueryString(params = {}) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    searchParams.append(key, String(value));
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

// Client APIs
export const clientsAPI = {
  getOverview: (params = {}) =>
    request(`/clients/overview${toQueryString(params)}`),
  getSignals: (params = {}) =>
    request(`/clients/signals${toQueryString(params)}`),
  pushToSales: (uid, payload = {}) =>
    request(`/clients/${encodeURIComponent(uid)}/push-to-sales`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getDetail: (uid) => request(`/clients/${encodeURIComponent(uid)}/detail`),
};

// Trading APIs
export const tradingAPI = {
  getOverview: (params = {}) =>
    request(`/trading/overview${toQueryString(params)}`),
  getTrends: (params = {}) =>
    request(`/trading/trends${toQueryString(params)}`),
  getCategories: (params = {}) =>
    request(`/trading/categories${toQueryString(params)}`),
  getTopContributors: (params = {}) =>
    request(`/trading/top-contributors${toQueryString(params)}`),
};

// AUC APIs
export const aucAPI = {
  getMonthOptions: (params = {}) =>
    request(`/auc/month-options${toQueryString(params)}`),
  getOverview: (params = {}) =>
    request(`/auc/overview${toQueryString(params)}`),
  getTrends: (params = {}) =>
    request(`/auc/trends${toQueryString(params)}`),
  getTierDistribution: (params = {}) =>
    request(`/auc/tier-distribution${toQueryString(params)}`),
  getAssetAllocation: (params = {}) =>
    request(`/auc/asset-allocation${toQueryString(params)}`),
  getTopClients: (params = {}) =>
    request(`/auc/top-clients${toQueryString(params)}`),
};

// Rankings APIs
export const rankingsAPI = {
  getOverview: (params = {}) =>
    request(`/rankings/overview${toQueryString(params)}`),
  getMovements: (params = {}) =>
    request(`/rankings/movements${toQueryString(params)}`),
  getTop500Trading: (params = {}) =>
    request(`/rankings/top500-trading${toQueryString(params)}`),
  getTop500Auc: (params = {}) =>
    request(`/rankings/top500-auc${toQueryString(params)}`),
};

// Map APIs
export const mapAPI = {
  getHeatmapData: (params = {}) =>
    request(`/map/heatmap-data${toQueryString(params)}`),
  getRoiRanking: (params = {}) =>
    request(`/map/roi-ranking${toQueryString(params)}`),
  getAgeDistribution: (params = {}) =>
    request(`/map/age-distribution${toQueryString(params)}`),
};

// Activities APIs
export const activitiesAPI = {
  getList: (params = {}) => request(`/activities${toQueryString(params)}`),
  getDetail: (id) => request(`/activities/${encodeURIComponent(id)}`),
  getTrend: (id) => request(`/activities/${encodeURIComponent(id)}/trend`),
  getTracking: (id, params = {}) =>
    request(
      `/activities/${encodeURIComponent(id)}/tracking${toQueryString(params)}`,
    ),
};

// Data Import APIs
export const importAPI = {
  uploadExcel: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request("/import/upload", {
      method: "POST",
      body: formData,
    });
  },
};
