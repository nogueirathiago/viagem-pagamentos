from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data.json"
OUTPUT_DIR = ROOT / "output"
PNG_PATH = OUTPUT_DIR / "painel_pagamentos_whatsapp.png"
TEXT_PATH = OUTPUT_DIR / "painel_pagamentos_whatsapp.txt"
SITE_DIR = ROOT / "site"
SITE_DATA_PATH = SITE_DIR / "data.json"
SITE_PREVIEW_PATH = SITE_DIR / "preview.png"

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1820
PREVIEW_WIDTH = 1200
PREVIEW_HEIGHT = 630

BG_TOP = "#F6F0E8"
BG_BOTTOM = "#E7EFEA"
TEXT_DARK = "#1E2A28"
TEXT_MUTED = "#5B6A67"
CARD_BG = "#FFFDFC"
ACCENT = "#2F7D6B"
ACCENT_SOFT = "#DCEFEA"
WARN = "#A86D3A"
DIVIDER = "#D9E1DD"
PREVIEW_BLUE = "#2F71EF"
PREVIEW_MINT = "#2FBF9F"
PREVIEW_DARK = "#2C3950"
PREVIEW_RED = "#D93A35"

DATE_FMT = "%d/%m/%Y"


@dataclass
class Member:
    name: str
    paid_installments: int
    prepaid_installments: list[str] = field(default_factory=list)


