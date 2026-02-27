import streamlit as st
import pdfplumber
import re
import numpy as np

# ============ PAGE CONFIG ============
st.set_page_config(page_title="Ultimate Lab Report Agent", page_icon="🏥", layout="wide")

# ============ BACKEND CLASSES (Medical Benchmarks) ============
class MedicalBenchmarks:
    def __init__(self):
        self.ranges = {
            "Glucose": {"normal": (70, 99), "prediabetes": (100, 125), "diabetes": (126, 999), "unit": "mg/dL"},
            "Hemoglobin": {"normal_male": (13.5, 17.5), "normal_female": (12.0, 15.5), "unit": "g/dL"},
            "Cholesterol": {"normal": (125, 200), "borderline": (200, 239), "high": (240, 999), "unit": "mg/dL"},
            "HDL": {"normal_male": (40, 60), "normal_female": (50, 60), "unit": "mg/dL"},
            "LDL": {"optimal": (0, 100), "borderline": (130, 159), "high": (160, 999), "unit": "mg/dL"},
            "Triglycerides": {"normal": (0, 149), "borderline": (150, 199), "high": (200, 999), "unit": "mg/dL"},
            "Creatinine": {"normal_male": (0.7, 1.3), "normal_female": (0.6, 1.1), "unit": "mg/dL"},
            "ALT": {"normal_male": (7, 55), "normal_female": (7, 45), "unit": "U/L"},
            "AST": {"normal": (8, 48), "unit": "U/L"},
            "BUN": {"normal": (7, 20), "unit": "mg/dL"}
        }
    
    def compare(self, test_name, value, gender="male"):
        test_name = test_name.strip().title()
        if test_name not in self.ranges:
            return {"status": "unknown", "message": "No reference range found"}
        
        ref = self.ranges[test_name]
        
        if test_name == "Hemoglobin":
            key = f"normal_{gender}"
            if key in ref:
                min_val, max_val = ref[key]
                if value < min_val:
                    return {"status": "low", "message": f"Low ({min_val}-{max_val} {ref['unit']})"}
                elif value > max_val:
                    return {"status": "high", "message": f"High ({min_val}-{max_val} {ref['unit']})"}
                else:
                    return {"status": "normal", "message": "Normal"}
        
        if "normal" in ref:
            min_val, max_val = ref["normal"]
            if value < min_val:
                return {"status": "low", "message": f"Below normal ({min_val}-{max_val} {ref['unit']})"}
            elif value > max_val:
                for category, (cat_min, cat_max) in ref.items():
                    if category not in ["normal", "unit"] and cat_min <= value <= cat_max:
                        return {"status": "high", "message": f"{category}: {value} {ref['unit']}"}
                return {"status": "high", "message": f"Above normal ({min_val}-{max_val} {ref['unit']})"}
            else:
                return {"status": "normal", "message": "Normal"}
        
        return {"status": "unknown", "message": "Check manually"}

class HealthAnalyzer:
    def __init__(self):
        self.benchmarks = MedicalBenchmarks()
    
    def analyze(self, lab_values, gender="male", age=30):
        results = []
        alerts = []
        
        for test in lab_values:
            comparison = self.benchmarks.compare(test["test"], test["value"], gender)
            result = {
                "test": test["test"],
                "value": test["value"],
                "unit": test["unit"],
                "status": comparison["status"],
                "message": comparison["message"]
            }
            results.append(result)
            if comparison["status"] in ["low", "high"]:
                alerts.append(result)
        
        health_score = self._calculate_score(results)
        
        return {
            "results": results,
            "alerts": alerts,
            "health_score": health_score,
            "alert_count": len(alerts)
        }
    
    def _calculate_score(self, results):
        if not results:
            return 50
        score = 0
        for r in results:
            if r["status"] == "normal":
                score += 100
            elif r["status"] in ["low", "high"]:
                score += 40
            else:
                score += 70
        return round(score / len(results))
    
    def generate_summary(self, analysis):
        if analysis['alert_count'] == 0:
            return "✅ Great news! All values are normal!"
        else:
            return f"⚠️ Found {analysis['alert_count']} abnormal value(s)."

# ============ FRONTEND ANALYZER (No external AI) ============
SKIP_KEYWORDS = [
    "patient", "referred", "reg", "collected", "reported",
    "urine routine", "physical examination", "chemical examination",
    "microscopic examination"
]

