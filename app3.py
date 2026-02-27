import streamlit as st
import pdfplumber
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import base64
from datetime import datetime
import json
from fpdf import FPDF
import io

# ============ PAGE CONFIG ============
st.set_page_config(page_title="Ultimate Lab Report Agent", page_icon="🏥", layout="wide")

# ============ FEATURE 5: BEAUTIFUL CSS ============
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Poppins', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        animation: fadeIn 1s ease-in;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    .main-header h1 {
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.95;
    }
    
    .health-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        transition: transform 0.3s;
        text-align: center;
        margin: 1rem 0;
    }
    
    .health-card:hover {
        transform: translateY(-5px);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 5px solid #667eea;
        animation: slideIn 0.5s ease;
        transition: all 0.3s;
    }
    
    .metric-card:hover {
        box-shadow: 0 8px 30px rgba(102, 126, 234, 0.2);
    }
    
    .abnormal-item {
        background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin: 0.8rem 0;
        border-left: 6px solid #f56565;
        box-shadow: 0 2px 10px rgba(245, 101, 101, 0.1);
        animation: slideIn 0.3s ease;
    }
    
    .normal-item {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin: 0.8rem 0;
        border-left: 6px solid #48bb78;
        box-shadow: 0 2px 10px rgba(72, 187, 120, 0.1);
        animation: slideIn 0.3s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .pulse {
        animation: pulse 2s infinite;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s;
        width: 100%;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    .stSelectbox {
        border-radius: 10px;
    }
    
    .success-box {
        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 600;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 600;
    }
    
    .info-card {
        background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
    }
    
    .download-btn {
        background: linear-gradient(135deg, #9f7aea 0%, #805ad5 100%);
        color: white;
        padding: 0.75rem 2rem;
        border-radius: 10px;
        text-decoration: none;
        display: inline-block;
        margin: 1rem 0;
        transition: all 0.3s;
    }
    
    .download-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 20px rgba(159, 122, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

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

# ============ FEATURE 1: ADVANCED PDF PARSER ============
def advanced_parse_lab_report(pdf_file):
    """Parse PDF using multiple methods for better extraction"""
    results = []
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                # Method 1: Extract tables
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        for row in table:
                            if row and len(row) >= 2:
                                test = str(row[0]) if row[0] else ""
                                value = str(row[1]) if len(row) > 1 and row[1] else ""
                                unit = str(row[2]) if len(row) > 2 and row[2] else ""
                                reference = str(row[3]) if len(row) > 3 and row[3] else ""
                                
                                if test and value and len(test.strip()) > 1:
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
                
                # Method 2: Extract text with regex patterns
                text = page.extract_text()
                if text:
                    # Common patterns in lab reports
                    patterns = [
                        r'(Glucose|Hemoglobin|Cholesterol|HDL|LDL|Triglycerides|Creatinine|ALT|AST|BUN)\s*:?\s*(\d+\.?\d*)\s*(mg/dL|g/dL|U/L)',
                        r'(Glucose|Hemoglobin|Cholesterol|HDL|LDL|Triglycerides|Creatinine|ALT|AST|BUN)\s+(\d+\.?\d*)\s+(mg/dL|g/dL|U/L)'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        for match in matches:
                            if len(match) >= 3:
                                try:
                                    val_float = float(match[1])
                                    results.append({
                                        "test": match[0].strip(),
                                        "value": val_float,
                                        "unit": match[2].strip(),
                                        "reference": "",
                                        "is_numeric": True
                                    })
                                except:
                                    pass
    
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
    
    # Remove duplicates (keep first occurrence)
    unique_results = []
    seen_tests = set()
    for r in results:
        if r['test'] not in seen_tests:
            seen_tests.add(r['test'])
            unique_results.append(r)
    
    return unique_results

# ============ SKIP KEYWORDS ============
SKIP_KEYWORDS = [
    "patient", "referred", "reg", "collected", "reported",
    "urine routine", "physical examination", "chemical examination",
    "microscopic examination", "name", "age", "sex", "date", "doctor"
]

RISK_WEIGHTS = {
    "ketone bodies": 4, "bilirubin": 5, "sugar / glucose": 5,
    "protein / albumin": 4, "blood": 4, "leukocytes": 3,
    "nitrite": 3, "pus cells": 3, "r.b.c.": 3,
    "ph": 2, "specific gravity": 2,
}

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

# ============ FEATURE 2: 3D HEALTH DASHBOARD ============
def create_3d_health_dashboard(analysis_results):
    """Create interactive 3D visualization"""
    
    # Create gauge chart
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=analysis_results['health_score'],
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Health Score", 'font': {'size': 24}},
        delta={'reference': 50, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "rgba(102, 126, 234, 0.8)", 'thickness': 0.75},
            'bgcolor': 'white',
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 40], 'color': 'rgba(255, 99, 71, 0.3)'},
                {'range': [40, 70], 'color': 'rgba(255, 165, 0, 0.3)'},
                {'range': [70, 100], 'color': 'rgba(50, 205, 50, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': analysis_results['health_score']
            }
        }
    ))
    
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={'color': "darkblue", 'family': "Poppins"}
    )
    
    return fig

