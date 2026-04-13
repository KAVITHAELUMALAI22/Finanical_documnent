"""Step 1 — Classify PDF and extract all text + tables."""
import pdfplumber

def classify_pdf(pdf_path):
    text_p = scanned_p = total = 0
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            for page in pdf.pages[:10]:
                words = (page.extract_text() or "").split()
                if len(words) > 30: text_p += 1
                else: scanned_p += 1
    except Exception as e:
        return {"type":"error","error":str(e),"total_pages":0,"text_pages":0,"scanned_pages":0}
    t = "text" if scanned_p==0 else ("scanned" if text_p==0 else "mixed")
    return {"type":t,"total_pages":total,"text_pages":text_p,"scanned_pages":scanned_p}

def extract_text(pdf_path):
    full = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                txt = page.extract_text() or ""
                tbl = ""
                for table in page.extract_tables():
                    for row in table:
                        r = "  |  ".join(str(c).strip() for c in row if c and str(c).strip())
                        if r: tbl += r + "\n"
                combined = txt + "\n" + tbl
                if len(combined.split()) > 15:
                    full += f"\n=== PAGE {i+1} ===\n{combined}\n"
    except Exception as e:
        return f"[Error: {e}]"
    return full
