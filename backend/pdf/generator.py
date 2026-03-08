import io

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from engine.utils import mins_to_hhmm

DEFAULT_POSITION_ORDER = [
    "TWR-M",
    "TWR-N",
    "CLD-1",
    "SMC-S",
    "SMC-N",
    "TWR-S1",
    "SMC-M",
    "TWR-S2",
]

POS_COLORS = {
    "TWR-M": HexColor("#DCEAF7"),
    "TWR-N": HexColor("#F7E4D2"),
    "CLD-1": HexColor("#DDEED7"),
    "SMC-S": HexColor("#F8F0BF"),
    "SMC-N": HexColor("#F4DDCB"),
    "TWR-S1": HexColor("#D9EEF2"),
    "SMC-M": HexColor("#E3E3E3"),
    "TWR-S2": HexColor("#F8DCDD"),
}


def _position_sort_key(position, position_order):
    try:
        return (0, position_order.index(position))
    except ValueError:
        return (1, position)


def _collect_positions(schedule, position_order):
    positions = {position for blocks in schedule.values() for position, _, _ in blocks}
    return sorted(positions, key=lambda position: _position_sort_key(position, position_order))


def _collect_time_boundaries(schedule):
    boundaries = {time for blocks in schedule.values() for _, start, end in blocks for time in (start, end)}
    return sorted(boundaries)


def _build_coverage_rows(schedule, positions, boundaries):
    rows = []
    for position in positions:
        row = []
        for start, end in zip(boundaries, boundaries[1:]):
            assigned = "-"
            for controller, blocks in schedule.items():
                for block_position, block_start, block_end in blocks:
                    if block_position == position and block_start <= start and block_end >= end:
                        assigned = controller
                        break
                if assigned != "-":
                    break
            row.append(assigned)
        rows.append((position, row))
    return rows


def _build_controller_rows(schedule, slot_order):
    rows = []
    for controller in slot_order:
        blocks = sorted(schedule.get(controller, []), key=lambda block: block[1])
        if not blocks:
            rows.append((controller, "No assignment"))
            continue
        summary = ", ".join(
            f"{position} {mins_to_hhmm(start)}-{mins_to_hhmm(end)}"
            for position, start, end in blocks
        )
        rows.append((controller, summary))
    return rows


def _draw_page_header(pdf, page_w, page_h, start_mins, end_mins):
    paper = HexColor("#F7F1E3")
    ink = HexColor("#2B2620")
    line = HexColor("#B7AA92")

    pdf.setFillColor(paper)
    pdf.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    pdf.setStrokeColor(line)
    pdf.setLineWidth(1)
    pdf.line(10 * mm, page_h - 18 * mm, page_w - 10 * mm, page_h - 18 * mm)

    pdf.setFillColor(ink)
    pdf.setFont("Times-Bold", 16)
    pdf.drawCentredString(page_w / 2, page_h - 12 * mm, "DUTY ROSTER")
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(
        page_w / 2,
        page_h - 16.2 * mm,
        f"Shift Window  {mins_to_hhmm(start_mins)} - {mins_to_hhmm(end_mins)}",
    )


def _draw_position_coverage(pdf, x, y_top, width, schedule, position_order):
    ink = HexColor("#2B2620")
    line = HexColor("#B7AA92")
    label_fill = HexColor("#EEE5D3")

    positions = _collect_positions(schedule, position_order)
    boundaries = _collect_time_boundaries(schedule)
    coverage_rows = _build_coverage_rows(schedule, positions, boundaries)

    pdf.setFillColor(ink)
    pdf.setFont("Times-Bold", 11)
    pdf.drawString(x, y_top, "SECTION A. POSITION COVERAGE")

    if len(boundaries) < 2:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x, y_top - 8 * mm, "No schedule data available.")
        return y_top - 12 * mm

    row_h = 8 * mm
    label_w = 24 * mm
    slot_count = len(boundaries) - 1
    slot_w = (width - label_w) / max(1, slot_count)
    table_top = y_top - 4 * mm
    table_h = row_h * (len(coverage_rows) + 1)

    pdf.setStrokeColor(line)
    pdf.setLineWidth(0.5)
    pdf.rect(x, table_top - table_h, width, table_h, fill=0, stroke=1)

    pdf.setFillColor(label_fill)
    pdf.rect(x, table_top - row_h, label_w, row_h, fill=1, stroke=0)
    pdf.setFillColor(ink)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(x + 2 * mm, table_top - 5.5 * mm, "Position")

    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
        cell_x = x + label_w + index * slot_w
        pdf.setFillColor(label_fill)
        pdf.rect(cell_x, table_top - row_h, slot_w, row_h, fill=1, stroke=0)
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawCentredString(
            cell_x + slot_w / 2,
            table_top - 5.2 * mm,
            f"{mins_to_hhmm(start)}-{mins_to_hhmm(end)}",
        )

    for row_index, (position, assignments) in enumerate(coverage_rows, start=1):
        row_y = table_top - row_h * row_index
        fill = POS_COLORS.get(position, HexColor("#EFE8DB"))
        pdf.setFillColor(fill)
        pdf.rect(x, row_y - row_h, label_w, row_h, fill=1, stroke=0)
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(x + 2 * mm, row_y - 5.5 * mm, position)

        for col_index, controller in enumerate(assignments):
            cell_x = x + label_w + col_index * slot_w
            pdf.setFillColor(colors.white)
            pdf.rect(cell_x, row_y - row_h, slot_w, row_h, fill=1, stroke=0)
            pdf.setFillColor(ink)
            pdf.setFont("Helvetica", 8)
            pdf.drawCentredString(cell_x + slot_w / 2, row_y - 5.5 * mm, controller)

    for row_index in range(len(coverage_rows) + 1):
        line_y = table_top - row_h * row_index
        pdf.line(x, line_y, x + width, line_y)

    pdf.line(x + label_w, table_top, x + label_w, table_top - table_h)
    for col_index in range(slot_count + 1):
        line_x = x + label_w + col_index * slot_w
        pdf.line(line_x, table_top, line_x, table_top - table_h)

    return table_top - table_h - 8 * mm


