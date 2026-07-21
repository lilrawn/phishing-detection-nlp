#!/usr/bin/env python3
"""
Create PowerPoint presentation for Phishing Detection System
Run this script to generate the .pptx file
"""
import os
import sys

# Check if python-pptx is installed
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
except ImportError:
    print("Installing python-pptx...")
    os.system(f"{sys.executable} -m pip install python-pptx")
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor

def create_presentation():
    """Create the PowerPoint presentation"""
    
    # Create presentation
    prs = Presentation()
    
    # Set slide width and height (16:9)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # Define color scheme
    COLORS = {
        'primary': RGBColor(0, 85, 150),
        'secondary': RGBColor(200, 70, 50),
        'success': RGBColor(0, 150, 100),
        'warning': RGBColor(250, 150, 50),
        'danger': RGBColor(200, 50, 50),
        'dark': RGBColor(50, 50, 50),
        'light': RGBColor(240, 240, 240)
    }
    
    # ========== SLIDE 1: TITLE ==========
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    
    # Background
    background = slide.shapes.add_shape(
        1,  # Rectangle
        Inches(0), Inches(0),
        prs.slide_width, prs.slide_height
    )
    background.fill.solid()
    background.fill.fore_color.rgb = COLORS['primary']
    background.line.fill.background()
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11.333), Inches(1.5))
    title_frame = title_box.text_frame
    title_frame.text = "🛡️ PHISHING EMAIL"
    title_frame.paragraphs[0].font.size = Pt(54)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
    title_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    
    subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(3.5), Inches(11.333), Inches(1))
    subtitle_frame = subtitle_box.text_frame
    subtitle_frame.text = "DETECTION SYSTEM"
    subtitle_frame.paragraphs[0].font.size = Pt(54)
    subtitle_frame.paragraphs[0].font.bold = True
    subtitle_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
    subtitle_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    
    # Tagline
    tagline_box = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(11.333), Inches(0.8))
    tagline_frame = tagline_box.text_frame
    tagline_frame.text = "AI-Powered Detection Using NLP & ML"
    tagline_frame.paragraphs[0].font.size = Pt(24)
    tagline_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
    tagline_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    
    # Author
    author_box = slide.shapes.add_textbox(Inches(1), Inches(6.5), Inches(11.333), Inches(0.5))
    author_frame = author_box.text_frame
    author_frame.text = "Presented by: Liron Nyambu | Student No: 25ZAD110502"
    author_frame.paragraphs[0].font.size = Pt(14)
    author_frame.paragraphs[0].font.color.rgb = RGBColor(200, 200, 200)
    author_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    
    # ========== SLIDE 2: PROBLEM STATEMENT ==========
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    title_frame = title_box.text_frame
    title_frame.text = "📌 PROBLEM STATEMENT"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLORS['primary']
    
    # Content box
    content = [
        "🔴 PHISHING ATTACKS are the #1 cyber threat",
        "   • 90% of data breaches start with phishing",
        "   • Over 56,000 emails scanned - 58% were phishing",
        "",
        "❌ CURRENT SOLUTIONS ARE FAILING:",
        "   • Traditional filters - Bypassed by simple tricks",
        "   • Blacklists - Can't catch new attacks",
        "   • Rule-based systems - Miss clever social engineering",
        "",
        "💡 THE GAP: No system that combines:",
        "   • Real-time browser monitoring",
        "   • Advanced NLP analysis",
        "   • Sender reputation tracking",
        "   • User feedback integration"
    ]
    
    content_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(12.333), Inches(6))
    content_frame = content_box.text_frame
    content_frame.word_wrap = True
    
    for i, line in enumerate(content):
        if i == 0:
            p = content_frame.paragraphs[0]
        else:
            p = content_frame.add_paragraph()
        p.text = line
        p.font.size = Pt(20)
        if "🔴" in line or "❌" in line:
            p.font.bold = True
            p.font.color.rgb = COLORS['danger']
        elif "💡" in line:
            p.font.bold = True
            p.font.color.rgb = COLORS['success']
        else:
            p.font.color.rgb = COLORS['dark']
    
    # ========== SLIDE 3: OBJECTIVES ==========
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    title_frame = title_box.text_frame
    title_frame.text = "🎯 OBJECTIVES"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLORS['primary']
    
    # Main objective
    obj_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(12.333), Inches(1))
    obj_frame = obj_box.text_frame
    obj_frame.text = "MAIN OBJECTIVE:"
    obj_frame.paragraphs[0].font.size = Pt(22)
    obj_frame.paragraphs[0].font.bold = True
    obj_frame.paragraphs[0].font.color.rgb = COLORS['secondary']
    
    obj2_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.833), Inches(0.8))
    obj2_frame = obj2_box.text_frame
    obj2_frame.text = "Design and evaluate an AI-powered phishing detection system using Natural Language Processing (NLP)"
    obj2_frame.paragraphs[0].font.size = Pt(18)
    obj2_frame.paragraphs[0].font.color.rgb = COLORS['dark']
    
    # Specific objectives
    spec_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.8), Inches(12.333), Inches(0.6))
    spec_frame = spec_box.text_frame
    spec_frame.text = "SPECIFIC OBJECTIVES:"
    spec_frame.paragraphs[0].font.size = Pt(22)
    spec_frame.paragraphs[0].font.bold = True
    spec_frame.paragraphs[0].font.color.rgb = COLORS['secondary']
    
    objectives = [
        "1. 📁 Collect and preprocess phishing/legitimate email datasets",
        "2. 🔧 Apply NLP techniques (tokenization, lemmatization, TF-IDF)",
        "3. 🤖 Train and compare ML models (Naïve Bayes, Logistic Regression, SVM, Random Forest)",
        "4. 📊 Evaluate using accuracy, precision, recall, F1-score",
        "5. 🚀 Build real-time browser extension and dashboard"
    ]
    
    for i, obj in enumerate(objectives):
        y_pos = 3.4 + i * 0.5
        obj_box = slide.shapes.add_textbox(Inches(0.8), Inches(y_pos), Inches(11.833), Inches(0.5))
        obj_frame = obj_box.text_frame
        obj_frame.text = obj
        obj_frame.paragraphs[0].font.size = Pt(16)
        obj_frame.paragraphs[0].font.color.rgb = COLORS['dark']
    
    # ========== SLIDE 4: METHODOLOGY - ARCHITECTURE ==========
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    title_frame = title_box.text_frame
    title_frame.text = "🏗️ SYSTEM ARCHITECTURE"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLORS['primary']
    
    # Architecture diagram (text-based)
    arch_text = [
        "┌─────────────────────────────────────────────────────────────┐",
        "│                     BROWSER EXTENSION                      │",
        "│                     (Chrome/Brave)                         │",
        "└─────────────────────────────────────────────────────────────┘",
        "                              │",
        "                              ▼",
        "┌─────────────────────────────────────────────────────────────┐",
        "│                   DESKTOP APPLICATION                       │",
        "│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │",
        "│  │   HTTP      │  │  ML Model   │  │  Database   │        │",
        "│  │   Server    │──│  (spaCy +   │──│  (SQLite)   │        │",
        "│  │   Port 9877 │  │  scikit)    │  │             │        │",
        "│  └─────────────┘  └─────────────┘  └─────────────┘        │",
        "└─────────────────────────────────────────────────────────────┘",
        "                              │",
        "                              ▼",
        "┌─────────────────────────────────────────────────────────────┐",
        "│                      DASHBOARD (GUI)                        │",
        "│                   Real-time Statistics                      │",
        "└─────────────────────────────────────────────────────────────┘"
    ]
    
    arch_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(12.333), Inches(5))
    arch_frame = arch_box.text_frame
    arch_frame.word_wrap = True
    
    for i, line in enumerate(arch_text):
        if i == 0:
            p = arch_frame.paragraphs[0]
        else:
            p = arch_frame.add_paragraph()
        p.text = line
        p.font.size = Pt(12)
        p.font.name = "Courier New"
        p.font.color.rgb = COLORS['dark']
    
    # Data flow note
    flow_box = slide.shapes.add_textbox(Inches(0.5), Inches(6.2), Inches(12.333), Inches(0.5))
    flow_frame = flow_box.text_frame
    flow_frame.text = "📊 DATA FLOW: Email → Browser Extension → ML Analysis → Database → Dashboard"
    flow_frame.paragraphs[0].font.size = Pt(14)
    flow_frame.paragraphs[0].font.bold = True
    flow_frame.paragraphs[0].font.color.rgb = COLORS['success']
    
    # ========== SLIDE 5: METHODOLOGY - ML PIPELINE ==========
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    title_frame = title_box.text_frame
    title_frame.text = "🤖 ML PIPELINE"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLORS['primary']
    
    pipeline_text = [
        "📧 RAW EMAIL",
        "    │",
        "    ▼",
        "┌─────────────────────────────────────────────────────────────┐",
        "│ STEP 1: PREPROCESSING                                      │",
        "│ • HTML removal • Tokenization • Lemmatization              │",
        "│ • Stop word removal • URL/email tokenization               │",
        "└─────────────────────────────────────────────────────────────┘",
        "    │",
        "    ▼",
        "┌─────────────────────────────────────────────────────────────┐",
        "│ STEP 2: FEATURE EXTRACTION                                 │",
        "│ • TF-IDF Vectorization (2000 features)                     │",
        "│ • Handcrafted features: URL count, urgent words, ALL CAPS  │",
        "└─────────────────────────────────────────────────────────────┘",
        "    │",
        "    ▼",
        "┌─────────────────────────────────────────────────────────────┐",
        "│ STEP 3: MULTI-STAGE CONFIDENCE SCORING                     │",
        "│ Stage 1: Rules (40%) • Urgent words, ALL CAPS              │",
        "│ Stage 2: ML Model (30%) • Trained on 56,649 emails         │",
        "│ Stage 3: Links (20%) • Typosquatting detection              │",
        "│ Stage 4: Sender (10%) • Domain verification                │",
        "└─────────────────────────────────────────────────────────────┘",
        "    │",
        "    ▼",
        "🔴 PHISHING / 🟢 LEGITIMATE / 🟡 SUSPICIOUS"
    ]
    
    pipeline_box = slide.shapes.add_textbox(Inches(0.3), Inches(1.2), Inches(12.733), Inches(5.8))
    pipeline_frame = pipeline_box.text_frame
    pipeline_frame.word_wrap = True
    
    for i, line in enumerate(pipeline_text):
        if i == 0:
            p = pipeline_frame.paragraphs[0]
        else:
            p = pipeline_frame.add_paragraph()
        p.text = line
        p.font.size = Pt(10)
        p.font.name = "Courier New"
        if "🔴" in line:
            p.font.color.rgb = COLORS['danger']
        elif "🟢" in line:
            p.font.color.rgb = COLORS['success']
        elif "🟡" in line:
            p.font.color.rgb = COLORS['warning']
        else:
            p.font.color.rgb = COLORS['dark']
    
    # ========== SLIDE 6: RESULTS - MODEL PERFORMANCE ==========
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    title_frame = title_box.text_frame
    title_frame.text = "📊 MODEL PERFORMANCE"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLORS['primary']
    
    # Best model
    best_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.1), Inches(12.333), Inches(0.6))
    best_frame = best_box.text_frame
    best_frame.text = "🏆 BEST MODEL: Logistic Regression (C=10.0)"
    best_frame.paragraphs[0].font.size = Pt(22)
    best_frame.paragraphs[0].font.bold = True
    best_frame.paragraphs[0].font.color.rgb = COLORS['success']
    
    # Table header
    headers = ["Model", "Accuracy", "Precision", "Recall", "F1"]
    col_widths = [2.5, 1.8, 1.8, 1.8, 1.8]
    
    for i, header in enumerate(headers):
        x = 0.8 + sum(col_widths[:i])
        header_box = slide.shapes.add_textbox(Inches(x), Inches(1.8), Inches(col_widths[i]), Inches(0.5))
        header_frame = header_box.text_frame
        header_frame.text = header
        header_frame.paragraphs[0].font.size = Pt(16)
        header_frame.paragraphs[0].font.bold = True
        header_frame.paragraphs[0].font.color.rgb = COLORS['primary']
        header_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    
    # Table data
    data = [
        ["Naïve Bayes", "94.6%", "94.8%", "96.3%", "95.6%"],
        ["Logistic Regression", "97.8%", "98.1%", "97.8%", "97.9%"],
        ["SVM", "96.8%", "96.1%", "97.5%", "96.8%"],
        ["Random Forest", "95.1%", "94.3%", "96.0%", "95.2%"]
    ]
    
    for row_idx, row in enumerate(data):
        for col_idx, value in enumerate(row):
            x = 0.8 + sum(col_widths[:col_idx])
            y = 2.4 + row_idx * 0.5
            data_box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(col_widths[col_idx]), Inches(0.5))
            data_frame = data_box.text_frame
            data_frame.text = value
            data_frame.paragraphs[0].font.size = Pt(14)
            if row_idx == 1:  # Highlight best model
                data_frame.paragraphs[0].font.bold = True
                data_frame.paragraphs[0].font.color.rgb = COLORS['success']
            else:
                data_frame.paragraphs[0].font.color.rgb = COLORS['dark']
            data_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    
    # Confusion matrix
    cm_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.5), Inches(5), Inches(2))
    cm_frame = cm_box.text_frame
    cm_frame.text = "📈 CONFUSION MATRIX:\n\n               Predicted\n           Legit    Phish\nActual  Legit  4,632     115\n        Phish    131   6,452"
    cm_frame.paragraphs[0].font.size = Pt(14)
    cm_frame.paragraphs[0].font.bold = True
    cm_frame.paragraphs[0].font.color.rgb = COLORS['primary']
    
    # Metrics
    metrics_box = slide.shapes.add_textbox(Inches(7), Inches(4.5), Inches(5.5), Inches(2))
    metrics_frame = metrics_box.text_frame
    metrics_frame.text = "✅ ACCURACY: 97.83%\n✅ Only 2.17% error rate\n✅ 98.1% precision\n✅ 98.0% recall"
    metrics_frame.paragraphs[0].font.size = Pt(14)
    metrics_frame.paragraphs[0].font.color.rgb = COLORS['dark']
    
    # ========== SLIDE 7: KEY FEATURES ==========
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    title_frame = title_box.text_frame
    title_frame.text = "⚡ KEY FEATURES"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLORS['primary']
    
    features = [
        ("🌐 BROWSER EXTENSION", "Real-time Gmail monitoring, Auto-detects opened emails, Instant popup alerts (red/yellow/green)"),
        ("📊 DASHBOARD", "Live statistics, Color-coded email history, Activity log with timestamps, Sender reputation tracking"),
        ("🤖 ADVANCED ANALYSIS", "Multi-stage confidence scoring (0-100%), Link typosquatting detection, Grammar/spelling error detection"),
        ("💾 DATABASE", "SQLite storage (local, no cloud), Stores all scanned emails, User feedback tracking")
    ]
    
    y_start = 1.2
    for i, (title, desc) in enumerate(features):
        y = y_start + i * 1.3
        
        # Title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(y), Inches(5), Inches(0.5))
        title_frame = title_box.text_frame
        title_frame.text = title
        title_frame.paragraphs[0].font.size = Pt(18)
        title_frame.paragraphs[0].font.bold = True
        title_frame.paragraphs[0].font.color.rgb = COLORS['secondary']
        
        # Description
        desc_box = slide.shapes.add_textbox(Inches(0.8), Inches(y + 0.4), Inches(11.5), Inches(0.8))
        desc_frame = desc_box.text_frame
        desc_frame.word_wrap = True
        desc_frame.text = desc
        desc_frame.paragraphs[0].font.size = Pt(12)
        desc_frame.paragraphs[0].font.color.rgb = COLORS['dark']
    
    # ========== SLIDE 8: RESULTS - DETECTION EXAMPLES ==========
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    title_frame = title_box.text_frame
    title_frame.text = "🔍 REAL-WORLD DETECTION"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLORS['primary']
    
    # Legitimate emails
    legit_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(5.5), Inches(0.5))
    legit_frame = legit_box.text_frame
    legit_frame.text = "📧 LEGITIMATE EMAILS"
    legit_frame.paragraphs[0].font.size = Pt(20)
    legit_frame.paragraphs[0].font.bold = True
    legit_frame.paragraphs[0].font.color.rgb = COLORS['success']
    
    legit_examples = [
        "Amazon Shipping: 17.9% 🟢 LEGITIMATE",
        "Netflix Statement: 22.0% 🟢 LEGITIMATE",
        "Team Meeting: 22.1% 🟢 LEGITIMATE"
    ]
    
    for i, example in enumerate(legit_examples):
        y = 1.8 + i * 0.5
        ex_box = slide.shapes.add_textbox(Inches(0.8), Inches(y), Inches(5), Inches(0.5))
        ex_frame = ex_box.text_frame
        ex_frame.text = example
        ex_frame.paragraphs[0].font.size = Pt(14)
        ex_frame.paragraphs[0].font.color.rgb = COLORS['success']
    
    # Phishing emails
    phish_box = slide.shapes.add_textbox(Inches(6.5), Inches(1.2), Inches(5.5), Inches(0.5))
    phish_frame = phish_box.text_frame
    phish_frame.text = "📧 PHISHING EMAILS"
    phish_frame.paragraphs[0].font.size = Pt(20)
    phish_frame.paragraphs[0].font.bold = True
    phish_frame.paragraphs[0].font.color.rgb = COLORS['danger']
    
    phish_examples = [
        "PayPal 'Account Limited': 66.0% 🔴 PHISHING",
        "Apple 'ID Verification': 59.0% 🔴 PHISHING",
        "IRS 'Tax Refund': 65.0% 🔴 PHISHING"
    ]
    
    for i, example in enumerate(phish_examples):
        y = 1.8 + i * 0.5
        ex_box = slide.shapes.add_textbox(Inches(6.8), Inches(y), Inches(5), Inches(0.5))
        ex_frame = ex_box.text_frame
        ex_frame.text = example
        ex_frame.paragraphs[0].font.size = Pt(14)
        ex_frame.paragraphs[0].font.color.rgb = COLORS['danger']
    
    # Detection reasons
    reasons_box = slide.shapes.add_textbox(Inches(0.5), Inches(3.5), Inches(12.333), Inches(0.5))
    reasons_frame = reasons_box.text_frame
    reasons_frame.text = "🎯 DETECTION REASONS (PayPal Example):"
    reasons_frame.paragraphs[0].font.size = Pt(16)
    reasons_frame.paragraphs[0].font.bold = True
    reasons_frame.paragraphs[0].font.color.rgb = COLORS['secondary']
    
    reasons_text = [
        "   • Suspicious sender: paypal-security.com",
        "   • Typosquatting link: paypal-verify.com",
        "   • Urgent words: 'URGENT', 'limited', 'verify'",
        "   • ML confidence: 100%"
    ]
    
    for i, reason in enumerate(reasons_text):
        y = 4.0 + i * 0.4
        r_box = slide.shapes.add_textbox(Inches(0.8), Inches(y), Inches(11.5), Inches(0.4))
        r_frame = r_box.text_frame
        r_frame.text = reason
        r_frame.paragraphs[0].font.size = Pt(12)
        r_frame.paragraphs[0].font.color.rgb = COLORS['dark']
    
    # ========== SLIDE 9: CONCLUSION ==========
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    title_frame = title_box.text_frame
    title_frame.text = "✅ CONCLUSION"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLORS['primary']
    
    # Objectives achieved
    obj_achieved = [
        "✓ Collected & preprocessed 56,649 emails",
        "✓ Applied NLP techniques successfully",
        "✓ Trained 4 ML models with 97.83% accuracy",
        "✓ Built real-time browser extension",
        "✓ Created interactive dashboard"
    ]
    
    for i, obj in enumerate(obj_achieved):
        y = 1.2 + i * 0.5
        obj_box = slide.shapes.add_textbox(Inches(0.5), Inches(y), Inches(6), Inches(0.5))
        obj_frame = obj_box.text_frame
        obj_frame.text = obj
        obj_frame.paragraphs[0].font.size = Pt(14)
        obj_frame.paragraphs[0].font.color.rgb = COLORS['dark']
    
    # Key achievements
    achievements = [
        "🏆 98% detection accuracy",
        "🚀 Real-time browser monitoring",
        "📊 Multi-stage confidence scoring",
        "💻 Cross-platform support",
        "🔄 Complete user feedback system"
    ]
    
    for i, ach in enumerate(achievements):
        y = 1.2 + i * 0.5
        ach_box = slide.shapes.add_textbox(Inches(6.5), Inches(y), Inches(6), Inches(0.5))
        ach_frame = ach_box.text_frame
        ach_frame.text = ach
        ach_frame.paragraphs[0].font.size = Pt(14)
        ach_frame.paragraphs[0].font.color.rgb = COLORS['success']
    
    # Impact
    impact_box = slide.shapes.add_textbox(Inches(0.5), Inches(4), Inches(12.333), Inches(0.5))
    impact_frame = impact_box.text_frame
    impact_frame.text = "📈 IMPACT:"
    impact_frame.paragraphs[0].font.size = Pt(18)
    impact_frame.paragraphs[0].font.bold = True
    impact_frame.paragraphs[0].font.color.rgb = COLORS['secondary']
    
    impact_text = [
        "• Protects users from the #1 cyber threat",
        "• Catches evolving phishing techniques",
        "• Easy to use with familiar interface",
        "• Privacy-focused (all data stays local)"
    ]
    
    for i, impact in enumerate(impact_text):
        y = 4.5 + i * 0.4
        imp_box = slide.shapes.add_textbox(Inches(0.8), Inches(y), Inches(11.5), Inches(0.4))
        imp_frame = imp_box.text_frame
        imp_frame.text = impact
        imp_frame.paragraphs[0].font.size = Pt(12)
        imp_frame.paragraphs[0].font.color.rgb = COLORS['dark']
    
    # ========== SLIDE 10: FUTURE WORK ==========
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    title_frame = title_box.text_frame
    title_frame.text = "🚀 FUTURE WORK"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = COLORS['primary']
    
    future_items = [
        "1. 🤖 DEEP LEARNING INTEGRATION - Implement BERT/Transformer models",
        "2. 📧 MULTI-PLATFORM SUPPORT - Outlook, Yahoo Mail integration",
        "3. ☁️ CLOUD SYNC (Optional) - Encrypted backup of history",
        "4. 🏢 ENTERPRISE FEATURES - Team dashboards, centralized management",
        "5. 🔬 CONTINUOUS LEARNING - Automatic model retraining with user feedback",
        "6. 🌍 MORE LANGUAGES - Support for non-English phishing emails",
        "7. 🔗 ENHANCED URL REPUTATION - Real-time domain reputation checking"
    ]
    
    for i, item in enumerate(future_items):
        y = 1.2 + i * 0.55
        item_box = slide.shapes.add_textbox(Inches(0.5), Inches(y), Inches(12.333), Inches(0.55))
        item_frame = item_box.text_frame
        item_frame.word_wrap = True
        item_frame.text = item
        item_frame.paragraphs[0].font.size = Pt(14)
        if "1." in item or "2." in item or "3." in item:
            item_frame.paragraphs[0].font.bold = True
        item_frame.paragraphs[0].font.color.rgb = COLORS['dark']
    
    # Save presentation
    output_path = os.path.join(os.path.dirname(__file__), "Phishing_Detection_Presentation.pptx")
    prs.save(output_path)
    print(f"✅ Presentation saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    create_presentation()
