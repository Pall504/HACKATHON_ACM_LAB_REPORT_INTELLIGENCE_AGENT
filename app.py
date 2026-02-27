import streamlit as st
import pdfplumber

# Page settings
st.set_page_config(page_title="AI Lab Report Analyzer", layout="wide")

st.title("🩺 AI Lab Report Analyzer")
st.write("Upload your lab report PDF to extract structured test results.")

# -------- PDF Parsing Function --------
def parse_lab_report(uploaded_file):
    results = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            if tables:
                for table in tables:
                    for row in table:
                        if row and len(row) >= 2:
                            test = row[0]
                            value = row[1]
                            unit = row[2] if len(row) > 2 else ""
                            reference = row[3] if len(row) > 3 else ""

                            if test and value and test.strip() not in ["TEST", ""]:
                                results.append({
                                    "Test": test.strip(),
                                    "Value": value.strip() if value else "N/A",
                                    "Unit": unit.strip() if unit else "",
                                    "Reference Range": reference.strip() if reference else ""
                                })

    return results

# -------- File Upload Section --------
uploaded_file = st.file_uploader("📄 Upload Lab Report (PDF)", type="pdf")

if uploaded_file is not None:
    st.success("PDF uploaded successfully!")

    report_data = parse_lab_report(uploaded_file)

    if report_data:
        st.subheader("🔍 Extracted Test Results")
        for item in report_data:
            st.write(item)
    else:
        st.warning("No structured lab data found in the PDF.")