def create_radar_chart(analysis_results):
    """Create radar chart for different health metrics"""
    categories = []
    values = []
    
    for r in analysis_results['results'][:6]:  # Take first 6 for radar
        categories.append(r['test'])
        # Normalize values to 0-100 scale (simplified)
        if r['status'] == 'normal':
            values.append(80)
        elif r['status'] in ['low', 'high']:
            values.append(40)
        else:
            values.append(60)
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        marker=dict(color='rgba(102, 126, 234, 0.8)'),
        line=dict(color='rgba(102, 126, 234, 1)', width=2)
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        height=350,
        margin=dict(l=40, r=40, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)"
    )
    
    return fig

# ============ FEATURE 4: SMART RECOMMENDATIONS ENGINE ============
class SmartRecommendations:
    def __init__(self):
        self.recommendations_db = {
            "cholesterol": {
                "high": [
                    "🥑 Eat more avocados and nuts - they contain healthy fats",
                    "🐟 Include fatty fish like salmon twice a week",
                    "🏃 Walk 30 minutes daily to improve HDL",
                    "🚫 Avoid trans fats found in fried foods",
                    "🥗 Add soluble fiber from oats, barley, and legumes"
                ],
                "borderline": [
                    "🥗 Add more soluble fiber (oats, beans, apples)",
                    "🏋️ Start with 20-minute daily walks",
                    "🥩 Replace red meat with lean proteins like chicken or fish",
                    "🥑 Include healthy fats from olive oil and avocados"
                ]
            },
            "ldl": {
                "high": [
                    "🚫 Reduce saturated fats from red meat and full-fat dairy",
                    "🌰 Eat almonds and walnuts daily",
                    "🏃 Exercise for 30 minutes at least 5 times a week",
                    "🍎 Add apples, grapes, strawberries to your diet"
                ],
                "borderline": [
                    "🥗 Increase soluble fiber intake",
                    "🏋️ Start regular physical activity",
                    "🥑 Replace butter with olive oil"
                ]
            },
            "hdl": {
                "low": [
                    "🏃 Aerobic exercise like jogging, swimming, or cycling",
                    "🥑 Eat healthy fats from avocados, nuts, and olive oil",
                    "🐟 Consume fatty fish rich in omega-3",
                    "🚫 Quit smoking if applicable",
                    "🍷 Moderate alcohol consumption (if approved by doctor)"
                ]
            },
            "triglycerides": {
                "high": [
                    "🍚 Reduce sugar and refined carbohydrates",
                    "🚫 Limit alcohol consumption",
                    "🏃 Exercise regularly to burn excess calories",
                    "🐟 Eat fish high in omega-3 fatty acids",
                    "🥗 Choose whole grains over white flour"
                ],
                "borderline": [
                    "🍬 Cut back on sugar and sweets",
                    "🏋️ Increase physical activity",
                    "🍚 Choose whole grain carbs"
                ]
            },
            "glucose": {
                "high": [
                    "🍚 Choose whole grains over refined carbs",
                    "🚶 Walk for 15 minutes after meals",
                    "🥤 Avoid sugary drinks and fruit juices",
                    "🥗 Eat more non-starchy vegetables",
                    "⏰ Maintain regular meal times"
                ]
            },
            "alt": {
                "high": [
                    "🚫 Avoid alcohol completely",
                    "🥗 Reduce fatty and processed foods",
                    "💧 Stay well hydrated",
                    "🏃 Maintain healthy weight through exercise"
                ]
            },
            "ast": {
                "high": [
                    "🚫 Avoid alcohol completely",
                    "🥗 Reduce fatty and processed foods",
                    "💧 Stay well hydrated",
                    "🏃 Maintain healthy weight through exercise"
                ]
            },
            "creatinine": {
                "high": [
                    "💧 Drink more water (8-10 glasses daily)",
                    "🚫 Avoid excessive protein intake",
                    "🚫 Limit salt intake",
                    "🚫 Avoid NSAIDs like ibuprofen without doctor approval"
                ]
            }
        }
    
    def get_recommendations(self, abnormal_tests):
        recs = []
        for test in abnormal_tests:
            test_lower = test['test'].lower()
            status = test['status'].lower()
            
            # Check each key in recommendations_db
            for key in self.recommendations_db:
                if key in test_lower:
                    # Check if status matches
                    if status in self.recommendations_db[key]:
                        recs.extend(self.recommendations_db[key][status])
                    # Also check for generic 'high' if status contains 'high'
                    elif 'high' in status and 'high' in self.recommendations_db[key]:
                        recs.extend(self.recommendations_db[key]['high'])
                    elif 'borderline' in status and 'borderline' in self.recommendations_db[key]:
                        recs.extend(self.recommendations_db[key]['borderline'])
        
        # Remove duplicates and return top 5
        return list(dict.fromkeys(recs))[:5]

