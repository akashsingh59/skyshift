from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from backend.analytics import analytics_health_status, get_last_24h_download_summary, record_roster_download
from backend.models.roster_models import NightRosterRequest, RosterRequest
from backend.engine.engine import generate_day_schedule
from backend.engine.constants import NIGHT_POSITION_ORDER, get_positions
from backend.engine.night_scheduler import build_night_schedule_for_pdf
from backend.engine.utils import hhmm_to_mins, validate_shift_window
from backend.pdf.generator import generate_pdf_from_schedule

router = APIRouter(prefix="/api/roster")


def _to_shift_window(start_time: str, end_time: str) -> tuple[int, int]:
    start_mins = hhmm_to_mins(start_time)
    end_mins = hhmm_to_mins(end_time)

    if end_mins <= start_mins:
        end_mins += 24 * 60

    if not validate_shift_window(start_mins, end_mins):
        raise HTTPException(status_code=400, detail="Invalid shift time window")

    return start_mins, end_mins


def _extract_requester_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for", "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip

    if request.client:
        return request.client.host

    return None


@router.post("/generate")
def generate_roster(request_data: RosterRequest, http_request: Request):
    start_mins, end_mins = _to_shift_window(request_data.startTime, request_data.endTime)
    requester_ip = _extract_requester_ip(http_request)
    user_agent = http_request.headers.get("user-agent")

    if request_data.shift == "night":
        night_request = request_data if isinstance(request_data, NightRosterRequest) else None
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

        record_roster_download(
            shift=night_request.shift,
            total_controllers=night_request.totalControllers,
            requester_ip=requester_ip,
            user_agent=user_agent,
        )

        return Response(content=pdf_bytes, media_type="application/pdf")

    
    active_positions=get_positions(request_data.openPositions,request_data.totalControllers)
    controllers = [f"C{i+1}" for i in range(request_data.totalControllers)]
    

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

    record_roster_download(
        shift=request_data.shift,
        total_controllers=request_data.totalControllers,
        requester_ip=requester_ip,
        user_agent=user_agent,
    )

    return Response(content=pdf_bytes, media_type="application/pdf")


@router.get("/analytics/downloads/last-24h")
def get_download_analytics_last_24h():
    return get_last_24h_download_summary()


@router.get("/analytics/health")
def get_analytics_health():
    return analytics_health_status()
