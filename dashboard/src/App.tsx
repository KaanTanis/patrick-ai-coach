import { useState } from "react";
import { getApiKey, setApiKey } from "./api";
import {
  OverviewPage,
  NutritionPage,
  InsightsPage,
  MemoriesPage,
  ConsistencyPage,
} from "./pages/Dashboard";

type Tab = "overview" | "nutrition" | "insights" | "memories" | "consistency";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "nutrition", label: "Nutrition" },
  { id: "insights", label: "Insights" },
  { id: "memories", label: "Memories" },
  { id: "consistency", label: "Consistency" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("overview");
  const [apiKey, setApiKeyState] = useState(getApiKey());
  const [keyInput, setKeyInput] = useState(apiKey);

  const saveKey = () => {
    setApiKey(keyInput);
    setApiKeyState(keyInput);
  };

  return (
    <div className="app">
      <header>
        <h1>tbot</h1>
        <p>Personal AI coach — dashboard</p>
      </header>

      <div className="api-key-form">
        <input
          type="password"
          placeholder="API key (X-API-Key header)"
          value={keyInput}
          onChange={(e) => setKeyInput(e.target.value)}
        />
        <button onClick={saveKey}>Save</button>
      </div>

      {!apiKey && (
        <div className="error">Enter your API_KEY from .env to load dashboard data.</div>
      )}

      <nav>
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "active" : ""}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && <OverviewPage />}
      {tab === "nutrition" && <NutritionPage />}
      {tab === "insights" && <InsightsPage />}
      {tab === "memories" && <MemoriesPage />}
      {tab === "consistency" && <ConsistencyPage />}
    </div>
  );
}