def _draw_controller_assignments(pdf, x, y_top, width, schedule, slot_order, page_bottom):
    ink = HexColor("#2B2620")
    line = HexColor("#B7AA92")
    label_fill = HexColor("#EEE5D3")

    rows = _build_controller_rows(schedule, slot_order)

    pdf.setFillColor(ink)
    pdf.setFont("Times-Bold", 11)
    pdf.drawString(x, y_top, "SECTION B. CONTROLLER ASSIGNMENTS")

    row_h = 7 * mm
    controller_w = 20 * mm
    summary_w = width - controller_w
    table_top = y_top - 4 * mm
    y_cursor = table_top

    pdf.setFillColor(label_fill)
    pdf.rect(x, y_cursor - row_h, controller_w, row_h, fill=1, stroke=0)
    pdf.rect(x + controller_w, y_cursor - row_h, summary_w, row_h, fill=1, stroke=0)
    pdf.setFillColor(ink)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(x + 2 * mm, y_cursor - 5 * mm, "Ctrl")
    pdf.drawString(x + controller_w + 2 * mm, y_cursor - 5 * mm, "Assignment Summary")
    y_cursor -= row_h

    for controller, summary in rows:
        if y_cursor - row_h < page_bottom:
            pdf.setFont("Helvetica", 8)
            pdf.drawString(x, y_cursor - 3 * mm, "Additional controller rows omitted on this page.")
            return

        pdf.setFillColor(colors.white)
        pdf.rect(x, y_cursor - row_h, controller_w, row_h, fill=1, stroke=0)
        pdf.rect(x + controller_w, y_cursor - row_h, summary_w, row_h, fill=1, stroke=0)
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(x + 2 * mm, y_cursor - 5 * mm, controller)
        pdf.setFont("Helvetica", 7.5)
        pdf.drawString(x + controller_w + 2 * mm, y_cursor - 5 * mm, summary[:140])
        y_cursor -= row_h

    table_bottom = y_cursor
    table_h = table_top - table_bottom

    pdf.setStrokeColor(line)
    pdf.setLineWidth(0.5)
    pdf.rect(x, table_bottom, width, table_h, fill=0, stroke=1)
    pdf.line(x + controller_w, table_top, x + controller_w, table_bottom)

    current_y = table_top
    while current_y >= table_bottom:
        pdf.line(x, current_y, x + width, current_y)
        current_y -= row_h


def _render_schedule_pdf(schedule, slot_order, start_mins, end_mins, position_order):
    buffer = io.BytesIO()
    page_w, page_h = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))

    margin_x = 12 * mm
    page_bottom = 10 * mm
    content_w = page_w - 2 * margin_x

    _draw_page_header(pdf, page_w, page_h, start_mins, end_mins)
    next_y = _draw_position_coverage(
        pdf,
        margin_x,
        page_h - 26 * mm,
        content_w,
        schedule,
        position_order or DEFAULT_POSITION_ORDER,
    )
    _draw_controller_assignments(pdf, margin_x, next_y, content_w, schedule, slot_order, page_bottom)

    pdf.save()
    buffer.seek(0)
    return buffer.read()


def generate_pdf_from_schedule(schedule, slot_order, start_mins, end_mins, position_order=None):
    return _render_schedule_pdf(
        schedule,
        slot_order,
        start_mins,
        end_mins,
        position_order or DEFAULT_POSITION_ORDER,
    )