RISK_WEIGHTS = {
    "ketone bodies": 4, "bilirubin": 5, "sugar / glucose": 5,
    "protein / albumin": 4, "blood": 4, "leukocytes": 3,
    "nitrite": 3, "pus cells": 3, "r.b.c.": 3,
    "ph": 2, "specific gravity": 2,
}

def parse_lab_report(pdf_file):
    results = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 2:
                            continue
                        
                        test = str(row[0]) if row[0] else ""
                        value = str(row[1]) if len(row) > 1 and row[1] else ""
                        unit = str(row[2]) if len(row) > 2 and row[2] else ""
                        reference = str(row[3]) if len(row) > 3 and row[3] else ""
                        
                        if not test or not value:
                            continue
                        if any(skip in test.lower() for skip in SKIP_KEYWORDS):
                            continue
                        
                        # Try to convert to numeric
                        try:
                            val_float = float(value.strip())
                            results.append({
                                "test": test.strip(),
                                "value": val_float,
                                "unit": unit.strip(),
                                "reference": reference.strip(),
                                "is_numeric": True
                            })
                        except:
                            results.append({
                                "test": test.strip(),
                                "value": value.strip(),
                                "unit": unit.strip(),
                                "reference": reference.strip(),
                                "is_numeric": False
                            })
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
    return results

def check_abnormal(test, value, reference):
    if reference.lower() == "absent":
        return "ABNORMAL ⚠️" if "present" in str(value).lower() else "NORMAL ✅"
    if " - " in reference:
        try:
            low, high = reference.split(" - ")
            val = float(str(value).strip())
            if val < float(low.strip()): return "LOW 🔻"
            elif val > float(high.strip()): return "HIGH 🔺"
            else: return "NORMAL ✅"
        except:
            return "NORMAL ✅"
    if reference.strip() and str(value).strip().lower() == reference.strip().lower():
        return "NORMAL ✅"
    return "NORMAL ✅"

def calculate_risk(abnormal_list):
    total = 0
    for item in abnormal_list:
        test_lower = str(item.get("test", "")).lower()
        weight = RISK_WEIGHTS.get(test_lower, 2)
        total += weight
    max_possible = sum(RISK_WEIGHTS.values())
    score = round((total / max_possible) * 100) if max_possible > 0 else 0
    level = "🟢 LOW RISK" if score <= 30 else "🟡 MODERATE RISK" if score <= 60 else "🔴 HIGH RISK"
    return score, level

def detect_patterns(report_data):
    patterns = []
    values = {}
    for item in report_data:
        test_lower = str(item.get("test", "")).lower()
        value_lower = str(item.get("value", "")).lower()
        values[test_lower] = value_lower
    
    if "present" in values.get("ketone bodies", ""):
        if "present" in values.get("sugar / glucose", ""):
            patterns.append("🔴 Possible Diabetic Ketoacidosis Risk")
        else:
            patterns.append("🟡 Possible Starvation or Low Carb State")
    if "present" in values.get("bilirubin", ""):
        patterns.append("🟡 Possible Liver or Bile Duct Issue")
    if "present" in values.get("nitrite", "") and "present" in values.get("leukocytes", ""):
        patterns.append("🔴 Possible Urinary Tract Infection")
    if "present" in values.get("protein / albumin", ""):
        patterns.append("🟡 Possible Kidney Stress")
    return patterns

