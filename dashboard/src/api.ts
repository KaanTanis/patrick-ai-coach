const API_KEY_STORAGE = "tbot_api_key";

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
  smoking: (days = 30) =>
    fetchApi<{ cravings: { date: string; level: number }[]; events: unknown[] }>(
      `/metrics/smoking?days=${days}`
    ),
  heatmap: (days = 90) =>
    fetchApi<{ checkins: string[]; workouts: string[] }>(`/metrics/consistency/heatmap?days=${days}`),
  insights: () => fetchApi<{ data: { title: string; body: string; type: string; confidence: number }[] }>("/insights"),
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
