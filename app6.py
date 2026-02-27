import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="AI Lab Report Analyzer", layout="wide")

st.title("🩺 AI Lab Report Analyzer")
st.write("Upload your lab report PDF to extract structured test results.")


# -------- SMART PDF PARSER --------
def parse_lab_report(uploaded_file):
    results = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:

            # 1️⃣ Try table extraction first
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if row and len(row) >= 2:
                            test = row[0]
                            value = row[1]
                            unit = row[2] if len(row) > 2 else ""
                            reference = row[3] if len(row) > 3 else ""

                            if test and value and test.strip().lower() not in ["test", ""]:
                                results.append({
                                    "Test": test.strip(),
                                    "Value": value.strip(),
                                    "Unit": unit.strip(),
                                    "Reference Range": reference.strip()
                                })

            # 2️⃣ Fallback: Text-based parsing
            else:
                text = page.extract_text()
                if text:
                    lines = text.split("\n")

                    for line in lines:
                        # Regex pattern: TestName   12.5   mg/dL   10-20
                        match = re.match(
                            r"([A-Za-z\s]+)\s+([\d.]+)\s*([A-Za-z/%]*)\s*([\d.-]+\s*-\s*[\d.-]+)?",
                            line
                        )

                        if match:
                            test = match.group(1).strip()
                            value = match.group(2)
                            unit = match.group(3) if match.group(3) else ""
                            reference = match.group(4) if match.group(4) else ""

                            results.append({
                                "Test": test,
                                "Value": value,
                                "Unit": unit,
                                "Reference Range": reference
                            })

    return results


# -------- FILE UPLOAD --------
uploaded_file = st.file_uploader("📄 Upload Lab Report (PDF)", type="pdf")

if uploaded_file is not None:
    st.success("PDF uploaded successfully!")

    report_data = parse_lab_report(uploaded_file)

    if report_data:
        st.subheader("🔍 Extracted Test Results")
        st.dataframe(report_data)
    else:
        st.warning("No structured lab data found in the PDF.")