export default function ChannelSelect({
  value,
  onChange,
}) {
  return (
    <>
      <h3>Select Contributory Channel</h3>
      <select
        value={value || ""}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        <option value="" disabled>
          Select Channel
        </option>

        {[1, 2, 3, 4, 5, 6, 7, 8].map((ch) => (
          <option key={ch} value={ch}>
            Channel {ch}
          </option>
        ))}
      </select>
    </>
  );
}