import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import tempfile

# --- PDF Processing Function ---
def add_styled_table_to_pdf(input_pdf_path, logo_img_path, sign_img_path, output_path, fields, placement="corner"):
    try:
        doc = fitz.open(input_pdf_path)
    except Exception as e:
        st.error(f"PDF file could not be opened: {e}")
        st.stop()

    sky_blue = (0.53, 0.81, 0.98)
    text_color = (0, 0, 0)
    bg_color = (1, 1, 1)

    margin = 10
    row_height = 18
    project_row_height = 36
    submitted_row_height = 50  # Increased height for logo
    label_col_width = 90
    content_col_width = 180
    project_col_width = 260
    submitted_col_width = 260
    logo_row_height = row_height

    table_fields = [
        ("DR. NO.", "drno"),
        ("TITLE", "title"),
        ("CLIENT", "client"),
        ("PROJECT", "project"),
        ("WORK ORDER REF", "workorder"),
        ("CONTRACTOR NAME", "contractor"),
        ("CONSULTANT NAME", "consultant"),
        ("SUBMITTED BY", "submitted"),
        ("CHECKED BY", "checked"),
        ("APPROVED BY", "approved"),
    ]

    def process_image(image_file):
        try:
            img = Image.open(image_file).convert("RGBA")
            if img.height == 0 or img.width == 0:
                raise ValueError("Image has invalid dimensions.")
            return img
        except Exception as e:
            st.error(f"Image processing failed: {e}")
            st.stop()

    def shift_overlapping_content_up(page, table_rect, shift_amount):
        blocks = page.get_text("blocks")
        overlapping_blocks = []
        for block in blocks:
            block_rect = fitz.Rect(block[:4])
            if block_rect.intersects(table_rect):
                overlapping_blocks.append(block)
        for block in overlapping_blocks:
            block_rect = fitz.Rect(block[:4])
            page.draw_rect(block_rect, color=bg_color, fill=bg_color)
        for block in overlapping_blocks:
            text = block[4]
            block_rect = fitz.Rect(block[:4])
            new_rect = fitz.Rect(
                block_rect.x0,
                block_rect.y0 - shift_amount,
                block_rect.x1,
                block_rect.y1 - shift_amount
            )
            page.insert_textbox(new_rect, text, fontsize=7.8, fontname="helv", color=text_color)

    logo_img = process_image(logo_img_path)
    sign_img = process_image(sign_img_path)

    for page in doc:
        pw, ph = page.rect.width, page.rect.height

        visible_fields = [(label, key) for (label, key) in table_fields if fields.get(key, "").strip()]
        row_heights = []
        content_widths = []

        for label, key in visible_fields:
            if key == "project":
                row_heights.append(project_row_height)
                content_widths.append(project_col_width)
            elif key == "submitted":
                row_heights.append(submitted_row_height)
                content_widths.append(submitted_col_width)
            else:
                row_heights.append(row_height)
                content_widths.append(content_col_width)

        row_heights.append(logo_row_height)
        content_widths.append(project_col_width)

        table_width = label_col_width + max(content_widths)
        total_height = sum(row_heights)

        if placement == "footer":
            table_left_x = margin
            table_right_x = pw - margin
        else:
            table_right_x = pw - margin
            table_left_x = table_right_x - table_width

        table_bottom_y = ph - margin
        table_top_y = table_bottom_y - total_height
        table_rect = fitz.Rect(table_left_x, table_top_y, table_right_x, table_bottom_y)

        shift_amount = total_height + margin
        shift_overlapping_content_up(page, table_rect, shift_amount)

        page.draw_rect(table_rect, color=sky_blue, fill=bg_color)

        y = table_top_y
        for h in row_heights:
            page.draw_line((table_left_x, y), (table_right_x, y), color=sky_blue, width=0.8)
            y += h

        col_split_x = table_left_x + label_col_width
        page.draw_line((col_split_x, table_top_y), (col_split_x, table_bottom_y), color=sky_blue, width=0.8)
        page.draw_line((table_right_x, table_top_y), (table_right_x, table_bottom_y), color=sky_blue, width=0.8)

        y = table_top_y
        for idx, (label, key) in enumerate(visible_fields):
            h = row_heights[idx]
            c_width = content_widths[idx]
            label_rect = fitz.Rect(table_left_x + 3, y + 2, col_split_x - 2, y + h)
            content_rect = fitz.Rect(col_split_x + 3, y + 2, col_split_x + c_width - 3, y + h)

            page.insert_textbox(label_rect, label, fontsize=7.8, fontname="helv", color=text_color, align=0)

            if key == "submitted":
                submitted_name = fields.get(key, "")
                name_rect = fitz.Rect(col_split_x + 3, y + 2, col_split_x + submitted_col_width - 60, y + h)
                page.insert_textbox(name_rect, submitted_name, fontsize=7.8, fontname="helv", color=text_color, align=0)
                if sign_img.height > 0:
                    scale = (h - 6) / sign_img.height
                    sign_target_width = sign_img.width * scale
                    sign_x0 = col_split_x + submitted_col_width - sign_target_width - 4
                    sign_x1 = col_split_x + submitted_col_width - 4
                    sign_y0 = y + (h - sign_img.height * scale) / 2
                    sign_y1 = sign_y0 + sign_img.height * scale
                    sign_rect = fitz.Rect(sign_x0, sign_y0, sign_x1, sign_y1)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_sign_img:
                        sign_img.save(temp_sign_img.name)
                        page.insert_image(sign_rect, filename=temp_sign_img.name, keep_proportion=True)
            else:
                content = fields.get(key, "")
                page.insert_textbox(content_rect, content, fontsize=7.8, fontname="helv", color=text_color, align=0)
            y += h

        logo_row_top = table_bottom_y - logo_row_height + 2
        logo_rect = fitz.Rect(table_left_x + 2, logo_row_top, table_right_x - 2, table_bottom_y - 2)
        logo_img_resized = logo_img.resize((int(logo_rect.width), int(logo_rect.height)), Image.LANCZOS)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_logo_img:
            logo_img_resized.save(temp_logo_img.name)
            page.insert_image(logo_rect, filename=temp_logo_img.name)

    doc.save(output_path)

