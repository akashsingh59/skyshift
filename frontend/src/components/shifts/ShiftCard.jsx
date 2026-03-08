import { useState } from "react";
import ControllerSelect from "./common/ControllerSelect";

export default function ShiftCard({
  shiftKey,
  startTime,
  endTime,
  controllerLogic,
  showOpenPositions,
  onGenerate,
  afterControllers = null,
}) {
  const [openPositions, setOpenPositions] = useState(8);
  const [controllers, setControllers] = useState(12);
  const controllerOptions = controllerLogic(openPositions);
  const defaultContributoryChannel = 1;

  const needsChannel =
    (openPositions === 7 && controllers === 13) ||
    (openPositions === 8 && controllers === 14);

  function handleGenerate() {
    onGenerate({
      shift: shiftKey,
      startTime,
      endTime,
      openPositions,
      totalControllers: controllers,
      contributoryChannel: needsChannel ? defaultContributoryChannel : null,
    });
  }

  return (
    <div className="card">
      <h2>{shiftKey.toUpperCase()} SHIFT</h2>

      {showOpenPositions && (
        <>
          <h3>Open Positions</h3>
          <select
            value={openPositions}
            onChange={(e) => setOpenPositions(Number(e.target.value))}
          >
            <option value={7}>7</option>
            <option value={8}>8</option>
          </select>
        </>
      )}

      <ControllerSelect
        value={controllers}
        options={controllerOptions}
        onChange={setControllers}
      />

      {afterControllers}
      <button onClick={handleGenerate}>
        Generate {shiftKey} Roster
      </button>
    </div>
  );
}
