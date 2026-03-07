import ShiftCard from "./ShiftCard";
function nightControllerLogic() {
  return [15, 16, 17];
}

export default function NightShift({ onGenerate }) {
  return (
    <ShiftCard
      shiftKey="night"
      startTime="15:00"
      endTime="02:00"
      controllerLogic={nightControllerLogic}
      showOpenPositions={false}
      onGenerate={onGenerate}
    />
  );
}