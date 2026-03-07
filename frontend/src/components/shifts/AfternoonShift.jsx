import ShiftCard from "./ShiftCard";

function afternoonControllerLogic(openPositions) {
  if (openPositions === 7) return [12, 13];
  if (openPositions === 8) return [12, 13, 14];
  return [];
}

export default function AfternoonShift({ onGenerate }) {
  return (
    <ShiftCard
      shiftKey="afternoon"
      startTime="08:30"
      endTime="15:00"
      controllerLogic={afternoonControllerLogic}
      showOpenPositions={true}
      onGenerate={onGenerate}
    />
  );
}