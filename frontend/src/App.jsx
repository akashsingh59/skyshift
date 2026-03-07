import { useState } from "react";
import MorningShift from "./components/shifts/MorningShift";
import AfternoonShift from "./components/shifts/AfternoonShift";
import NightShift from "./components/shifts/NightShift";
import  {generateRoster}  from "./services/rosterApi";

export default function App() {
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

  return (
    <div className="app">
      <h1>SkyShift Roster Generator</h1>

      <div className="shift-container">
        <MorningShift onGenerate={handleGenerate} />
        <AfternoonShift onGenerate={handleGenerate} />
        <NightShift onGenerate={handleGenerate} />
      </div>

      {loading && <p className="status">Generating roster...</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}