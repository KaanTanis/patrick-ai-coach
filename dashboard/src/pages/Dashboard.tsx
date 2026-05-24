import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { api } from "../api";

export function OverviewPage() {
  const [weight, setWeight] = useState<{ date: string; weight: number }[]>([]);
  const [checkins, setCheckins] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.weight(), api.checkins()])
      .then(([w, c]) => {
        setWeight(w.data);
        setCheckins(c.data);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error">{error}</div>;

  return (
    <div className="grid">
      <div className="card">
        <h2>Weight</h2>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={weight}>
            <XAxis dataKey="date" tick={{ fill: "#8b93a7", fontSize: 11 }} />
            <YAxis tick={{ fill: "#8b93a7", fontSize: 11 }} domain={["auto", "auto"]} />
            <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #2a2f3d" }} />
            <Line type="monotone" dataKey="weight" stroke="#6b9fff" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="card">
        <h2>Mood & Energy (30d)</h2>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={checkins}>
            <XAxis dataKey="date" tick={{ fill: "#8b93a7", fontSize: 11 }} />
            <YAxis domain={[1, 10]} tick={{ fill: "#8b93a7", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #2a2f3d" }} />
            <Line type="monotone" dataKey="mood" stroke="#6b9fff" dot={false} />
            <Line type="monotone" dataKey="energy" stroke="#5ecf8a" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function NutritionPage() {
  const [calories, setCalories] = useState<{ date: string; calories: number }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.calories()
      .then((r) => setCalories(r.data))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error">{error}</div>;

  return (
    <div className="card">
      <h2>Daily Calories</h2>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={calories}>
          <XAxis dataKey="date" tick={{ fill: "#8b93a7", fontSize: 11 }} />
          <YAxis tick={{ fill: "#8b93a7", fontSize: 11 }} />
          <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #2a2f3d" }} />
          <Bar dataKey="calories" fill="#6b9fff" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function InsightsPage() {
  const [insights, setInsights] = useState<{ title: string; body: string; type: string }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.insights()
      .then((r) => setInsights(r.data))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error">{error}</div>;

  return (
    <div className="card">
      <h2>Behavioral Insights</h2>
      {insights.length === 0 && <p style={{ color: "var(--muted)" }}>No insights yet.</p>}
      {insights.map((i, idx) => (
        <div key={idx} className="insight-item">
          <h3>{i.title}</h3>
          <p>{i.body}</p>
        </div>
      ))}
    </div>
  );
}

export function MemoriesPage() {
  const [memories, setMemories] = useState<{ type: string; content: string }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.memories()
      .then((r) => setMemories(r.data))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error">{error}</div>;

  return (
    <div className="card">
      <h2>AI Memory</h2>
      {memories.map((m, idx) => (
        <div key={idx} className="memory-item">
          <span className="memory-type">{m.type}</span>
          {m.content}
        </div>
      ))}
    </div>
  );
}

export function PhilosophyPage() {
  const [emotions, setEmotions] = useState<{ emotion: string; intensity: number; logged_at: string }[]>([]);
  const [stoic, setStoic] = useState<{ morning: number; evening: number; total: number } | null>(null);
  const [themes, setThemes] = useState<{ word: string; count: number }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.emotions(), api.stoicStreak(), api.dreamThemes()])
      .then(([e, s, t]) => {
        setEmotions(e.data);
        setStoic(s);
        setThemes(t.words);
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="error">{error}</div>;

  return (
    <div className="grid">
      <div className="card">
        <h2>Emotion Check-ins</h2>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={emotions}>
            <XAxis
              dataKey="logged_at"
              tick={{ fill: "#8b93a7", fontSize: 10 }}
              tickFormatter={(v) => String(v).slice(5, 10)}
            />
            <YAxis domain={[1, 10]} tick={{ fill: "#8b93a7", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #2a2f3d" }} />
            <Line type="monotone" dataKey="intensity" stroke="#c084fc" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="card">
        <h2>Stoic Ritual Streak (30d)</h2>
        <p>Morning: {stoic?.morning ?? 0} · Evening: {stoic?.evening ?? 0}</p>
        <p>Total: {stoic?.total ?? 0}</p>
      </div>
      <div className="card">
        <h2>Dream Theme Words</h2>
        {themes.length === 0 && <p style={{ color: "var(--muted)" }}>No dream entries yet.</p>}
        {themes.map((t) => (
          <div key={t.word} className="memory-item">
            {t.word} <span style={{ color: "var(--muted)" }}>({t.count})</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ConsistencyPage() {
  const [heatmap, setHeatmap] = useState<{ checkins: string[]; workouts: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.heatmap()
      .then(setHeatmap)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!heatmap) return null;

  const checkinSet = new Set(heatmap.checkins);
  const workoutSet = new Set(heatmap.workouts);
  const cells = Array.from({ length: 91 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (90 - i));
    const key = d.toISOString().slice(0, 10);
    let cls = "heatmap-cell";
    if (workoutSet.has(key)) cls += " workout";
    else if (checkinSet.has(key)) cls += " active";
    return <div key={key} className={cls} title={key} />;
  });

  return (
    <div className="card">
      <h2>Consistency (90 days)</h2>
      <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
        Blue = check-in, Green = workout day
      </p>
      <div className="heatmap">{cells}</div>
    </div>
  );
}