# --- Streamlit App ---
st.set_page_config(page_title="PDF Title-Block Stamper")
st.title("📄 PDF Title-Block Stamper")

with st.form("pdf_form"):
    st.subheader("📝 Enter Table Details")
    drno = st.text_input("DR. NO.")
    title = st.text_input("TITLE")
    client = st.text_input("CLIENT")
    project = st.text_area("PROJECT", height=50)
    workorder = st.text_input("WORK ORDER REF")
    contractor = st.text_input("CONTRACTOR NAME")
    consultant = st.text_input("CONSULTANT NAME")
    submitted = st.text_input("SUBMITTED BY")
    checked = st.text_input("CHECKED BY")
    approved = st.text_input("APPROVED BY")

    st.subheader("📎 Upload Files")
    sign_file = st.file_uploader("Upload Signature (Submitted By)", type=["png", "jpg", "jpeg"])
    logo_file = st.file_uploader("Upload Company Logo", type=["png", "jpg", "jpeg"])
    pdf_file = st.file_uploader("Upload PDF", type="pdf")

    placement = st.radio("📌 Table Placement", ["Bottom Right Corner", "Footer (Full Width)"])
    submitted_btn = st.form_submit_button("🚀 Generate PDF")

if submitted_btn:
    if not all([pdf_file, logo_file, sign_file]):
        st.warning("Please upload all files (PDF, logo, and signature).")
    else:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                temp_pdf.write(pdf_file.read())
                temp_pdf.flush()
                input_pdf_path = temp_pdf.name

            with tempfile.NamedTemporaryFile(delete=False) as temp_logo:
                temp_logo.write(logo_file.read())
                temp_logo.flush()
                logo_path = temp_logo.name

            with tempfile.NamedTemporaryFile(delete=False) as temp_sign:
                temp_sign.write(sign_file.read())
                temp_sign.flush()
                sign_path = temp_sign.name

            output_pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix="_output.pdf").name

            field_data = {
                "drno": drno,
                "title": title,
                "client": client,
                "project": project,
                "workorder": workorder,
                "contractor": contractor,
                "consultant": consultant,
                "submitted": submitted,
                "checked": checked,
                "approved": approved
            }

            mode = "footer" if placement == "Footer (Full Width)" else "corner"
            add_styled_table_to_pdf(input_pdf_path, logo_path, sign_path, output_pdf_path, field_data, placement=mode)

            with open(output_pdf_path, "rb") as f:
                st.success("✅ PDF updated successfully!")
                st.download_button("📥 Download Updated PDF", f, file_name="updated_output.pdf", mime="application/pdf")

        except Exception as e:
            st.error(f"An error occurred: {e}")