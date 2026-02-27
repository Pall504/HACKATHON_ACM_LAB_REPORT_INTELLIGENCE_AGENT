import streamlit as st
import pdfplumber
import re
import pandas as pd

st.set_page_config(page_title="Lab Report Intelligence Agent", layout="wide")

st.title("🧠 Lab Report Intelligence Agent")
st.write("AI-powered lab report analysis with benchmark comparison and risk scoring.")

# ---------------- PDF PARSER ----------------
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

                            if test and value and test.strip().lower() not in ["test", ""]:
                                results.append({
                                    "Test": test.strip(),
                                    "Value": value.strip(),
                                    "Unit": unit.strip(),
                                    "Reference Range": reference.strip()
                                })
            else:
                text = page.extract_text()
                if text:
                    lines = text.split("\n")
                    for line in lines:
                        match = re.match(
                            r"([A-Za-z\s]+)\s+([\d.]+)\s*([A-Za-z/%]*)\s*([\d.-]+\s*-\s*[\d.-]+)?",
                            line
                        )
                        if match:
                            results.append({
                                "Test": match.group(1).strip(),
                                "Value": match.group(2),
                                "Unit": match.group(3) if match.group(3) else "",
                                "Reference Range": match.group(4) if match.group(4) else ""
                            })

    return results


# ---------------- BENCHMARK CHECK ----------------
def check_abnormal(value, ref_range):
    try:
        if "-" in ref_range:
            low, high = ref_range.split("-")
            low = float(low.strip())
            high = float(high.strip())
            value = float(value)

            if value < low:
                return "Low"
            elif value > high:
                return "High"
            else:
                return "Normal"
        else:
            return "Unknown"
    except:
        return "Unknown"


# ---------------- RISK SCORING ----------------
def calculate_risk(data):
    risk_score = 0

    for row in data:
        if row["Status"] == "High":
            risk_score += 10
        elif row["Status"] == "Low":
            risk_score += 5

    if risk_score < 20:
        level = "Low Risk"
    elif risk_score < 50:
        level = "Moderate Risk"
    else:
        level = "High Risk"

    return risk_score, level


# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("📄 Upload Lab Report (PDF)", type="pdf")

if uploaded_file:
    st.success("PDF uploaded successfully!")

    report_data = parse_lab_report(uploaded_file)

    if report_data:
        # Convert to DataFrame
        df = pd.DataFrame(report_data)

        # Add Status Column
        df["Status"] = df.apply(
            lambda row: check_abnormal(row["Value"], row["Reference Range"]),
            axis=1
        )

        st.subheader("🔍 Extracted & Analyzed Results")
        st.dataframe(df)

        # Risk Score
        risk_score, risk_level = calculate_risk(df.to_dict("records"))

        st.subheader("📊 Health Risk Assessment")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Risk Score", risk_score)

        with col2:
            if risk_level == "Low Risk":
                st.success(risk_level)
            elif risk_level == "Moderate Risk":
                st.warning(risk_level)
            else:
                st.error(risk_level)

        # Pattern Detection
        st.subheader("🧬 Pattern Insights")

        patterns = []
        if "Hemoglobin" in df["Test"].values:
            hb = df[df["Test"] == "Hemoglobin"]["Status"].values[0]
            if hb == "Low":
                patterns.append("Possible anemia pattern detected.")

        if "Cholesterol" in df["Test"].values:
            chol = df[df["Test"] == "Cholesterol"]["Status"].values[0]
            if chol == "High":
                patterns.append("Elevated cholesterol may increase cardiac risk.")

        if patterns:
            for p in patterns:
                st.warning(p)
        else:
            st.info("No major health risk patterns detected.")

        # Summary
        st.subheader("📝 AI-Generated Summary")

        abnormal_tests = df[df["Status"] != "Normal"]

        if not abnormal_tests.empty:
            st.write("The following values are outside normal range:")
            st.write(abnormal_tests[["Test", "Value", "Status"]])
            st.write("It is recommended to consult a healthcare professional for further evaluation.")
        else:
            st.success("All parameters appear within normal limits.")

        st.caption("⚠️ This tool provides informational insights only and is not a medical diagnosis.")

    else:
        st.warning("No structured lab data found in the PDF.")