@dataclass
class Couple:
    name: str
    members: list[Member]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def brl(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    integer, decimal = f"{quantized:.2f}".split(".")
    reversed_groups = [integer[max(i - 3, 0):i] for i in range(len(integer), 0, -3)]
    return f"R$ {'.'.join(reversed(reversed_groups))},{decimal}"


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica.ttc",
            ]
        )
    else:
        candidates.extend(
            [
                "/System/Library/Fonts/SFNS.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            ]
        )

    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def validate_due_dates(months: Iterable[dict]) -> None:
    for month in months:
        due = datetime.strptime(month["due_date"], "%Y-%m-%d").date()
        if due.day == 7:
            continue
        if due.weekday() >= 5:
            raise ValueError(f"Vencimento em fim de semana: {month['due_date']}")
        original = date(due.year, due.month, 7)
        if original.weekday() < 5:
            raise ValueError(f"Data antecipada sem necessidade: {month['due_date']}")
        if original.weekday() == 5 and due.day != 6:
            raise ValueError(f"Sabado deveria antecipar para dia 6: {month['due_date']}")
        if original.weekday() == 6 and due.day != 5:
            raise ValueError(f"Domingo deveria antecipar para dia 5: {month['due_date']}")


def validate_financials(data: dict) -> Decimal:
    total_amount = Decimal(str(data["total_amount"]))
    installments = data["installments_total"]
    couple_total = sum(Decimal(str(month["couple_amount"])) for month in data["payment_rule"]["months"])
    couples_count = len(data["couples"])
    computed_total = couple_total * couples_count
    if computed_total != total_amount:
        raise ValueError(
            f"Total inconsistente. Esperado {brl(total_amount)} e calculado {brl(computed_total)}."
        )
    if installments != len(data["payment_rule"]["months"]):
        raise ValueError("Numero de parcelas nao bate com a quantidade de meses configurados.")
    return total_amount


def couple_total_amount(months: list[dict]) -> Decimal:
    return sum(Decimal(str(month["couple_amount"])) for month in months)


def parse_couples(data: dict) -> list[Couple]:
    installments_total = data["installments_total"]
    valid_labels = {month["label"] for month in data["payment_rule"]["months"]}
    couples: list[Couple] = []
    for couple_data in data["couples"]:
        members = [Member(**member) for member in couple_data["members"]]
        for member in members:
            paid_total = total_paid(member)
            if member.paid_installments < 0 or paid_total > installments_total:
                raise ValueError(
                    f"{member.name} tem {paid_total} parcelas pagas, fora do intervalo 0..{installments_total}."
                )
            unknown_prepaid = set(member.prepaid_installments) - valid_labels
            if unknown_prepaid:
                labels = ", ".join(sorted(unknown_prepaid))
                raise ValueError(f"{member.name} tem parcelas antecipadas invalidas: {labels}.")
        couples.append(Couple(name=couple_data["name"], members=members))
    return couples


def total_paid(member: Member) -> int:
    return member.paid_installments + len(member.prepaid_installments)


def member_paid_labels(member: Member, months: list[dict]) -> set[str]:
    normal_paid = {month["label"] for month in months[:member.paid_installments]}
    return normal_paid | set(member.prepaid_installments)


def couple_paid_amount(couple: Couple, months: list[dict]) -> Decimal:
    paid_by_member = [member_paid_labels(member, months) for member in couple.members]
    paid_amount = Decimal("0")
    members_count = Decimal(len(couple.members))

    for month in months:
        amount = Decimal(str(month["couple_amount"]))
        paid_count = sum(1 for labels in paid_by_member if month["label"] in labels)
        if paid_count == len(couple.members):
            paid_amount += amount
        elif paid_count:
            paid_amount += amount * Decimal(paid_count) / members_count
    return paid_amount


def couple_balance(couple: Couple, months: list[dict]) -> Decimal:
    balance = couple_total_amount(months) - couple_paid_amount(couple, months)
    return max(balance, Decimal("0"))


def compact_prepaid_label(label: str) -> str:
    month = label.split("/", maxsplit=1)[0]
    return f"{month[:3]} OK"


def format_member_progress(member: Member, installments_total: int) -> str:
    status = f"{total_paid(member)}/{installments_total}"
    if member.prepaid_installments:
        tags = ", ".join(compact_prepaid_label(label) for label in member.prepaid_installments)
        return f"{status} {tags}"
    return status


def average_progress(couple: Couple) -> Decimal:
    total = sum(total_paid(member) for member in couple.members)
    return Decimal(total) / Decimal(len(couple.members))


def format_couple_progress(couple: Couple, installments_total: int) -> str:
    statuses = [format_member_progress(member, installments_total) for member in couple.members]
    if len(set(statuses)) == 1:
        return statuses[0]
    status = " | ".join(f"{member.name} {format_member_progress(member, installments_total)}" for member in couple.members)
    return f"Misto: {status}"


def build_text(data: dict, couples: list[Couple], total_amount: Decimal) -> str:
    installments_total = data["installments_total"]
    months = data["payment_rule"]["months"]
    total_per_couple = couple_total_amount(months)

    lines = [
        data["trip_name"],
        f"Total da hospedagem: {brl(total_amount)}",
        f"Total por casal: {brl(total_per_couple)}",
        f"Parcela do casal: {brl(Decimal(str(months[0]['couple_amount'])))} de junho a outubro e {brl(Decimal(str(months[-1]['couple_amount'])))} em novembro.",
        "",
        "Vencimentos:",
    ]
    for month in months:
        due = datetime.strptime(month["due_date"], "%Y-%m-%d").strftime(DATE_FMT)
        lines.append(f"- {month['label']}: {due} | {brl(Decimal(str(month['couple_amount'])))} por casal")

    lines.extend(["", "Resumo por casal:"])
    for couple in couples:
        progress = format_couple_progress(couple, installments_total)
        lines.append(f"- {couple.name}: {progress} | falta {brl(couple_balance(couple, months))}")

    lines.extend(["", "Resumo por pessoa:"])
    for couple in couples:
        for member in couple.members:
            lines.append(f"- {member.name}: {format_member_progress(member, installments_total)}")
    return "\n".join(lines) + "\n"


def create_gradient_background(width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), BG_TOP)
    draw = ImageDraw.Draw(image)
    top_rgb = tuple(int(BG_TOP[i:i + 2], 16) for i in (1, 3, 5))
    bottom_rgb = tuple(int(BG_BOTTOM[i:i + 2], 16) for i in (1, 3, 5))
    for y in range(height):
        ratio = y / max(height - 1, 1)
        line_color = tuple(int(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * ratio) for i in range(3))
        draw.line((0, y, width, y), fill=line_color)
    return image


def rounded_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: str, radius: int = 28, outline: str | None = None) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=2 if outline else 0)


def draw_text(draw: ImageDraw.ImageDraw, pos: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, fill: str) -> tuple[int, int]:
    draw.text(pos, text, font=font, fill=fill)
    bbox = draw.textbbox(pos, text, font=font)
    return bbox[2], bbox[3]


