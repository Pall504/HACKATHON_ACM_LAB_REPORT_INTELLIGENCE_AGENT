import streamlit as st
import pdfplumber
import re
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from groq import Groq

# ============ MEDICAL BENCHMARKS BACKEND ============
class MedicalBenchmarks:
    def __init__(self):
        self.ranges = {
            "Glucose": {"normal": (70, 99), "unit": "mg/dL"},
            "Hemoglobin": {"normal_male": (13.5, 17.5), "normal_female": (12.0, 15.5), "unit": "g/dL"},
            "Cholesterol": {"normal": (125, 200), "borderline": (200, 239), "high": (240, 999), "unit": "mg/dL"},
            "HDL": {"normal_male": (40, 60), "normal_female": (50, 60), "unit": "mg/dL"},
            "LDL": {"optimal": (0, 100), "borderline": (130, 159), "high": (160, 999), "unit": "mg/dL"},
            "Triglycerides": {"normal": (0, 149), "borderline": (150, 199), "high": (200, 999), "unit": "mg/dL"},
            "Creatinine": {"normal_male": (0.7, 1.3), "normal_female": (0.6, 1.1), "unit": "mg/dL"},
            "ALT": {"normal_male": (7, 55), "normal_female": (7, 45), "unit": "U/L"},
            "AST": {"normal": (8, 48), "unit": "U/L"},
        }
    
    def compare(self, test_name, value, gender="male"):
        test_name = test_name.strip().title()
        if test_name not in self.ranges:
            return {"status": "unknown", "message": "No reference range"}
        ref = self.ranges[test_name]
        
        if test_name == "Hemoglobin":
            key = f"normal_{gender}"
            if key in ref:
                min_val, max_val = ref[key]
                if value < min_val: return {"status": "low", "message": f"Low ({min_val}-{max_val})"}
                elif value > max_val: return {"status": "high", "message": f"High ({min_val}-{max_val})"}
                else: return {"status": "normal", "message": "Normal"}
        
        if "normal" in ref:
            min_val, max_val = ref["normal"]
            if value < min_val: return {"status": "low", "message": f"Below normal ({min_val}-{max_val})"}
            elif value > max_val: return {"status": "high", "message": f"Above normal ({min_val}-{max_val})"}
            else: return {"status": "normal", "message": "Normal"}
        return {"status": "unknown", "message": "Check manually"}

class HealthAnalyzer:
    def __init__(self): self.benchmarks = MedicalBenchmarks()
    def analyze(self, lab_values, gender="male"):
        results, alerts = [], []
        for test in lab_values:
            comparison = self.benchmarks.compare(test["test"], test["value"], gender)
            result = {"test": test["test"], "value": test["value"], "unit": test["unit"], 
                     "status": comparison["status"], "message": comparison["message"]}
            results.append(result)
            if comparison["status"] in ["low", "high"]: alerts.append(result)
        health_score = self._calculate_score(results)
        return {"results": results, "alerts": alerts, "health_score": health_score, "alert_count": len(alerts)}
    
    def _calculate_score(self, results):
        if not results: return 50
        score = sum(100 if r["status"] == "normal" else 40 for r in results)
        return round(score / len(results))

# ============ AI RAG SETUP ============
GROQ_API_KEY = "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"  # Your key
client = Groq(api_key=GROQ_API_KEY)

SKIP_KEYWORDS = ["patient", "referred", "reg", "collected", "reported", "urine routine", 
                 "physical examination", "chemical examination", "microscopic examination"]

RISK_WEIGHTS = {"ketone bodies": 4, "bilirubin": 5, "sugar / glucose": 5, "protein / albumin": 4,
                "blood": 4, "leukocytes": 3, "nitrite": 3, "pus cells": 3, "r.b.c.": 3, "ph": 2}

