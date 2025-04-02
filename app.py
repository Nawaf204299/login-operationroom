
from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import numpy as np
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

ADMIN_USERNAME = 'operationroom'
ADMIN_PASSWORD = 'Aircargo123'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

suspicious_keywords = [
    'powder', 'capsule', 'tablet', 'herb', 'herbal', 'extract', 'leaf', 'tea',
    'khat', 'supplement', 'medicine', 'sample', 'personal use', 'personal goods',
    'organic matter', 'resin', 'seeds', 'incense', 'oil', 'natural', 'botanical'
]

def analyze_manifest(filepath):
    xls = pd.ExcelFile(filepath)
    df = xls.parse(xls.sheet_names[0])
    df['Description_clean'] = df['Description'].astype(str).str.lower()
    df['Suspicion_Score'] = df['Description_clean'].apply(
        lambda x: sum(kw in x for kw in suspicious_keywords)
    )
    df['Weight'] = pd.to_numeric(df['Weight'], errors='coerce').fillna(0)
    df['USD_Value'] = pd.to_numeric(df['USD_Value'], errors='coerce').fillna(0)
    df['Value_to_Weight'] = df.apply(
        lambda row: row['USD_Value'] / row['Weight'] if row['Weight'] > 0 else np.nan, axis=1
    )
    df['Low_Value_Heavy'] = df['Value_to_Weight'] < 10
    df['Suspicion_Score'] += df['Low_Value_Heavy'].astype(int)
    top_suspects = df.sort_values(by=['Suspicion_Score', 'Weight'], ascending=[False, False]).head(10)
    return top_suspects

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))

@app.route('/analyze', methods=['POST'])
def analyze():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if 'file' not in request.files:
        return "No file uploaded", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    try:
        results = analyze_manifest(filepath)
        return render_template('results.html', tables=[results.to_html(classes='data')], titles=results.columns.values)
    except Exception as e:
        return f"Error processing file: {e}", 500
