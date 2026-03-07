import ShiftCard from "./ShiftCard";

function morningControllerLogic(openPositions) {
  if (openPositions === 7) return [12, 13];
  if (openPositions === 8) return [12, 13, 14];
  return [];
}

export default function MorningShift({ onGenerate }) {
  return (
    <ShiftCard
      shiftKey="morning"
      startTime="02:00"
      endTime="08:30"
      controllerLogic={morningControllerLogic}
      showOpenPositions={true}
      onGenerate={onGenerate}
    />
  );
}