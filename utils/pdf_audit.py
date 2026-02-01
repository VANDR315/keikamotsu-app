from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# =========================
# 日本語フォント登録
# =========================
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

# =========================
# 点呼PDF作成（運転者別対応）
# rows:
#  [date, time, driver, condition, alcohol, checker]
# =========================
def create_tenko_pdf(rows, filename, company_name=""):
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),   # A4横
        rightMargin=20,
        leftMargin=20,
        topMargin=25,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()

    base_style = ParagraphStyle(
        name="Base",
        fontName="HeiseiKakuGo-W5",
        fontSize=8,
        leading=10,
        wordWrap="CJK"
    )

    title_style = ParagraphStyle(
        name="Title",
        fontName="HeiseiKakuGo-W5",
        fontSize=14,
        leading=18,
        alignment=1  # 中央
    )

    elements = []

    # =========================
    # タイトル
    # =========================
    elements.append(
        Paragraph("点呼記録簿（貨物軽自動車運送事業）", title_style)
    )
    elements.append(Spacer(1, 6))

    if company_name:
        elements.append(
            Paragraph(f"事業者名：{company_name}", base_style)
        )
        elements.append(Spacer(1, 6))

    elements.append(
        Paragraph("【国土交通省 監査対応様式】", base_style)
    )
    elements.append(Spacer(1, 12))

    # =========================
    # 表ヘッダ
    # =========================
    table_data = [[
        Paragraph("日付", base_style),
        Paragraph("時刻", base_style),
        Paragraph("運転者氏名", base_style),
        Paragraph("点呼区分", base_style),
        Paragraph("健康状態", base_style),
        Paragraph("酒気帯び", base_style),
        Paragraph("点呼実施者", base_style),
        Paragraph("備考", base_style),
    ]]

    # =========================
    # 表データ
    # =========================
    for r in rows:
        date = r[0]
        time = r[1]          # 09:15 形式
        driver = r[2]
        condition = r[3]
        alcohol = r[4]
        checker = r[5]

        table_data.append([
            Paragraph(date, base_style),
            Paragraph(time, base_style),
            Paragraph(driver, base_style),
            Paragraph("業務前", base_style),
            Paragraph(condition, base_style),
            Paragraph(alcohol, base_style),
            Paragraph(checker, base_style),
            Paragraph("", base_style),
        ])

    # =========================
    # テーブル作成
    # =========================
    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            70,   # 日付
            55,   # 時刻
            110,  # 運転者
            80,   # 点呼区分
            85,   # 健康状態
            85,   # 酒気帯び
            100,  # 点呼者
            120   # 備考
        ],
        rowHeights=22
    )

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    elements.append(table)

    # =========================
    # PDF生成
    # =========================
    doc.build(elements)
