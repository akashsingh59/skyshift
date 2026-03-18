import { useState } from "react";
import MorningShift from "./components/shifts/MorningShift";
import AfternoonShift from "./components/shifts/AfternoonShift";
import NightShift from "./components/shifts/NightShift";
import  {generateRoster}  from "./services/rosterApi";

const shifts = [
  {
    key: "morning",
    title: "Morning",
    window: "02:00 - 08:30",
    note: "Day opening roster with 7 or 8 live positions.",
  },
  {
    key: "afternoon",
    title: "Afternoon",
    window: "08:30 - 15:00",
    note: "Midday coverage with the same day-shift controls.",
  },
  {
    key: "night",
    title: "Night",
    window: "15:00 - 02:00",
    note: "Night coverage with position-specific closure windows.",
  },
];

export default function App() {
  const [activeShift, setActiveShift] = useState("morning");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate(payload) {
    try {
      setLoading(true);
      setError("");

      await generateRoster(payload);

    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const activeShiftConfig = shifts.find((shift) => shift.key === activeShift);

  function renderShiftPanel() {
    if (activeShift === "morning") {
      return <MorningShift onGenerate={handleGenerate} />;
    }

    if (activeShift === "afternoon") {
      return <AfternoonShift onGenerate={handleGenerate} />;
    }

    return <NightShift onGenerate={handleGenerate} />;
  }

  return (
    <div className="app">
      <div className="hero-panel">
        <h2 className="eyebrow">SkyShift</h2>
        
        <p className="hero-copy">
          Pick a shift, adjust coverage, and generate the PDF from one focused workspace.
        </p>
      </div>

      <div className="workspace-shell">
        <div className="shift-switcher" role="tablist" aria-label="Shift selector">
          {shifts.map((shift) => (
            <button
              key={shift.key}
              type="button"
              role="tab"
              aria-selected={activeShift === shift.key}
              className={`shift-pill${activeShift === shift.key ? " active" : ""}`}
              onClick={() => setActiveShift(shift.key)}
            >
              <span>{shift.title}</span>
              <small>{shift.window}</small>
            </button>
          ))}
        </div>

        <div className="workspace-panel">
          <div className="workspace-header">
            <div>
              <p className="workspace-label">{activeShiftConfig.title} Shift</p>
              <h2>{activeShiftConfig.window}</h2>
            </div>
            <p className="workspace-note">{activeShiftConfig.note}</p>
          </div>

          <div className="shift-stage">
            {renderShiftPanel()}
          </div>
        </div>
      </div>

      {(loading || error) && (
        <div className="feedback-strip">
          {loading && <p className="status">Generating roster...</p>}
          {error && <p className="error">{error}</p>}
        </div>
      )}
      <p>contact 9870576022 for suggestions</p>
    </div>
  );
}