def draw_progress_bar(draw: ImageDraw.ImageDraw, x: int, y: int, width: int, progress: float) -> None:
    rounded_box(draw, (x, y, x + width, y + 18), ACCENT_SOFT, radius=9)
    fill_width = max(18, int(width * max(0.0, min(progress, 1.0)))) if progress > 0 else 0
    if fill_width:
        rounded_box(draw, (x, y, x + fill_width, y + 18), ACCENT, radius=9)


def progress_color(progress: float) -> str:
    progress = max(0.0, min(1.0, progress))
    hue = progress * 128
    chroma = 0.72
    light = 0.48
    return hsl_to_hex(hue, chroma, light)


def hsl_to_hex(hue: float, saturation: float, lightness: float) -> str:
    chroma = (1 - abs(2 * lightness - 1)) * saturation
    x = chroma * (1 - abs((hue / 60) % 2 - 1))
    if 0 <= hue < 60:
        red, green, blue = chroma, x, 0
    elif 60 <= hue < 120:
        red, green, blue = x, chroma, 0
    else:
        red, green, blue = 0, chroma, x
    m = lightness - chroma / 2
    rgb = tuple(round((channel + m) * 255) for channel in (red, green, blue))
    return "#" + "".join(f"{channel:02X}" for channel in rgb)


def mix_hex(color: str, white_ratio: float) -> str:
    rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    mixed = tuple(round(channel + (255 - channel) * white_ratio) for channel in rgb)
    return "#" + "".join(f"{channel:02X}" for channel in mixed)


def draw_preview_card(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    label: str,
    value: str,
    color: str,
    label_font: ImageFont.FreeTypeFont,
    value_font: ImageFont.FreeTypeFont,
) -> None:
    rounded_box(draw, xy, color, radius=18)
    x1, y1, x2, _ = xy
    draw.rounded_rectangle((x2 - 82, y1 - 36, x2 + 36, y1 + 84), radius=32, fill=mix_hex(color, 0.24))
    draw.text((x1 + 22, y1 + 22), label, font=label_font, fill="#F4FAFF")
    draw.text((x1 + 22, y1 + 58), value, font=value_font, fill="#FFFFFF")


