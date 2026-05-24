const API_KEY_STORAGE = "tbot_api_key";

export type TimelineEvent = {
  at: string;
  type: string;
  title: string;
  detail: Record<string, unknown>;
};

export function getApiKey(): string {
  return localStorage.getItem(API_KEY_STORAGE) || "";
}

export function setApiKey(key: string) {
  localStorage.setItem(API_KEY_STORAGE, key);
}

async function fetchApi<T>(path: string): Promise<T> {
  const key = getApiKey();
  const res = await fetch(`/api${path}`, {
    headers: { "X-API-Key": key },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  weight: (days = 90) => fetchApi<{ data: { date: string; weight: number }[] }>(`/metrics/weight?days=${days}`),
  checkins: (days = 30) =>
    fetchApi<{ data: Record<string, unknown>[] }>(`/metrics/checkins?days=${days}`),
  calories: (days = 30) =>
    fetchApi<{ data: { date: string; calories: number }[] }>(`/metrics/calories?days=${days}`),
  heatmap: (days = 90) =>
    fetchApi<{ checkins: string[]; workouts: string[] }>(`/metrics/consistency/heatmap?days=${days}`),
  tokens: (days = 7) =>
    fetchApi<{ total_tokens: number; estimated_cost_usd: number }>(`/metrics/tokens?days=${days}`),
  timeline: (days = 30) =>
    fetchApi<{ data: TimelineEvent[] }>(`/timeline?days=${days}`),
  weeklySummary: () => fetchApi<{ summary: string | null }>("/timeline/weekly-summary"),
  correlations: () => fetchApi<{ data: { flag: string; evidence: Record<string, unknown> }[] }>(
    "/timeline/correlations"
  ),
  goals: () =>
    fetchApi<{ data: { type: string; content: string; metadata: Record<string, unknown> }[] }>(
      "/timeline/goals"
    ),
  insights: () => fetchApi<{ data: { id: number; title: string; body: string; type: string; evidence?: Record<string, unknown> }[] }>("/insights"),
  memories: () =>
    fetchApi<{ data: { type: string; content: string; importance: number }[] }>("/memories"),
  emotions: (days = 30) =>
    fetchApi<{ data: { emotion: string; intensity: number; logged_at: string }[] }>(
      `/philosophy/emotions?days=${days}`
    ),
  stoicStreak: (days = 30) =>
    fetchApi<{ morning: number; evening: number; total: number }>(
      `/philosophy/stoic/streak?days=${days}`
    ),
  dreamThemes: (days = 30) =>
    fetchApi<{ words: { word: string; count: number }[] }>(`/philosophy/themes?days=${days}`),
};