# ============ FEATURE 6: PDF REPORT GENERATOR ============
def create_pdf_report(analysis, patient_name, gender, date, all_results):
    """Generate downloadable PDF report"""
    pdf = FPDF()
    pdf.add_page()
    
    # Colors and styling
    pdf.set_fill_color(102, 126, 234)  # Purple
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 20)
    
    # Header
    pdf.cell(190, 20, "Lab Report Analysis", ln=1, align='C', fill=True)
    pdf.ln(10)
    
    # Patient info
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(50, 8, f"Patient: {patient_name}", ln=1)
    pdf.cell(50, 8, f"Gender: {gender}", ln=1)
    pdf.cell(50, 8, f"Date: {date}", ln=1)
    pdf.cell(50, 8, f"Health Score: {analysis['health_score']}/100", ln=1)
    pdf.ln(10)
    
    # Results
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 10, "Test Results:", ln=1, fill=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", '', 11)
    for r in analysis['results']:
        status_symbol = "✓" if r['status'] == 'normal' else "⚠"
        if r['status'] == 'normal':
            pdf.set_text_color(0, 128, 0)  # Green
        else:
            pdf.set_text_color(255, 0, 0)  # Red
        
        pdf.cell(190, 6, f"{status_symbol} {r['test']}: {r['value']} {r['unit']} - {r['message']}", ln=1)
    
    pdf.ln(10)
    
    # All raw results
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 8, "Complete Results:", ln=1)
    pdf.set_font("Arial", '', 10)
    for item in all_results:
        pdf.cell(190, 5, f"{item['test']}: {item['value']} {item.get('unit', '')}", ln=1)
    
    # Save PDF to bytes
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return pdf_bytes

def get_pdf_download_link(pdf_bytes, filename="lab_report.pdf"):
    """Create a download link for PDF"""
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}" class="download-btn">📥 Download PDF Report</a>'
    return href

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
        
        elif test == 'creatinine':
            plan['lifestyle'].append("• Drink more water (8-10 glasses daily)")
            plan['diet'].append("• Limit protein intake and salt")
    
    # Remove duplicates
    for key in plan:
        plan[key] = list(dict.fromkeys(plan[key]))
    
    return plan

# ============ MAIN UI ============
st.markdown("""
<div class="main-header">
    <h1>🏥 Ultimate Lab Report Intelligence Agent</h1>
    <p>Advanced AI-Powered Medical Analysis | 3D Visualization | Smart Recommendations</p>
</div>
""", unsafe_allow_html=True)

st.warning("⚠️ This is not a medical diagnosis. Always consult a doctor.")

