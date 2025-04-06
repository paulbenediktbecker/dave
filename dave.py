import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color
import os

# ==== CONFIG ====
crop_x0 = 390  # Left
crop_y0 = 78   # Bottom
crop_x1 = 575  # Right
crop_y1 = 155  # Top
vertical_offset = -7.8  # 🔥 Move whole address 25 points lower
# =================

folder = "data"
files = os.listdir(folder)

for curr in files:
    # Step 1: Open 'without.pdf' and redact old "Deutschland"
    withoudpdf_path = f"{folder}/{curr}"
    doc_without = fitz.open(withoudpdf_path)
    page_without = doc_without[0]

    # Find and redact old "Deutschland"
    text_instances = page_without.search_for("Deutschland")
    for inst in text_instances:
        if inst.y1 > 500:  # only redact wrong "Deutschland" higher up
            page_without.add_redact_annot(inst, fill=(1, 1, 1))
    page_without.apply_redactions()

    # Save cleaned without.pdf
    doc_without.save("without_cleaned.pdf")

    # Step 2: Open 'with.pdf' and extract the address block
    doc_with = fitz.open("with.pdf")
    page_with = doc_with[0]
    page_height = page_with.rect.height

    real_crop_y0 = page_height - crop_y1
    real_crop_y1 = page_height - crop_y0
    crop_rect = fitz.Rect(crop_x0, real_crop_y0, crop_x1, real_crop_y1)

    page_dict = page_with.get_text("dict")

    # Step 3: Create a mini PDF with the shifted address block
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)

    gray_color = Color(139/255, 140/255, 142/255)  # Soft gray color
    can.setFont("Helvetica", 10.5)
    can.setFillColor(gray_color)

    for block in page_dict["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                span_rect = fitz.Rect(span["bbox"])
                if not crop_rect.intersects(span_rect):
                    continue

                text = span["text"]
                if "Rechnungsnummer" in text:
                    continue  # Skip "Rechnungsnummer" still

                fontsize = span["size"]

                x = span["bbox"][0]
                y = page_height - span["bbox"][1] + vertical_offset  # 🔥 APPLY vertical shift here!

                can.setFont("Helvetica", fontsize)
                can.drawString(x, y, text)

    can.save()
    packet.seek(0)

    # Step 4: Merge address block into cleaned 'without.pdf'
    without_pdf = PdfReader("without_cleaned.pdf")
    output = PdfWriter()

    without_page = without_pdf.pages[0]
    address_layer = PdfReader(packet).pages[0]

    without_page.merge_page(address_layer)
    output.add_page(without_page)

    # Step 5: Save final output
    final_path = f"cleaned/{curr}"
    with open(final_path, "wb") as f:
        output.write(f)

    print(f"✅ FINAL result saved: {final_path}")