def render_image(data: dict, couples: list[Couple], total_amount: Decimal) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image = create_gradient_background(CANVAS_WIDTH, CANVAS_HEIGHT)
    draw = ImageDraw.Draw(image)

    title_font = load_font(58, bold=True)
    section_title_font = load_font(34, bold=True)
    body_font = load_font(28)
    small_font = load_font(23)
    badge_font = load_font(22, bold=True)
    amount_font = load_font(44, bold=True)

    draw.ellipse((830, -80, 1140, 230), fill="#D7E8D8")
    draw.ellipse((-120, 1230, 180, 1530), fill="#EAD7C8")

    draw.text((80, 72), "Painel de Pagamentos", font=title_font, fill=TEXT_DARK)
    draw.text((82, 144), data["group_name"], font=body_font, fill=TEXT_MUTED)

    rounded_box(draw, (60, 210, 1020, 360), CARD_BG, outline=DIVIDER)
    draw.text((95, 248), "Hospedagem total", font=small_font, fill=TEXT_MUTED)
    draw.text((95, 285), brl(total_amount), font=amount_font, fill=TEXT_DARK)
    draw.text((615, 248), "Total por casal", font=small_font, fill=TEXT_MUTED)
    draw.text((615, 285), brl(couple_total_amount(data["payment_rule"]["months"])), font=amount_font, fill=TEXT_DARK)

    rounded_box(draw, (60, 395, 1020, 840), CARD_BG, outline=DIVIDER)
    draw.text((90, 430), "Vencimentos", font=section_title_font, fill=TEXT_DARK)
    draw.text((90, 475), "Dia 07 de cada mes, antecipando apenas quando cair no fim de semana.", font=small_font, fill=TEXT_MUTED)

    months = data["payment_rule"]["months"]
    chip_x = 90
    chip_y = 530
    chip_w = 420
    chip_h = 82
    row_gap = 22
    col_gap = 34
    for index, month in enumerate(months):
        row = index // 2
        col = index % 2
        x = chip_x + col * (chip_w + col_gap)
        y = chip_y + row * (chip_h + row_gap)
        rounded_box(draw, (x, y, x + chip_w, y + chip_h), "#F6FAF8", radius=24, outline="#E3ECE7")
        due = datetime.strptime(month["due_date"], "%Y-%m-%d").strftime(DATE_FMT)
        draw.text((x + 24, y + 18), month["label"], font=body_font, fill=TEXT_DARK)
        draw.text((x + 24, y + 46), due, font=small_font, fill=TEXT_MUTED)
        amount = brl(Decimal(str(month["couple_amount"])))
        bbox = draw.textbbox((0, 0), amount, font=badge_font)
        badge_w = bbox[2] - bbox[0] + 24
        rounded_box(draw, (x + chip_w - badge_w - 22, y + 21, x + chip_w - 22, y + 57), ACCENT_SOFT, radius=18)
        draw.text((x + chip_w - badge_w - 10, y + 28), amount, font=badge_font, fill=ACCENT)

    rounded_box(draw, (60, 875, 1020, 1240), CARD_BG, outline=DIVIDER)
    draw.text((90, 910), "Saldo por casal", font=section_title_font, fill=TEXT_DARK)
    card_top = 970
    for index, couple in enumerate(couples):
        y = card_top + index * 63
        if index:
            draw.line((90, y - 16, 990, y - 16), fill=DIVIDER, width=2)
        avg = average_progress(couple)
        progress_ratio = float(avg / Decimal(data["installments_total"]))
        draw.text((92, y), couple.name, font=body_font, fill=TEXT_DARK)
        progress_text = format_couple_progress(couple, data["installments_total"])
        members_text = " + ".join(member.name for member in couple.members)
        draw.text((272, y), f"{members_text} - {progress_text}", font=small_font, fill=TEXT_MUTED)
        balance_text = f"Falta {brl(couple_balance(couple, months))}"
        balance_box = draw.textbbox((0, 0), balance_text, font=small_font)
        balance_x = 990 - (balance_box[2] - balance_box[0])
        draw.text((balance_x, y), balance_text, font=small_font, fill=ACCENT)
        draw_progress_bar(draw, 92, y + 34, 898, progress_ratio)

    rounded_box(draw, (60, 1275, 1020, 1740), CARD_BG, outline=DIVIDER)
    draw.text((90, 1310), "Resumo por pessoa", font=section_title_font, fill=TEXT_DARK)

    col_width = 430
    left_x = 92
    right_x = 552
    base_y = 1370
    for idx, couple in enumerate(couples):
        pair_x = left_x if idx % 2 == 0 else right_x
        pair_y = base_y + (idx // 2) * 154
        draw.text((pair_x, pair_y), couple.name, font=small_font, fill=TEXT_MUTED)
        for member_index, member in enumerate(couple.members):
            row_y = pair_y + 34 + member_index * 46
            draw.text((pair_x, row_y), member.name, font=body_font, fill=TEXT_DARK)
            status = format_member_progress(member, data["installments_total"])
            status_box = draw.textbbox((0, 0), status, font=small_font)
            text_x = pair_x + col_width - (status_box[2] - status_box[0])
            draw.text((text_x, row_y + 3), status, font=small_font, fill=ACCENT)
            draw_progress_bar(draw, pair_x, row_y + 30, col_width, total_paid(member) / data["installments_total"])

    draw.text((80, 1765), "Atualize os pagamentos em data.json e execute: python3 generate_panel.py", font=small_font, fill=TEXT_MUTED)
    image.save(PNG_PATH, quality=95)


def render_social_preview(data: dict, couples: list[Couple], total_amount: Decimal) -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (PREVIEW_WIDTH, PREVIEW_HEIGHT), "#F4F7FB")
    draw = ImageDraw.Draw(image)

    months = data["payment_rule"]["months"]
    group_paid = sum(couple_paid_amount(couple, months) for couple in couples)
    group_balance = total_amount - group_paid
    paid_installments = sum(total_paid(member) for couple in couples for member in couple.members)
    total_installments = len(couples) * 2 * data["installments_total"]
    overall_progress = paid_installments / total_installments
    overall_color = progress_color(overall_progress)

    title_font = load_font(54, bold=True)
    subtitle_font = load_font(25)
    section_font = load_font(28, bold=True)
    body_font = load_font(23, bold=True)
    small_font = load_font(19)
    amount_font = load_font(34, bold=True)
    percent_font = load_font(44, bold=True)

    for x in range(0, PREVIEW_WIDTH, 42):
        draw.line((x, 0, x, PREVIEW_HEIGHT), fill="#E7EDF6", width=1)
    for y in range(0, PREVIEW_HEIGHT, 42):
        draw.line((0, y, PREVIEW_WIDTH, y), fill="#E7EDF6", width=1)

    draw.ellipse((-135, 95, 165, 395), fill="#F3D8D3")
    draw.ellipse((930, -115, 1285, 240), fill="#D7F0DF")

    rounded_box(draw, (48, 36, 96, 84), "#FFFFFF", radius=13)
    draw.text((62, 51), "VP", font=small_font, fill=overall_color)
    draw.text((112, 50), "Viagem Pay", font=body_font, fill=TEXT_DARK)

    draw.text((48, 118), data["group_name"].upper(), font=small_font, fill=overall_color)
    draw.text((48, 148), "Painel de Pagamentos", font=title_font, fill=TEXT_DARK)
    draw.text((50, 212), "Hospedagem, parcelas e saldos em tempo real.", font=subtitle_font, fill=TEXT_MUTED)

    rounded_box(draw, (835, 92, 1138, 252), "#FFFFFF", radius=18, outline="#E5ECF5")
    draw.text((862, 123), "Progresso geral", font=small_font, fill=TEXT_MUTED)
    draw.text((862, 154), f"{round(overall_progress * 100)}%", font=percent_font, fill=TEXT_DARK)
    rounded_box(draw, (862, 217, 1110, 228), "#DCE7F8", radius=6)
    rounded_box(draw, (862, 217, 862 + max(8, int(248 * overall_progress)), 228), overall_color, radius=6)

    card_y = 282
    draw_preview_card(draw, (48, card_y, 296, card_y + 112), "Total hospedagem", brl(total_amount), PREVIEW_BLUE, small_font, amount_font)
    draw_preview_card(draw, (316, card_y, 564, card_y + 112), "Total por casal", brl(couple_total_amount(months)), PREVIEW_MINT, small_font, amount_font)
    draw_preview_card(draw, (584, card_y, 832, card_y + 112), "Pago pelo grupo", brl(group_paid), overall_color, small_font, amount_font)
    draw_preview_card(draw, (852, card_y, 1100, card_y + 112), "Falta no grupo", brl(group_balance), PREVIEW_DARK, small_font, amount_font)

    rounded_box(draw, (48, 430, 1172, 594), "#FFFFFF", radius=18, outline="#E5ECF5")
    draw.text((78, 460), "Saldo por casal", font=section_font, fill=TEXT_DARK)
    draw.text((905, 464), "Status atualizado para WhatsApp", font=small_font, fill=TEXT_MUTED)

    left_x = 78
    right_x = 618
    row_y = 512
    for index, couple in enumerate(couples):
        x = left_x if index % 2 == 0 else right_x
        y = row_y + (index // 2) * 44
        ratio = float(average_progress(couple) / Decimal(data["installments_total"]))
        color = progress_color(ratio)
        progress = format_couple_progress(couple, data["installments_total"])
        draw.ellipse((x, y, x + 28, y + 28), fill=mix_hex(color, 0.78))
        draw.pieslice((x, y, x + 28, y + 28), start=-90, end=-90 + int(360 * ratio), fill=color)
        draw.ellipse((x + 7, y + 7, x + 21, y + 21), fill="#FFFFFF")
        draw.text((x + 42, y - 2), couple.name, font=body_font, fill=TEXT_DARK)
        draw.text((x + 145, y), progress, font=small_font, fill=TEXT_MUTED)
        draw.text((x + 300, y), f"Falta {brl(couple_balance(couple, months))}", font=small_font, fill=color)

    draw.text((48, 608), "Acesse o link para ver o board completo atualizado.", font=small_font, fill=TEXT_MUTED)
    image.save(SITE_PREVIEW_PATH, quality=95)


def sync_site_data() -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DATA_PATH.write_text(DATA_PATH.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> None:
    data = load_json(DATA_PATH)
    validate_due_dates(data["payment_rule"]["months"])
    total_amount = validate_financials(data)
    couples = parse_couples(data)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_PATH.write_text(build_text(data, couples, total_amount), encoding="utf-8")
    render_image(data, couples, total_amount)
    render_social_preview(data, couples, total_amount)
    sync_site_data()
    print(f"Arquivos gerados:\n- {PNG_PATH}\n- {TEXT_PATH}")


if __name__ == "__main__":
    main()
