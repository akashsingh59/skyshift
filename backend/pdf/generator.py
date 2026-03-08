import io

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


def _build_coverage_rows(schedule, positions, shift_start, shift_end):
    rows = []
    for position in positions:
        segments = []
        blocks = []
        for controller, controller_blocks in schedule.items():
            for block_position, block_start, block_end in controller_blocks:
                if block_position == position:
                    blocks.append((block_start, block_end, controller))

        blocks.sort(key=lambda item: item[0])
        cursor = shift_start
        for block_start, block_end, controller in blocks:
            if block_start > cursor:
                segments.append((cursor, block_start, "-"))
            segments.append((block_start, block_end, controller))
            cursor = max(cursor, block_end)

        if cursor < shift_end:
            segments.append((cursor, shift_end, "-"))

        rows.append((position, segments))
    return rows


def _build_controller_rows(schedule, slot_order):
    rows = []
    for controller in slot_order:
        blocks = sorted(schedule.get(controller, []), key=lambda block: block[1])
        if not blocks:
            rows.append((controller, [("NO ASSIGNMENT", "", "")]))
            continue
        summary = [
            (position, mins_to_hhmm(start), mins_to_hhmm(end))
            for position, start, end in blocks
        ]
        rows.append((controller, summary))
    return rows


def _draw_dashed_rule(pdf, x1, y1, x2, y2, dash=(6, 3), width=1):
    pdf.saveState()
    pdf.setLineWidth(width)
    pdf.setDash(*dash)
    pdf.line(x1, y1, x2, y2)
    pdf.restoreState()


def _wrap_text(pdf, text, max_width, font_name, font_size):
    if not text:
        return [""]

    words = text.split()
    lines = []
    current = words[0]

    for word in words[1:]:
        candidate = f"{current} {word}"
        if pdf.stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def _infer_shift_label(start_mins, end_mins):
    if start_mins == 120 and end_mins == 510:
        return "Morning Shift"
    if start_mins == 510 and end_mins == 900:
        return "Afternoon Shift"
    return "Night Shift"


def _draw_page_header(pdf, page_w, page_h, start_mins, end_mins, page_num=1):
    paper = HexColor("#F7F3EA")
    ink = HexColor("#141414")

    pdf.setFillColor(paper)
    pdf.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    pdf.setFillColor(ink)
    if page_num == 1:
        pdf.setFont("Courier-Bold", 26)
        pdf.drawCentredString(page_w / 2, page_h - 10 * mm, "SkyShift")
        pdf.setFont("Courier-Bold", 13)
        pdf.drawCentredString(
            page_w / 2,
            page_h - 17.2 * mm,
            _infer_shift_label(start_mins, end_mins),
        )
    _draw_dashed_rule(pdf, 10 * mm, page_h - 20 * mm, page_w - 10 * mm, page_h - 20 * mm, width=1.6)


def _draw_position_coverage(pdf, x, y_top, width, schedule, position_order, shift_start, shift_end):
    ink = HexColor("#141414")

    positions = _collect_positions(schedule, position_order)
    coverage_rows = _build_coverage_rows(schedule, positions, shift_start, shift_end)

    pdf.setFillColor(ink)
    pdf.setFont("Courier-Bold", 14)
    pdf.drawString(x, y_top, "SECTION A. POSITION COVERAGE")
    _draw_dashed_rule(pdf, x, y_top - 1.5 * mm, x + width, y_top - 1.5 * mm, width=1.2)

    if not coverage_rows:
        pdf.setFont("Courier-Bold", 10)
        pdf.drawString(x, y_top - 8 * mm, "No schedule data available.")
        return y_top - 12 * mm

    row_h = 13.5 * mm
    row_gap = 3 * mm
    label_w = 28 * mm
    timeline_w = width - label_w
    first_row_top = y_top - 6 * mm

    for row_index, (position, segments) in enumerate(coverage_rows):
        row_top = first_row_top - (row_index * (row_h + row_gap))
        row_bottom = row_top - row_h
        row_mid = row_top - (row_h / 2)

        pdf.setFillColor(ink)
        pdf.setFont("Courier-Bold", 12)
        pdf.drawString(x + 1.2 * mm, row_mid + 0.8 * mm, position)

        visible_segments = [segment for segment in segments if segment[2] != "-"]
        if not visible_segments:
            visible_segments = segments

        cell_count = max(1, len(visible_segments))
        base_cell_w = max(34, timeline_w / cell_count)
        adjusted_widths = [base_cell_w for _ in visible_segments]

        if adjusted_widths:
            width_correction = timeline_w - sum(adjusted_widths)
            adjusted_widths[-1] += width_correction

        seg_x = x + label_w
        for (seg_start, seg_end, controller), seg_w in zip(visible_segments, adjusted_widths):
            seg_w = max(12, seg_w)
            pdf.setStrokeColor(ink)
            pdf.setLineWidth(1.2)
            pdf.rect(seg_x, row_mid - 5.6 * mm, seg_w, 11.2 * mm, fill=0, stroke=1)
            time_font = 10.4
            ctrl_font = 10.8
            pdf.setFont("Courier-Bold", time_font)
            pdf.drawCentredString(
                seg_x + seg_w / 2,
                row_mid + 2.1 * mm,
                f"{mins_to_hhmm(seg_start)}-{mins_to_hhmm(seg_end)}",
            )
            pdf.setFont("Courier-Bold", ctrl_font)
            pdf.drawCentredString(seg_x + seg_w / 2, row_mid - 1.8 * mm, controller)
            seg_x += seg_w

        _draw_dashed_rule(pdf, x, row_bottom - (row_gap / 2), x + width, row_bottom - (row_gap / 2), dash=(4, 2), width=1.1)

    return first_row_top - (len(coverage_rows) * (row_h + row_gap)) - 8 * mm


