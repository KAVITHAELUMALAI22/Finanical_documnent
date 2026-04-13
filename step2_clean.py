"""Step 2 — Clean and normalise extracted text."""
import re

def clean_text(text):
    t = text.lower()
    t = re.sub(r"\brs\.?\b|\binr\b", "inr", t)
    t = re.sub(r"\bcrores?\b|\bcr\.\b", "crore", t)
    t = re.sub(r"\blakhs?\b", "lakh", t)
    t = re.sub(r"\bmillions?\b|\bmn\b", "million", t)
    t = re.sub(r"\bbillions?\b|\bbn\b", "billion", t)
    t = re.sub(r"^\s*[-=.─]{4,}\s*$", "", t, flags=re.MULTILINE)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return "\n".join(l.strip() for l in t.splitlines()).strip()
