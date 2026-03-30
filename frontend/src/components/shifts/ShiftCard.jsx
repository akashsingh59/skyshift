import { useEffect, useState } from "react";
import ControllerSelect from "./common/ControllerSelect";

export default function ShiftCard({
  shiftKey,
  startTime,
  endTime,
  controllerLogic,
  showOpenPositions,
  onGenerate,
  afterControllers = null,
  defaultControllers = null,
}) {
  const [openPositions, setOpenPositions] = useState(8);
  const controllerOptions = controllerLogic(openPositions);
  const initialControllers =
    defaultControllers && controllerOptions.includes(defaultControllers)
      ? defaultControllers
      : (controllerOptions[0] ?? 12);
  const [controllers, setControllers] = useState(initialControllers);

  useEffect(() => {
    if (!controllerOptions.includes(controllers)) {
      setControllers(controllerOptions[0] ?? 12);
    }
  }, [controllerOptions, controllers]);

  function handleGenerate() {
    onGenerate({
      shift: shiftKey,
      startTime,
      endTime,
      openPositions,
      totalControllers: controllers,
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