def _draw_controller_assignments(pdf, x, y_top, width, schedule, slot_order, page_bottom, page_w, page_h, start_mins, end_mins):
    ink = HexColor("#141414")

    rows = _build_controller_rows(schedule, slot_order)

    section_title_gap = 4 * mm
    row_h = 9.5 * mm
    ctrl_w = 26 * mm
    pos_w = 70 * mm
    from_w = 32 * mm
    to_w = 32 * mm
    table_w = ctrl_w + pos_w + from_w + to_w
    if table_w > width:
        pos_w -= (table_w - width)
        table_w = width

    def draw_section_header(section_y):
        pdf.setFillColor(ink)
        pdf.setFont("Courier-Bold", 16)
        pdf.drawString(x, section_y, "SECTION B. CONTROLLER ASSIGNMENTS")
        _draw_dashed_rule(pdf, x, section_y - 1.5 * mm, x + table_w, section_y - 1.5 * mm, width=1.2)

    def draw_table_header(table_top):
        pdf.setFillColor(ink)
        pdf.setFont("Courier-Bold", 12)
        pdf.drawString(x + 1.8 * mm, table_top - 6.2 * mm, "CTRL")
        pdf.drawString(x + ctrl_w + 1.8 * mm, table_top - 6.2 * mm, "POSITION")
        pdf.drawString(x + ctrl_w + pos_w + 1.8 * mm, table_top - 6.2 * mm, "FROM")
        pdf.drawString(x + ctrl_w + pos_w + from_w + 1.8 * mm, table_top - 6.2 * mm, "TO")

        pdf.setStrokeColor(ink)
        pdf.setLineWidth(1.1)
        pdf.rect(x, table_top - row_h, table_w, row_h, fill=0, stroke=1)
        pdf.line(x + ctrl_w, table_top, x + ctrl_w, table_top - row_h)
        pdf.line(x + ctrl_w + pos_w, table_top, x + ctrl_w + pos_w, table_top - row_h)
        pdf.line(x + ctrl_w + pos_w + from_w, table_top, x + ctrl_w + pos_w + from_w, table_top - row_h)
        return table_top - row_h

    section_y = y_top
    draw_section_header(section_y)
    y_cursor = draw_table_header(section_y - section_title_gap)

    for controller, assignments in rows:
        group_rows = max(1, len(assignments))
        group_h = group_rows * row_h

        if y_cursor - group_h < page_bottom:
            pdf.showPage()
            _draw_page_header(pdf, page_w, page_h, start_mins, end_mins, page_num=2)
            section_y = page_h - 18 * mm
            draw_section_header(section_y)
            y_cursor = draw_table_header(section_y - section_title_gap)

        pdf.setStrokeColor(ink)
        pdf.setLineWidth(1.0)
        pdf.rect(x, y_cursor - group_h, table_w, group_h, fill=0, stroke=1)
        pdf.line(x + ctrl_w, y_cursor, x + ctrl_w, y_cursor - group_h)
        pdf.line(x + ctrl_w + pos_w, y_cursor, x + ctrl_w + pos_w, y_cursor - group_h)
        pdf.line(x + ctrl_w + pos_w + from_w, y_cursor, x + ctrl_w + pos_w + from_w, y_cursor - group_h)

        pdf.setFillColor(ink)
        pdf.setFont("Courier-Bold", 13)
        ctrl_text_y = y_cursor - (group_h / 2) - 1.6 * mm
        pdf.drawCentredString(x + (ctrl_w / 2), ctrl_text_y, controller)

        row_cursor = y_cursor
        for index, (position, start_text, end_text) in enumerate(assignments):
            pdf.setFont("Courier-Bold", 12)
            pdf.drawString(x + ctrl_w + 1.8 * mm, row_cursor - 6.2 * mm, position)
            pdf.drawString(x + ctrl_w + pos_w + 1.8 * mm, row_cursor - 6.2 * mm, start_text)
            pdf.drawString(x + ctrl_w + pos_w + from_w + 1.8 * mm, row_cursor - 6.2 * mm, end_text)

            row_cursor -= row_h
            if index < len(assignments) - 1:
                _draw_dashed_rule(
                    pdf,
                    x + ctrl_w,
                    row_cursor,
                    x + table_w,
                    row_cursor,
                    dash=(4, 2),
                    width=0.9,
                )

        _draw_dashed_rule(pdf, x, y_cursor - group_h, x + table_w, y_cursor - group_h, dash=(4, 2), width=1.0)
        y_cursor -= group_h


def _render_schedule_pdf(schedule, slot_order, start_mins, end_mins, position_order):
    buffer = io.BytesIO()
    page_w, page_h = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))

    margin_x = 12 * mm
    page_bottom = 10 * mm
    content_w = page_w - 2 * margin_x

    _draw_page_header(pdf, page_w, page_h, start_mins, end_mins, page_num=1)
    next_y = _draw_position_coverage(
        pdf,
        margin_x,
        page_h - 26 * mm,
        content_w,
        schedule,
        position_order or DEFAULT_POSITION_ORDER,
        start_mins,
        end_mins,
    )
    pdf.showPage()
    _draw_page_header(pdf, page_w, page_h, start_mins, end_mins, page_num=2)
    _draw_controller_assignments(
        pdf,
        margin_x,
        page_h - 18 * mm,
        content_w,
        schedule,
        slot_order,
        page_bottom,
        page_w,
        page_h,
        start_mins,
        end_mins,
    )

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