medical_knowledge = [
    "Ketone bodies in urine indicate the body is burning fat for energy, commonly seen in fasting, low carb diets, or uncontrolled diabetes.",
    "Bilirubin in urine can indicate liver disease, bile duct obstruction, or hemolytic anemia.",
    "Protein in urine may indicate kidney disease, urinary tract infection, or high blood pressure.",
    "High blood sugar in urine is commonly associated with diabetes mellitus.",
    "Nitrites in urine typically indicate bacterial infection in the urinary tract.",
    "Leukocytes in urine suggest inflammation or infection in the urinary tract.",
    "RBC in urine may indicate kidney stones, infection, or kidney disease.",
    "Pus cells in urine indicate urinary tract infection or kidney inflammation."
]

@st.cache_resource
def load_rag():
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(medical_knowledge).astype('float32')
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return model, index

def parse_lab_report(pdf_file):
    results = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 2: continue
                    test = row[0]
                    value = row[1] if len(row) > 1 else ""
                    unit = row[2] if len(row) > 2 else ""
                    reference = row[3] if len(row) > 3 else ""
                    
                    if not test or not value: continue
                    if any(skip in str(test).lower() for skip in SKIP_KEYWORDS): continue
                    
                    try:
                        val_float = float(str(value).strip())
                        results.append({
                            "test": str(test).strip(),
                            "value": val_float,
                            "unit": str(unit).strip() if unit else "",
                            "reference": str(reference).strip() if reference else "",
                            "is_numeric": True
                        })
                    except:
                        results.append({
                            "test": str(test).strip(),
                            "value": str(value).strip(),
                            "unit": str(unit).strip() if unit else "",
                            "reference": str(reference).strip() if reference else "",
                            "is_numeric": False
                        })
    return results

def check_abnormal(test, value, reference):
    if str(reference).lower() == "absent":
        return "ABNORMAL ⚠️" if "present" in str(value).lower() else "NORMAL ✅"
    if " - " in str(reference):
        try:
            low, high = str(reference).split(" - ")
            val = float(str(value).strip())
            if val < float(low.strip()): return "LOW 🔻"
            elif val > float(high.strip()): return "HIGH 🔺"
            else: return "NORMAL ✅"
        except: return "NORMAL ✅"
    return "NORMAL ✅"

def calculate_risk(abnormal_list):
    total = sum(RISK_WEIGHTS.get(str(a.get("test", "")).lower(), 2) for a in abnormal_list)
    max_possible = sum(RISK_WEIGHTS.values())
    score = round((total / max_possible) * 100)
    level = "🟢 LOW RISK" if score <= 30 else "🟡 MODERATE RISK" if score <= 60 else "🔴 HIGH RISK"
    return score, level

def detect_patterns(report_data):
    patterns = []
    values = {str(item.get("test", "")).lower(): str(item.get("value", "")).lower() for item in report_data}
    if "present" in values.get("ketone bodies", ""):
        if "present" in values.get("sugar / glucose", ""): patterns.append("Possible Diabetic Ketoacidosis Risk 🔴")
        else: patterns.append("Possible Starvation or Low Carb State 🟡")
    if "present" in values.get("bilirubin", ""): patterns.append("Possible Liver or Bile Duct Issue 🟡")
    if "present" in values.get("nitrite", "") and "present" in values.get("leukocytes", ""):
        patterns.append("Possible Urinary Tract Infection 🔴")
    return patterns

def generate_explanation(abnormal_list, risk_score, risk_level, patterns, rag_model, rag_index, gender):
    context = []
    for item in abnormal_list:
        query_vec = rag_model.encode([f"{item.get('test', '')} in urine"]).astype('float32')
        D, I = rag_index.search(query_vec, 2)
        for idx in I[0]: context.append(medical_knowledge[idx])
    context = list(set(context))
    context_text = "\n".join([f"- {c}" for c in context])
    abnormal_text = "\n".join([f"- {a.get('test', '')}: {a.get('value', '')}" for a in abnormal_list])
    pattern_text = "\n".join([f"- {p}" for p in patterns]) if patterns else "None"

    prompt = f"""You are a friendly medical assistant explaining a lab report to a patient (gender: {gender}).

VERIFIED MEDICAL KNOWLEDGE:
{context_text}

ABNORMAL VALUES:
{abnormal_text}

RISK SCORE: {risk_score}/100 ({risk_level})
PATTERNS: {pattern_text}

Give a calm, simple, reassuring explanation. Never diagnose. Always recommend consulting a doctor."""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ============ STREAMLIT UI ============
st.set_page_config(page_title="Ultimate Lab Report Agent", page_icon="🏥", layout="wide")

