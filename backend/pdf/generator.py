import io

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from engine.constants import POSITIONS
from engine.utils import format_duration, mins_to_hhmm

POS_COLORS = {
    "TWR-M": HexColor("#4472C4"),
    "TWR-N": HexColor("#ED7D31"),
    "CLD-1": HexColor("#70AD47"),
    "SMC-S": HexColor("#FFC000"),
    "SMC-N": HexColor("#F4B183"),
    "TWR-S1": HexColor("#9DC3E6"),
    "SMC-M": HexColor("#A5A5A5"),
    "TWR-S2": HexColor("#FF7C80"),
}

POS_TEXT = {
    "TWR-M": colors.white,
    "TWR-N": colors.white,
    "CLD-1": colors.white,
    "SMC-S": HexColor("#1E2A3A"),
    "SMC-N": HexColor("#1E2A3A"),
    "TWR-S1": HexColor("#1E2A3A"),
    "SMC-M": HexColor("#1E2A3A"),
    "TWR-S2": colors.white,
}


def _render_schedule_pdf(schedule, slot_order, start_mins, end_mins):
    buffer = io.BytesIO()
    page_w, page_h = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))

    bg = HexColor("#14202E")
    card_bg = HexColor("#1E2D3D")
    label_bg = HexColor("#0D1926")
    text_dim = HexColor("#6B8BA4")
    text_hi = HexColor("#E8F4F8")

    margin = 6 * mm
    top = page_h - 16 * mm
    bottom = 4 * mm
    cols = 5
    rows = 3
    gap = 3 * mm
    total_w = page_w - 2 * margin
    total_h = top - bottom
    card_w = (total_w - (cols - 1) * gap) / cols
    card_h = (total_h - (rows - 1) * gap) / rows
    cards_per_page = cols * rows

    def draw_page_shell(page_num, page_count):
        pdf.setFillColor(bg)
        pdf.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        pdf.setFillColor(label_bg)
        pdf.rect(0, page_h - 14 * mm, page_w, 14 * mm, fill=1, stroke=0)
        pdf.setFillColor(text_hi)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(
            page_w / 2,
            page_h - 9 * mm,
            f"DUTY ROSTER  {mins_to_hhmm(start_mins)} - {mins_to_hhmm(end_mins)}",
        )
        if page_count > 1:
            pdf.setFont("Helvetica", 7)
            pdf.drawRightString(page_w - 4 * mm, page_h - 9 * mm, f"P{page_num}/{page_count}")

        legend_x = page_w - 8 * mm
        legend_y = page_h - 10.5 * mm
        for position in reversed(POSITIONS):
            pdf.setFillColor(POS_COLORS[position])
            pdf.roundRect(legend_x - 6 * mm, legend_y - 1.5 * mm, 6 * mm, 3 * mm, 1, fill=1, stroke=0)
            pdf.setFillColor(text_dim)
            pdf.setFont("Helvetica", 5)
            pdf.drawRightString(legend_x - 7 * mm, legend_y - 0.8 * mm, position)
            legend_x -= 18 * mm

    page_count = max(1, (len(slot_order) + cards_per_page - 1) // cards_per_page)

    for index, slot in enumerate(slot_order):
        page_index = index // cards_per_page
        page_num = page_index + 1
        local_index = index % cards_per_page
        if local_index == 0:
            if index > 0:
                pdf.showPage()
            draw_page_shell(page_num, page_count)

        col_index = local_index % cols
        row_index = local_index // cols
        card_x = margin + col_index * (card_w + gap)
        card_y = top - (row_index + 1) * card_h - row_index * gap

        blocks = schedule.get(slot, [])
        total_mins = sum(end - start for _, start, end in blocks)
        total_str = format_duration(total_mins)

        pdf.setFillColor(card_bg)
        pdf.setStrokeColor(HexColor("#253D52"))
        pdf.setLineWidth(0.6)
        pdf.roundRect(card_x, card_y, card_w, card_h, 3, fill=1, stroke=1)

        strip_w = 10 * mm
        pdf.setFillColor(label_bg)
        pdf.roundRect(card_x, card_y, strip_w, card_h, 3, fill=1, stroke=0)
        pdf.rect(card_x + strip_w / 2, card_y, strip_w / 2, card_h, fill=1, stroke=0)
        pdf.setFillColor(text_hi)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.saveState()
        pdf.translate(card_x + strip_w / 2, card_y + card_h / 2)
        pdf.rotate(90)
        pdf.drawCentredString(0, -3, slot)
        pdf.restoreState()

        pill_w = 18 * mm
        pill_h = 5 * mm
        pill_x = card_x + card_w - pill_w - 2 * mm
        pill_y = card_y + card_h - pill_h - 2 * mm
        pdf.setFillColor(HexColor("#0D3050"))
        pdf.setStrokeColor(HexColor("#1A6496"))
        pdf.setLineWidth(0.5)
        pdf.roundRect(pill_x, pill_y, pill_w, pill_h, 2, fill=1, stroke=1)
        pdf.setFillColor(HexColor("#7EC8E3"))
        pdf.setFont("Helvetica-Bold", 6.5)
        pdf.drawCentredString(pill_x + pill_w / 2, pill_y + 1.5 * mm, f"TOTAL  {total_str}")

        header_bottom = card_y + card_h - pill_h - 4 * mm
        pdf.setStrokeColor(HexColor("#253D52"))
        pdf.setLineWidth(0.4)
        pdf.line(card_x + strip_w + 1.5 * mm, header_bottom, card_x + card_w - 1.5 * mm, header_bottom)

        content_top = header_bottom - 1 * mm
        content_bottom = card_y + 2 * mm
        content_h = content_top - content_bottom
        block_x = card_x + strip_w + 2 * mm
        block_w = card_w - strip_w - 3.5 * mm

        block_count = max(1, len(blocks))
        block_gap = 0.8 if block_count > 6 else 1.2
        total_gap = block_gap * (block_count - 1)
        block_h = (content_h - total_gap) / block_count if block_count else content_h

        for block_index, (position, start, end) in enumerate(blocks):
            fill_color = POS_COLORS[position]
            text_color = POS_TEXT[position]
            block_y = content_top - (block_index + 1) * block_h - block_index * block_gap
            block_h_real = max(2.0, block_h)

            pdf.setFillColor(fill_color)
            pdf.setStrokeColor(HexColor("#14202E"))
            pdf.setLineWidth(0.5)
            pdf.roundRect(block_x, block_y, block_w, block_h_real, 2, fill=1, stroke=1)

            mid_y = block_y + block_h_real / 2
            pos_font = max(5.5, min(8.0, block_h_real * 0.42))
            time_font = max(5.0, min(7.5, block_h_real * 0.4))
            pdf.setFillColor(text_color)
            pdf.setFont("Helvetica-Bold", pos_font)
            pdf.drawString(block_x + 2.5 * mm, mid_y + 0.5, position)
            pdf.setFont("Helvetica-Bold", time_font)
            pdf.drawRightString(
                block_x + block_w - 2.5 * mm,
                mid_y + 0.5,
                f"{mins_to_hhmm(start)} - {mins_to_hhmm(end)}",
            )

    pdf.save()
    buffer.seek(0)
    return buffer.read()


def generate_pdf_from_schedule(schedule, slot_order, start_mins, end_mins):
    return _render_schedule_pdf(schedule, slot_order, start_mins, end_mins)
