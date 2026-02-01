# utils/pdf/daily_report_pdf.py
# 点呼＋点検＋日報 1日1PDF 生成（完全同期・監査対応版）

import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from utils.db import get_connection

# -------------------------
# 日本語フォント登録
# -------------------------
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF_DIR = os.path.join(BASE_DIR, "pdf")
os.makedirs(PDF_DIR, exist_ok=True)


# ==================================================
# メイン関数
# ==================================================
def generate_daily_report_pdf(driver_id: int, record_date: str):
    """
    driver_id + record_date の1日分PDFを生成
    return: pdf_path
    """

    conn = get_connection()
    c = conn.cursor()

    # -------------------------
    # ドライバー情報
    # -------------------------
    driver = c.execute("""
        SELECT d.driver_name, d.driver_code, c.company_name
        FROM drivers d
        JOIN companies c ON d.company_id = c.id
        WHERE d.id = ?
    """, (driver_id,)).fetchone()

    # -------------------------
    # 点呼（前・後）※ ★日常点検実施フラグ含む
    # -------------------------
    tenko = c.execute("""
        SELECT
            timing,
            record_time,
            health,
            alcohol,
            checker,
            memo,
            daily_check_done
        FROM tenko_records
        WHERE driver_id = ? AND record_date = ?
    """, (driver_id, record_date)).fetchall()

    tenko_before = next((t for t in tenko if t["timing"] == "before"), None)
    tenko_after  = next((t for t in tenko if t["timing"] == "after"), None)

    # -------------------------
    # 日常点検
    # -------------------------
    check = c.execute("""
        SELECT brake, tire, light, other
        FROM daily_checks
        WHERE driver_id = ? AND record_date = ?
    """, (driver_id, record_date)).fetchone()

    # -------------------------
    # 運転日報
    # -------------------------
    report = c.execute("""
        SELECT start_time, end_time, mileage, note
        FROM daily_reports
        WHERE driver_id = ? AND record_date = ?
    """, (driver_id, record_date)).fetchone()

    conn.close()

    # -------------------------
    # PDFパス
    # -------------------------
    filename = f"daily_{driver['driver_code']}_{record_date}.pdf"
    pdf_path = os.path.join(PDF_DIR, filename)

    # -------------------------
    # PDF生成
    # -------------------------
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    styles["Normal"].fontName = "HeiseiMin-W3"
    styles["Title"].fontName = "HeiseiMin-W3"

    elements = []

    # -------------------------
    # タイトル
    # -------------------------
    elements.append(Paragraph("軽貨物運送事業　安全管理記録（日別）", styles["Title"]))
    elements.append(Spacer(1, 12))

    # -------------------------
    # 基本情報
    # -------------------------
    base_table = Table([
        ["会社名", driver["company_name"]],
        ["ドライバー名", driver["driver_name"]],
        ["業務ID", driver["driver_code"]],
        ["日付", record_date],
    ], colWidths=[100, 350])

    base_table.setStyle(_table_style())
    elements.append(base_table)
    elements.append(Spacer(1, 14))

    # -------------------------
    # 乗務前点呼
    # -------------------------
    elements.append(_section_title("乗務前点呼"))
    elements.append(_tenko_table(tenko_before, is_before=True))

    # -------------------------
    # 乗務後点呼
    # -------------------------
    elements.append(Spacer(1, 10))
    elements.append(_section_title("乗務後点呼"))
    elements.append(_tenko_table(tenko_after, is_before=False))

    # -------------------------
    # 日常点検
    # -------------------------
    elements.append(Spacer(1, 10))
    elements.append(_section_title("日常点検"))

    if check:
        check_table = Table([
            ["ブレーキ", _ok_ng(check["brake"])],
            ["タイヤ", _ok_ng(check["tire"])],
            ["灯火類", _ok_ng(check["light"])],
            ["備考", check["other"] or ""],
        ], colWidths=[100, 350])
    else:
        check_table = Table([["未実施", ""]], colWidths=[100, 350])

    check_table.setStyle(_table_style())
    elements.append(check_table)

    # -------------------------
    # 運転日報
    # -------------------------
    elements.append(Spacer(1, 10))
    elements.append(_section_title("運転日報"))

    if report:
        mileage_text = f"{report['mileage']} km" if report["mileage"] is not None else ""
        report_table = Table([
            ["出庫", report["start_time"] or ""],
            ["帰庫", report["end_time"] or ""],
            ["走行距離", mileage_text],
            ["備考", report["note"] or ""],
        ], colWidths=[100, 350])
    else:
        report_table = Table([["未提出", ""]], colWidths=[100, 350])

    report_table.setStyle(_table_style())
    elements.append(report_table)

    # -------------------------
    # PDFビルド
    # -------------------------
    doc.build(elements)

    return pdf_path


# ==================================================
# 共通部品
# ==================================================
def _section_title(text):
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = "HeiseiMin-W3"
    return Paragraph(f"<b>{text}</b>", styles["Normal"])


def _tenko_table(t, is_before: bool):
    if not t:
        table = Table([["未実施", ""]], colWidths=[100, 350])
    else:
        rows = [
            ["時刻", t["record_time"]],
            ["健康状態", t["health"]],
            ["アルコール", f"{t['alcohol']} mg/L"],
        ]

        # ★乗務前点呼のみ：日常点検実施有無
        if is_before:
            done = "実施" if t["daily_check_done"] == 1 else "未実施"
            rows.append(["日常点検", done])

        rows.extend([
            ["点呼執行者", t["checker"]],
            ["備考", t["memo"] or ""],
        ])

        table = Table(rows, colWidths=[100, 350])

    table.setStyle(_table_style())
    return table


def _ok_ng(val):
    if val is None:
        return ""
    return "◯" if val == 1 else "✕"


def _table_style():
    return TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONT", (0, 0), (-1, -1), "HeiseiMin-W3"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
    ])
