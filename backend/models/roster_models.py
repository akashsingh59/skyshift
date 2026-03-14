from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator


class TimeWindow(BaseModel):
    startTime: str
    endTime: str


class BaseRosterRequest(TimeWindow):
    shift: Literal["morning", "afternoon", "night"]
    totalControllers: int = Field(..., ge=11, le=17)


class DayRosterRequest(BaseRosterRequest):
    shift: Literal["morning", "afternoon"]
    openPositions: int = Field(..., ge=7, le=8)
    contributoryChannel: int | None = Field(default=None, ge=1, le=8)

    @model_validator(mode="after")
    def validate_day_rules(self):
        needs_channel = (
            (self.openPositions == 7 and self.totalControllers == 13)
            or (self.openPositions == 8 and self.totalControllers == 14)
        )

        allowed_controllers = {
            7: {11, 12, 13},
            8: {12, 13, 14},
        }

        if self.totalControllers not in allowed_controllers[self.openPositions]:
            raise ValueError(
                f"Invalid totalControllers={self.totalControllers} for openPositions={self.openPositions}"
            )

        if needs_channel and self.contributoryChannel is None:
            raise ValueError("contributoryChannel is required for this day-shift combination")

        if not needs_channel and self.contributoryChannel is not None:
            raise ValueError("contributoryChannel should only be sent when required")

        return self


class MorningRosterRequest(DayRosterRequest):
    shift: Literal["morning"]


class AfternoonRosterRequest(DayRosterRequest):
    shift: Literal["afternoon"]


class NightChannelTiming(BaseModel):
    channel: int = Field(..., ge=1, le=8)
    open: str
    close: str


class NightRosterRequest(BaseRosterRequest):
    shift: Literal["night"]
    channelTimings: list[NightChannelTiming] = []

    @model_validator(mode="after")
    def validate_night_rules(self):

        # Controller rule
        if self.totalControllers not in {15, 16, 17}:
            raise ValueError(
                "Night shift totalControllers must be one of 15, 16, 17"
            )

        # Ensure no duplicate channels
        channel_numbers = [item.channel for item in self.channelTimings]

        if len(channel_numbers) != len(set(channel_numbers)):
            raise ValueError("Duplicate channel entries are not allowed")

        return self

    def normalized_channels(self):

        channels = {}

        # Assume all channels open full shift
        for ch in range(1, 9):
            channels[ch] = {
                "channel": ch,
                "shift_open": self.startTime,
                "shift_close": self.endTime,
                "closure": None
            }

        # Apply closures
        for item in self.channelTimings:
            channels[item.channel]["closure"] = {
                "start": item.open,
                "end": item.close
            }

        return channels

    def to_night_scheduler_payload(self):
        channel_closures = []

        for item in self.channelTimings:
            channel_closures.append(
                {
                    "channel": item.channel,
                    "closeFrom": item.open,
                    "closeTo": item.close,
                }
            )

        return {
            "totalControllers": self.totalControllers,
            "channelClosures": channel_closures,
        }


RosterRequest = Annotated[
    Union[MorningRosterRequest, AfternoonRosterRequest, NightRosterRequest],
    Field(discriminator="shift"),
]