# ============ PLAIN ENGLISH TRANSLATOR ============
class PlainEnglishTranslator:
    def __init__(self):
        self.translations = {
            "Glucose": {
                "name": "Blood Sugar",
                "simple": "Shows how much sugar is in your blood",
                "advice": {
                    "low": "You might feel shaky or tired. Eat something sweet.",
                    "high": "Cut down on sweets and sugary drinks.",
                    "normal": "Your body handles sugar well!"
                }
            },
            "Cholesterol": {
                "name": "Blood Fat",
                "simple": "Amount of fat in your blood that can clog arteries",
                "advice": {
                    "high": "Try to eat less fried food, red meat, and full-fat dairy.",
                    "borderline": "Watch your diet - less oil and more vegetables.",
                    "normal": "Your heart is happy!"
                }
            },
            "HDL": {
                "name": "Good Cholesterol",
                "simple": "The 'good' fat that protects your heart",
                "advice": {
                    "low": "Exercise more and eat healthy fats like nuts and fish.",
                    "normal": "Your good cholesterol is at a healthy level."
                }
            },
            "LDL": {
                "name": "Bad Cholesterol",
                "simple": "The 'bad' fat that can block your blood vessels",
                "advice": {
                    "high": "Reduce fatty foods, fast food, and processed snacks.",
                    "borderline": "Be careful with oily and fried foods.",
                    "normal": "Your arteries are clear!"
                }
            },
            "Triglycerides": {
                "name": "Blood Fats",
                "simple": "Another type of fat in your blood",
                "advice": {
                    "high": "Cut down on sugar, alcohol, and refined carbs.",
                    "borderline": "Reduce sweets and increase exercise.",
                    "normal": "Your fat levels are healthy."
                }
            },
            "Hemoglobin": {
                "name": "Iron Level",
                "simple": "Shows if you have enough iron in your blood",
                "advice": {
                    "low": "Eat more spinach, beans, and red meat.",
                    "high": "Stay hydrated and avoid smoking.",
                    "normal": "Your iron levels are good!"
                }
            },
            "Creatinine": {
                "name": "Kidney Function",
                "simple": "Shows how well your kidneys are cleaning your blood",
                "advice": {
                    "high": "Drink more water and avoid too much protein.",
                    "normal": "Your kidneys are working well!"
                }
            },
            "ALT": {
                "name": "Liver Health",
                "simple": "Shows if your liver is healthy",
                "advice": {
                    "high": "Avoid alcohol and fatty foods.",
                    "normal": "Your liver is healthy!"
                }
            },
            "AST": {
                "name": "Liver Health",
                "simple": "Shows if your liver is healthy",
                "advice": {
                    "high": "Avoid alcohol and fatty foods.",
                    "normal": "Your liver is healthy!"
                }
            }
        }
    
    def translate(self, test_name, status, value):
        test_name = test_name.strip().title()
        
        if test_name in self.translations:
            t = self.translations[test_name]
            simple_name = t['name']
            explanation = t['simple']
            
            advice = "No specific advice available."
            if status == "normal":
                advice = t['advice'].get('normal', "Keep up the good work!")
            elif status == "high" or "borderline" in status.lower():
                if 'high' in t['advice']:
                    advice = t['advice']['high']
                elif 'borderline' in t['advice']:
                    advice = t['advice']['borderline']
            elif status == "low":
                advice = t['advice'].get('low', "Consult your doctor about this.")
            
            return f"📌 **{simple_name}**: {value}\n   • What it means: {explanation}\n   • What to do: {advice}"
        else:
            return f"📌 **{test_name}**: {value} - Ask your doctor about this test."

# ============ HEALTH METER VISUALIZATION ============
def show_health_meter(health_score):
    if health_score >= 80:
        color = "#28a745"
        status = "EXCELLENT"
        message = "✅ Your health metrics are looking great!"
    elif health_score >= 60:
        color = "#ffc107"
        status = "GOOD"
        message = "⚠️ Most values are normal. Focus on the flagged items."
    elif health_score >= 40:
        color = "#fd7e14"
        status = "FAIR"
        message = "⚕️ Several values need attention. Consult your doctor."
    else:
        color = "#dc3545"
        status = "ATTENTION NEEDED"
        message = "🆘 Please consult a healthcare provider soon."
    
    st.markdown(f"""
    <div style="background-color: {color}; padding: 1.5rem; border-radius: 10px; text-align: center;">
        <h1 style="color: white; font-size: 3rem; margin: 0;">{health_score}</h1>
        <p style="color: white; font-size: 1.5rem; margin: 0;">{status}</p>
    </div>
    """, unsafe_allow_html=True)
    st.info(message)

# ============ ACTION PLAN GENERATOR ============
def generate_action_plan(alerts):
    plan = {
        "diet": [],
        "exercise": [],
        "lifestyle": [],
        "doctor": []
    }
    
    for alert in alerts:
        test = alert['test'].lower()
        
        if test in ['cholesterol', 'ldl', 'triglycerides']:
            plan['diet'].append("• Reduce fried foods, red meat, and full-fat dairy")
            plan['diet'].append("• Eat more oats, nuts, fruits, and vegetables")
            plan['exercise'].append("• Walk 30 minutes daily to improve cholesterol")
            plan['doctor'].append("• Discuss cholesterol medication if diet doesn't help")
        
        elif test == 'hdl':
            plan['diet'].append("• Eat healthy fats: avocados, nuts, olive oil")
            plan['exercise'].append("• Aerobic exercise like jogging or swimming")
        
        elif test == 'glucose':
            plan['diet'].append("• Reduce sugar, sweets, and refined carbs")
            plan['diet'].append("• Eat smaller, more frequent meals")
            plan['exercise'].append("• Exercise after meals to lower blood sugar")
        
        elif test in ['alt', 'ast']:
            plan['lifestyle'].append("• Avoid alcohol completely for 1 month")
            plan['diet'].append("• Reduce fatty and processed foods")
    
    # Remove duplicates
    for key in plan:
        plan[key] = list(dict.fromkeys(plan[key]))
    
    return plan

