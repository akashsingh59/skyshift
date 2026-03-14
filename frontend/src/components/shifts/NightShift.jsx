import { useState } from "react";
import ShiftCard from "./ShiftCard";

function nightControllerLogic() {
  return [15, 16, 17];
}

const channelLabels = {
  1: "TWR-M",
  2: "TWR-N",
  3: "CLD-1",
  4: "SMC-S",
  5: "SMC-N",
  6: "TWR-S1",
  7: "SMC-M",
  8: "TWR-S2",
};

export default function NightShift({ onGenerate }) {
  const [customChannelTimings, setCustomChannelTimings] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState(1);
  const [selectedOpen, setSelectedOpen] = useState("15:00");
  const [selectedClose, setSelectedClose] = useState("02:00");
  const [timingError, setTimingError] = useState("");

  const sectionStyle = {
    marginTop: "8px",
    marginBottom: "4px",
    padding: "8px",
    border: "1px solid rgba(148, 163, 184, 0.35)",
    borderRadius: "8px",
    background: "rgba(2, 6, 23, 0.3)",
  };

  const titleStyle = {
    marginBottom: "6px",
    fontSize: "11px",
    color: "#cbd5e1",
    fontWeight: 600,
  };

  const controlRowStyle = {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr 96px",
    gap: "6px",
    alignItems: "center",
    marginBottom: "6px",
  };

  const listStyle = {
    display: "grid",
    gap: "4px",
  };

  const itemStyle = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: "11px",
    color: "#e2e8f0",
    padding: "4px 6px",
    borderRadius: "6px",
    background: "rgba(15, 23, 42, 0.5)",
  };

  const removeButtonStyle = {
    alignSelf: "stretch",
    justifySelf: "stretch",
    padding: "2px 8px",
    fontSize: "10px",
    borderRadius: "6px",
  };

  const inputStyle = {
    width: "100%",
    padding: "3px 6px",
    borderRadius: "6px",
    fontSize: "11px",
    border: "1px solid rgba(255, 255, 255, 0.1)",
    background: "rgba(15, 23, 42, 0.6)",
    color: "#f1f5f9",
  };

  const errorStyle = {
    marginTop: "4px",
    fontSize: "11px",
    color: "#fca5a5",
  };

  const allChannels = [1, 2, 3, 4, 5, 6, 7, 8];
  const configuredChannels = new Set(
    customChannelTimings.map((item) => item.channel),
  );
  const availableChannels = allChannels.filter((ch) => !configuredChannels.has(ch));

  function isAllowedTime(timeValue) {
    const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(timeValue);
    if (!match) return false;
    const hour = Number(match[1]);
    const minute = Number(match[2]);
    const totalMinutes = hour * 60 + minute;
    return totalMinutes >= 15 * 60 || totalMinutes <= 2 * 60;
  }

  function handleAddChannelTiming() {
    if (!availableChannels.includes(selectedChannel)) {
      return;
    }
    if (!isAllowedTime(selectedOpen) || !isAllowedTime(selectedClose)) {
      setTimingError("Use HH:MM between 15:00 and 02:00.");
      return;
    }
    setTimingError("");

    setCustomChannelTimings((prev) =>
      [...prev, { channel: selectedChannel, open: selectedOpen, close: selectedClose }].sort(
        (a, b) => a.channel - b.channel,
      ),
    );

    const nextChannel = availableChannels.find((ch) => ch !== selectedChannel);
    if (nextChannel !== undefined) {
      setSelectedChannel(nextChannel);
    }
  }

  function handleRemoveChannelTiming(channelNumber) {
    setCustomChannelTimings((prev) =>
      prev.filter((item) => item.channel !== channelNumber),
    );
    setSelectedChannel(channelNumber);
  }

  function buildFinalChannelTimings() {
    return customChannelTimings;
  }

  function handleNightGenerate(basePayload) {
    onGenerate({
      ...basePayload,
      channelTimings: buildFinalChannelTimings(),
    });
  }

  const nightAfterControllers = (
    <div style={sectionStyle}>
      <div style={titleStyle}>Channel Close Timings (15:00 to 02:00)</div>
      <style>
        {`
          .night-inline-btn {
            width: auto !important;
            margin-top: 0 !important;
          }
        `}
      </style>

      <div style={controlRowStyle}>
        <select
          value={selectedChannel}
          onChange={(e) => setSelectedChannel(Number(e.target.value))}
          aria-label="Channel"
          disabled={availableChannels.length === 0}
        >
          {availableChannels.length === 0 ? (
            <option value="">All channels configured</option>
          ) : (
            availableChannels.map((channel) => (
              <option key={channel} value={channel}>
                {channelLabels[channel]}
              </option>
            ))
          )}
        </select>

        <input
          type="time"
          value={selectedOpen}
          onChange={(e) => setSelectedOpen(e.target.value)}
          aria-label="Open time"
          title="Closed from"
          disabled={availableChannels.length === 0}
          style={inputStyle}
        />

        <input
          type="time"
          value={selectedClose}
          onChange={(e) => setSelectedClose(e.target.value)}
          aria-label="Close time"
          title="Closed to"
          disabled={availableChannels.length === 0}
          style={inputStyle}
        />

        <button
          type="button"
          onClick={handleAddChannelTiming}
          disabled={availableChannels.length === 0}
          style={removeButtonStyle}
          className="night-inline-btn"
        >
          Add
        </button>
      </div>
      {timingError && <div style={errorStyle}>{timingError}</div>}

      <div style={listStyle}>
        {customChannelTimings.map((item) => (
          <div key={item.channel} style={itemStyle}>
            <span>
              {channelLabels[item.channel]}: closed {item.open} - {item.close}
            </span>
            <button
              type="button"
              onClick={() => handleRemoveChannelTiming(item.channel)}
              style={removeButtonStyle}
              className="night-inline-btn"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <ShiftCard
      shiftKey="night"
      startTime="15:00"
      endTime="02:00"
      controllerLogic={nightControllerLogic}
      showOpenPositions={false}
      onGenerate={handleNightGenerate}
      afterControllers={nightAfterControllers}
    />
  );
}
