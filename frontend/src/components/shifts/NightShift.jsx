import { useState } from "react";
import ShiftCard from "./ShiftCard";

function nightControllerLogic() {
  return [16, 17];
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

  const allChannels = [1, 2, 3, 4, 5, 6, 7, 8];
  const configuredChannels = new Set(
    customChannelTimings.map((item) => item.channel),
  );
  const availableChannels = allChannels.filter((ch) => !configuredChannels.has(ch));

  function formatNightTimeInput(value) {
    const digits = value.replace(/\D/g, "").slice(0, 4);
    if (digits.length <= 2) return digits;
    return `${digits.slice(0, 2)}:${digits.slice(2)}`;
  }

  function isAllowedTime(timeValue) {
    const normalized = formatNightTimeInput(timeValue);
    const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(normalized);
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
      [
        ...prev,
        {
          channel: selectedChannel,
          open: formatNightTimeInput(selectedOpen),
          close: formatNightTimeInput(selectedClose),
        },
      ].sort(
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
    <div className="night-panel">
      <div className="night-title">Channel Close Timings (15:00 to 02:00)</div>
      <style>
        {`
          .night-inline-btn {
            width: auto !important;
            margin-top: 0 !important;
          }
        `}
      </style>

      <div className="night-control-row">
        <div className="night-field">
          <label className="night-field-label" htmlFor="night-channel">
            Position
          </label>
          <select
            id="night-channel"
            value={selectedChannel}
            onChange={(e) => setSelectedChannel(Number(e.target.value))}
            aria-label="Position"
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
        </div>

        <div className="night-field">
          <label className="night-field-label" htmlFor="night-closed-from">
            Closed From
          </label>
          <input
            id="night-closed-from"
            type="text"
            value={selectedOpen}
            onChange={(e) => setSelectedOpen(formatNightTimeInput(e.target.value))}
            aria-label="Closed from"
            placeholder="1830"
            inputMode="numeric"
            pattern="[0-2][0-9]:?[0-5][0-9]"
            maxLength={5}
            disabled={availableChannels.length === 0}
            className="night-input"
          />
        </div>

        <div className="night-field">
          <label className="night-field-label" htmlFor="night-closed-to">
            Closed To
          </label>
          <input
            id="night-closed-to"
            type="text"
            value={selectedClose}
            onChange={(e) => setSelectedClose(formatNightTimeInput(e.target.value))}
            aria-label="Closed to"
            placeholder="2330"
            inputMode="numeric"
            pattern="[0-2][0-9]:?[0-5][0-9]"
            maxLength={5}
            disabled={availableChannels.length === 0}
            className="night-input"
          />
        </div>

        <button
          type="button"
          onClick={handleAddChannelTiming}
          disabled={availableChannels.length === 0}
          className="night-inline-btn night-action-btn"
        >
          Add
        </button>
      </div>
      <div className="night-help">Use 24-hour timing like 1830, 23:30, 0200.</div>
      {timingError && <div className="night-error">{timingError}</div>}

      <div className="night-list">
        {customChannelTimings.map((item) => (
          <div key={item.channel} className="night-item">
            <span className="night-item-copy">
              {channelLabels[item.channel]}: closed {item.open} - {item.close}
            </span>
            <button
              type="button"
              onClick={() => handleRemoveChannelTiming(item.channel)}
              className="night-inline-btn night-remove-btn"
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