# ============ STREAMLIT UI ============
st.title("🏥 Ultimate Lab Report Intelligence Agent")
st.markdown("### Combining Medical Benchmarks + Plain English Explanations")
st.warning("⚠️ This is not a medical diagnosis. Always consult a doctor.")

col1, col2 = st.columns([1, 3])

with col1:
    st.image("https://img.icons8.com/color/96/000000/medical-doctor.png", width=100)
    st.header("Patient Info")
    gender = st.selectbox("Gender", ["male", "female"])
    uploaded_file = st.file_uploader("Upload Lab Report PDF", type=["pdf"])

with col2:
    if uploaded_file:
        with st.spinner("🔍 Analyzing your report..."):
            # Parse PDF
            report_data = parse_lab_report(uploaded_file)
            
            if not report_data:
                st.error("No lab data found in the PDF. Please check the file format.")
            else:
                # Initialize translator
                translator = PlainEnglishTranslator()
                
                # BACKEND ANALYSIS (Medical Benchmarks)
                analyzer = HealthAnalyzer()
                numeric_values = [{'test': i['test'], 'value': float(i['value']), 'unit': i.get('unit', '')} 
                                 for i in report_data if i.get('is_numeric', False)]
                
                if numeric_values:
                    backend_analysis = analyzer.analyze(numeric_values, gender)
                    
                    st.subheader("📊 Health Overview")
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Health Score", f"{backend_analysis['health_score']}/100")
                    col_b.metric("Total Tests", len(backend_analysis['results']))
                    col_c.metric("Abnormal", backend_analysis['alert_count'])
                    
                    # Health meter
                    show_health_meter(backend_analysis['health_score'])
                    
                    st.subheader("📋 Medical Benchmarks Results")
                    for r in backend_analysis['results']:
                        if r['status'] == 'normal':
                            st.success(f"✅ {r['test']}: {r['value']} {r['unit']}")
                        else:
                            st.error(f"⚠️ {r['test']}: {r['value']} {r['unit']} - {r['message']}")
                    
                    # Plain English translations
                    st.subheader("🗣️ What These Numbers Mean")
                    for r in backend_analysis['results']:
                        if r['status'] != 'normal':
                            st.info(translator.translate(r['test'], r['status'], r['value']))
                
                # FRONTEND ANALYSIS (RAG-style)
                st.subheader("🧪 Detailed Lab Analysis")
                abnormal_list = []
                for item in report_data:
                    status = check_abnormal(item["test"], item["value"], item.get("reference", ""))
                    if "NORMAL" not in status:
                        abnormal_list.append(item)
                
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
                    
                    # Action Plan
                    action_plan = generate_action_plan(abnormal_list)
                    if any(action_plan.values()):
                        st.subheader("✅ Your Personal Action Plan")
                        if action_plan['diet']:
                            st.markdown("**🥗 Diet Changes:**")
                            for item in action_plan['diet']:
                                st.write(item)
                        if action_plan['exercise']:
                            st.markdown("**🏃 Exercise Tips:**")
                            for item in action_plan['exercise']:
                                st.write(item)
                        if action_plan['lifestyle']:
                            st.markdown("**🌿 Lifestyle Changes:**")
                            for item in action_plan['lifestyle']:
                                st.write(item)
                        if action_plan['doctor']:
                            st.markdown("**👨‍⚕️ When to See Doctor:**")
                            for item in action_plan['doctor']:
                                st.write(item)
                else:
                    st.success("✅ No abnormal values detected!")
                
                # All results expander
                with st.expander("📋 View All Raw Test Results"):
                    for item in report_data:
                        status = check_abnormal(item["test"], item["value"], item.get("reference", ""))
                        st.write(f"**{item['test']}**: {item['value']} {item.get('unit', '')} | Ref: {item.get('reference', '')} | {status}")
        
        st.success("✅ Analysis Complete!")
    else:
        st.info("👈 Please upload a PDF to begin")

st.markdown("---")
st.caption("⚕️ For informational purposes only. Consult your doctor.")