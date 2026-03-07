export default function ControllerSelect({
  value,
  options,
  onChange,
}) {
  return (
    <>
      <h3>Controllers Available</h3>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </>
  );
}