st.title("🏥 Ultimate Lab Report Intelligence Agent")
st.caption("Combining Medical Benchmarks + AI-Powered RAG + Groq")
st.warning("⚠️ This is not a medical diagnosis. Always consult a doctor.")

col1, col2 = st.columns([1, 3])

with col1:
    st.image("https://img.icons8.com/color/96/000000/medical-doctor.png")
    st.header("Patient Info")
    gender = st.selectbox("Gender", ["male", "female"])
    uploaded_file = st.file_uploader("Upload Lab Report PDF", type=["pdf"])

with col2:
    if uploaded_file:
        with st.spinner("🔍 Analyzing with BOTH backends..."):
            rag_model, rag_index = load_rag()
            report_data = parse_lab_report(uploaded_file)
            
            # BACKEND ANALYSIS (Medical Benchmarks)
            analyzer = HealthAnalyzer()
            numeric_values = [{'test': i['test'], 'value': float(i['value']), 'unit': i.get('unit', '')} 
                             for i in report_data if i.get('is_numeric', False)]
            
            if numeric_values:
                backend_analysis = analyzer.analyze(numeric_values, gender)
                st.subheader("📊 Medical Benchmarks Analysis")
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Health Score", f"{backend_analysis['health_score']}/100")
                col_b.metric("Total Tests", len(backend_analysis['results']))
                col_c.metric("Abnormal", backend_analysis['alert_count'])
                
                for r in backend_analysis['results']:
                    if r['status'] == 'normal':
                        st.success(f"✅ {r['test']}: {r['value']} {r['unit']}")
                    else:
                        st.error(f"⚠️ {r['test']}: {r['value']} {r['unit']} - {r['message']}")
            
            # FRONTEND ANALYSIS (RAG + AI)
            st.subheader("🧪 AI-Powered RAG Analysis")
            abnormal_list = [item for item in report_data 
                           if "NORMAL" not in check_abnormal(item["test"], item["value"], item.get("reference", ""))]
            
            if abnormal_list:
                risk_score, risk_level = calculate_risk(abnormal_list)
                patterns = detect_patterns(report_data)
                
                col_d, col_e = st.columns(2)
                col_d.metric("Risk Score", f"{risk_score}/100")
                col_e.metric("Risk Level", risk_level)
                
                if patterns:
                    st.subheader("🔍 Detected Patterns")
                    for p in patterns:
                        st.warning(p)
                
                explanation = generate_explanation(abnormal_list, risk_score, risk_level, 
                                                 patterns, rag_model, rag_index, gender)
                st.subheader("🤖 AI Explanation")
                st.info(explanation)
            else:
                st.success("✅ No abnormal values detected!")
            
            # All results
            with st.expander("📋 View All Test Results"):
                for item in report_data:
                    status = check_abnormal(item["test"], item["value"], item.get("reference", ""))
                    if "NORMAL" not in status:
                        st.write(f"⚠️ **{item['test']}**: {item['value']} {item.get('unit', '')} | Ref: {item.get('reference', '')}")
                    else:
                        st.write(f"✅ **{item['test']}**: {item['value']} {item.get('unit', '')}")
        
        st.success("✅ Analysis Complete!")
    else:
        st.info("👈 Please upload a PDF to begin")

st.markdown("---")
st.caption("⚕️ For informational purposes only. Consult your doctor.")