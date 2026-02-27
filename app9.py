import streamlit as st
import pdfplumber
import re
import pandas as pd
import matplotlib.pyplot as plt
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Lab Report Intelligence Agent", layout="wide")
st.title("🧠 Lab Report Intelligence Agent")

# ---------------- SAFE API KEY SETUP ----------------
OPENAI_API_KEY = None

try:
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
except:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None
    st.warning("⚠️ OpenAI API key not found. LLM features disabled.")

# ---------------- LANGUAGE INPUT ----------------
language = st.text_input(
    "Enter output language (e.g., English, Hindi, Arabic, Japanese)",
    value="English"
)

# ---------------- PDF PARSER ----------------
def parse_lab_report(uploaded_file):
    results = []

    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines = text.split("\n")
                    for line in lines:
                        match = re.match(
                            r"([A-Za-z\s]+)\s+([\d.]+)\s*([A-Za-z/%]*)\s*([\d.-]+\s*-\s*[\d.-]+)?",
                            line
                        )
                        if match:
                            test = match.group(1).strip()
                            value = match.group(2)
                            unit = match.group(3) if match.group(3) else ""
                            ref = match.group(4) if match.group(4) else ""

                            if len(test) > 2 and not any(x in test.lower() for x in ["name", "date", "reg", "age"]):
                                try:
                                    results.append({
                                        "Test": test,
                                        "Value": float(value),
                                        "Unit": unit,
                                        "Reference Range": ref
                                    })
                                except:
                                    pass
    except Exception as e:
        st.error(f"PDF parsing error: {e}")

    return results


# ---------------- BENCHMARK ----------------
def check_status(value, ref_range):
    try:
        low, high = ref_range.split("-")
        low = float(low.strip())
        high = float(high.strip())

        if value < low:
            return "Low"
        elif value > high:
            return "High"
        else:
            return "Normal"
    except:
        return "Unknown"


# ---------------- RISK SCORE ----------------
def calculate_risk(df):
    score = 0
    for _, row in df.iterrows():
        if row["Status"] == "High":
            score += 15
        elif row["Status"] == "Low":
            score += 10

    if score < 20:
        level = "Low Risk"
    elif score < 50:
        level = "Moderate Risk"
    else:
        level = "High Risk"

    return score, level


# ---------------- LLM SUMMARY SAFE ----------------
def generate_llm_summary(df, risk_level, language):
    if not client:
        return "LLM explanation disabled (No API key)."

    abnormal = df[df["Status"] != "Normal"]

    prompt = f"""
    Generate a calm, professional explanation in {language}.
    Risk Level: {risk_level}
    Abnormal Tests:
    {abnormal.to_string()}
    Avoid diagnosis.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"LLM error: {e}"


# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("Upload Lab Report PDF", type="pdf")

if uploaded_file:
    data = parse_lab_report(uploaded_file)

    if data:
        df = pd.DataFrame(data)
        df["Status"] = df.apply(
            lambda row: check_status(row["Value"], row["Reference Range"]),
            axis=1
        )

        st.subheader("📊 Structured Results")
        st.dataframe(df)

        score, level = calculate_risk(df)

        col1, col2 = st.columns(2)
        col1.metric("Risk Score", score)
        col2.metric("Risk Level", level)

        st.subheader("🤖 AI Explanation")
        summary = generate_llm_summary(df, level, language)
        st.write(summary)

        st.subheader("📈 Trend Graph")

        if "history" not in st.session_state:
            st.session_state.history = []

        st.session_state.history.append(df)
        combined = pd.concat(st.session_state.history)

        for test in combined["Test"].unique():
            test_data = combined[combined["Test"] == test]
            fig, ax = plt.subplots()
            ax.plot(test_data["Value"].values)
            ax.set_title(test)
            st.pyplot(fig)

        st.caption("⚠️ This tool provides informational insights only and is not a medical diagnosis.")

    else:
        st.warning("No valid lab data detected.")