# Initialize session state for patient name
if 'patient_name' not in st.session_state:
    st.session_state.patient_name = ""

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1rem;">
        <img src="https://img.icons8.com/color/96/000000/medical-doctor.png" width="100">
        <h2 style="color: #667eea; margin-top: 0.5rem;">Patient Portal</h2>
    </div>
    """, unsafe_allow_html=True)
    
    patient_name = st.text_input("👤 Patient Name", value=st.session_state.patient_name)
    st.session_state.patient_name = patient_name
    
    age = st.number_input("🎂 Age", min_value=0, max_value=120, value=30)
    gender = st.selectbox("⚥ Gender", ["male", "female"])
    
    st.markdown("---")
    st.markdown("### 📤 Upload Report")
    uploaded_file = st.file_uploader("Choose a lab report (PDF)", type=["pdf"])

# Main content
if uploaded_file:
    with st.spinner("🔍 Analyzing your report with advanced AI..."):
        # Parse PDF
        report_data = advanced_parse_lab_report(uploaded_file)
        
        # If no data found, use sample data for demo
        if not report_data:
            st.warning("⚠️ No data found in PDF. Using sample data for demonstration.")
            report_data = [
                {"test": "Glucose", "value": 95, "unit": "mg/dL", "reference": "70-99", "is_numeric": True},
                {"test": "Cholesterol", "value": 210, "unit": "mg/dL", "reference": "125-200", "is_numeric": True},
                {"test": "HDL", "value": 45, "unit": "mg/dL", "reference": "40-60", "is_numeric": True},
                {"test": "LDL", "value": 140, "unit": "mg/dL", "reference": "0-100", "is_numeric": True},
                {"test": "Triglycerides", "value": 180, "unit": "mg/dL", "reference": "0-149", "is_numeric": True},
                {"test": "Creatinine", "value": 1.1, "unit": "mg/dL", "reference": "0.7-1.3", "is_numeric": True},
                {"test": "ALT", "value": 30, "unit": "U/L", "reference": "7-55", "is_numeric": True},
                {"test": "AST", "value": 25, "unit": "U/L", "reference": "8-48", "is_numeric": True},
            ]
        
        # Initialize translator and analyzer
        translator = PlainEnglishTranslator()
        analyzer = HealthAnalyzer()
        
        # Get numeric values for backend analysis
        numeric_values = [{'test': i['test'], 'value': float(i['value']), 'unit': i.get('unit', '')} 
                         for i in report_data if i.get('is_numeric', False)]
        
        if numeric_values:
            backend_analysis = analyzer.analyze(numeric_values, gender, age)
            
            # Top row - Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style="color: #667eea; margin: 0;">{backend_analysis['health_score']}</h3>
                    <p style="margin: 0;">Health Score</p>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style="color: #667eea; margin: 0;">{len(backend_analysis['results'])}</h3>
                    <p style="margin: 0;">Total Tests</p>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style="color: #667eea; margin: 0;">{backend_analysis['alert_count']}</h3>
                    <p style="margin: 0;">Abnormal</p>
                </div>
                """, unsafe_allow_html=True)
            with col4:
                status_text = "Good" if backend_analysis['alert_count'] == 0 else "Needs Attention"
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style="color: #667eea; margin: 0;">{status_text}</h3>
                    <p style="margin: 0;">Status</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # FEATURE 2: 3D DASHBOARD
            st.markdown("## 📊 3D Health Dashboard")
            col_left, col_right = st.columns(2)
            
            with col_left:
                fig_gauge = create_3d_health_dashboard(backend_analysis)
                st.plotly_chart(fig_gauge, use_container_width=True)
            
            with col_right:
                fig_radar = create_radar_chart(backend_analysis)
                st.plotly_chart(fig_radar, use_container_width=True)
            
            st.markdown("---")
            
            # Medical Benchmarks Results
            st.markdown("## 📋 Medical Benchmarks Analysis")
            for r in backend_analysis['results']:
                if r['status'] == 'normal':
                    st.markdown(f"""
                    <div class="normal-item">
                        <strong>✅ {r['test']}:</strong> {r['value']} {r['unit']} 
                        <span style="float: right;">{r['message']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="abnormal-item">
                        <strong>⚠️ {r['test']}:</strong> {r['value']} {r['unit']} 
                        <span style="float: right; color: #f56565;">{r['message']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Plain English Explanations for abnormal values
            abnormal_results = [r for r in backend_analysis['results'] if r['status'] != 'normal']
            if abnormal_results:
                st.markdown("## 🗣️ What These Numbers Mean")
                for r in abnormal_results:
                    st.info(translator.translate(r['test'], r['status'], r['value']))
            
            # FEATURE 4: SMART RECOMMENDATIONS
            st.markdown("## 💡 Smart Recommendations")
            recommender = SmartRecommendations()
            recommendations = recommender.get_recommendations(abnormal_results)
            
            if recommendations:
                cols = st.columns(2)
                for i, rec in enumerate(recommendations):
                    with cols[i % 2]:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #e6f0fa 0%, #d4e4f7 100%); 
                                   padding: 1rem; border-radius: 10px; margin: 0.5rem 0;
                                   border-left: 5px solid #4299e1;">
                            {rec}
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.success("✅ No specific recommendations needed. Keep up the good work!")
            
            # Detailed Analysis
            st.markdown("---")
            st.markdown("## 🧪 Detailed Lab Analysis")
            
            abnormal_list = []
            for item in report_data:
                status = check_abnormal(item["test"], item["value"], item.get("reference", ""))
                if "NORMAL" not in status:
                    abnormal_list.append(item)
            
            if abnormal_list:
                risk_score, risk_level = calculate_risk(abnormal_list)
                patterns = detect_patterns(report_data)
                
                col_risk1, col_risk2 = st.columns(2)
                with col_risk1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h2 style="color: #667eea;">{risk_score}</h2>
                        <p>Risk Score</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col_risk2:
                    color = "#48bb78" if "LOW" in risk_level else "#ed8936" if "MODERATE" in risk_level else "#f56565"
                    st.markdown(f"""
                    <div style="background: {color}; padding: 1.5rem; border-radius: 15px; text-align: center;">
                        <h3 style="color: white; margin: 0;">{risk_level}</h3>
                    </div>
                    """, unsafe_allow_html=True)
                
                if patterns:
                    st.markdown("### 🔍 Detected Patterns")
                    for p in patterns:
                        st.warning(p)
                
                # Action Plan
                action_plan = generate_action_plan(abnormal_list)
                if any(action_plan.values()):
                    st.markdown("### ✅ Your Personal Action Plan")
                    
                    if action_plan['diet']:
                        with st.expander("🥗 Diet Changes", expanded=True):
                            for item in action_plan['diet']:
                                st.write(item)
                    
                    if action_plan['exercise']:
                        with st.expander("🏃 Exercise Tips", expanded=True):
                            for item in action_plan['exercise']:
                                st.write(item)
                    
                    if action_plan['lifestyle']:
                        with st.expander("🌿 Lifestyle Changes", expanded=True):
                            for item in action_plan['lifestyle']:
                                st.write(item)
                    
                    if action_plan['doctor']:
                        with st.expander("👨‍⚕️ When to See Doctor", expanded=True):
                            for item in action_plan['doctor']:
                                st.write(item)
            else:
                st.success("✅ No abnormal values detected in detailed analysis!")
            
            # All results expander
            with st.expander("📋 View All Raw Test Results"):
                for item in report_data:
                    status = check_abnormal(item["test"], item["value"], item.get("reference", ""))
                    st.write(f"**{item['test']}**: {item['value']} {item.get('unit', '')} | Ref: {item.get('reference', '')} | {status}")
            
            # FEATURE 6: PDF EXPORT
            st.markdown("---")
            st.markdown("## 📥 Export Report")
            
            if patient_name:
                # Generate PDF
                pdf_bytes = create_pdf_report(
                    backend_analysis, 
                    patient_name, 
                    gender, 
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    report_data
                )
                
                # Create download link
                download_link = get_pdf_download_link(pdf_bytes, f"{patient_name}_lab_report.pdf")
                st.markdown(download_link, unsafe_allow_html=True)
                st.info("💾 Click the button above to download your complete health report")
            else:
                st.info("👤 Enter patient name in the sidebar to enable PDF export")
    
    st.success("✅ Analysis Complete!")
else:
    # Welcome screen
    col_welcome1, col_welcome2, col_welcome3 = st.columns(3)
    
    with col_welcome1:
        st.markdown("""
        <div class="info-card">
            <h3>📊 3D Analytics</h3>
            <p>Interactive 3D visualizations of your health metrics</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_welcome2:
        st.markdown("""
        <div class="info-card" style="background: linear-gradient(135deg, #9f7aea 0%, #805ad5 100%);">
            <h3>🤖 Smart AI</h3>
            <p>Intelligent pattern detection and recommendations</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_welcome3:
        st.markdown("""
        <div class="info-card" style="background: linear-gradient(135deg, #f687b3 0%, #ed64a6 100%);">
            <h3>📱 PDF Export</h3>
            <p>Download comprehensive reports to share with doctors</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; padding: 3rem;">
        <h2 style="color: #667eea;">🚀 Upload a Lab Report to Begin</h2>
        <p style="color: #718096;">Supports PDF format • Advanced parsing • Instant results</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption("⚕️ For informational purposes only. Consult your doctor for medical advice.")