from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from models.roster_models import NightRosterRequest, RosterRequest
from engine.engine import generate_day_schedule
from engine.constants import NIGHT_POSITION_ORDER, get_positions
from engine.night_scheduler import build_night_schedule_for_pdf
from engine.utils import hhmm_to_mins, validate_shift_window
from pdf.generator import generate_pdf_from_schedule

router = APIRouter(prefix="/api/roster")


def _to_shift_window(start_time: str, end_time: str) -> tuple[int, int]:
    start_mins = hhmm_to_mins(start_time)
    end_mins = hhmm_to_mins(end_time)

    if end_mins <= start_mins:
        end_mins += 24 * 60

    if not validate_shift_window(start_mins, end_mins):
        raise HTTPException(status_code=400, detail="Invalid shift time window")

    return start_mins, end_mins


@router.post("/generate")
def generate_roster(request: RosterRequest):
    start_mins, end_mins = _to_shift_window(request.startTime, request.endTime)

    if request.shift == "night":
        night_request = request if isinstance(request, NightRosterRequest) else None
        if night_request is None:
            raise HTTPException(status_code=400, detail="Invalid night roster payload")

        try:
            schedule, controller_order, night_start, night_end = build_night_schedule_for_pdf(
                night_request.to_night_scheduler_payload()
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        pdf_bytes = generate_pdf_from_schedule(
            schedule=schedule,
            slot_order=controller_order,
            start_mins=night_start,
            end_mins=night_end,
            position_order=NIGHT_POSITION_ORDER,
        )

        return Response(content=pdf_bytes, media_type="application/pdf")

    
    active_positions=get_positions(request.openPositions,request.totalControllers)
    controllers = [f"C{i+1}" for i in range(request.totalControllers)]
    

    try:
        schedule = generate_day_schedule(
            controllers,
            active_positions,
            start_mins,
            end_mins,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    pdf_bytes = generate_pdf_from_schedule(
        schedule=schedule,
        slot_order=controllers,
        start_mins=start_mins,
        end_mins=end_mins,
        position_order=active_positions,
    )

    return Response(content=pdf_bytes, media_type="application/pdf")
