import os
import sqlite3
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory, get_flashed_messages
from flask_session import Session
from functools import wraps

def calculate_age(dob_year, dob_month, dob_day):
    today = datetime.today()
    age = today.year - dob_year
    if today.month < dob_month:
        age -= 1
    elif today.month == dob_month:
        if today.day < dob_day:
            age -=1
    return age

def get_suggestions(age):
    bpm_recs = {
        "verylow":"Very Low BPM: Consult a doctor if you experience dizziness, fatigue, or fainting",
        "low":"Low BPM: Stay Hydrated, Get enough rest",
        "high":"High BPM: Try meditation or stress-reducing activies, Reduce caffeine",
        "veryhigh":"Very High BPM: Consult a doctor if consistently this high or you experience chest pain or shortness of breath"
        }
    sys_recs = {
        "verylow":"Very Low SYS: Consult a doctor if you experience dizziness, blurred vision, or fainting",
        "low":"Low SYS: Drink more fluids, Eat a balanced diet",
        "high":"High SYS: Reduce salt intake, exercise regularly",
        "veryhigh":" Very High SYS: Consult a doctor if consistently this high or you experience severe headache or chest pain"
        }
    dia_recs = {
        "verylow":"Very Low DIA: Consult a doctor if you experience fatigue, lightheadedness, or fainting",
        "low":"Low DIA: Increase fluid intake and salt intake (slightly), Avoid prolonged standing",
        "high":"High DIA: Reduce salt intake, exercise regularly, reduce stress",
        "veryhigh":"Very High DIA: Consult a doctor if consistently this high or you experience headache or shortness of breath"
        }

    conn = sqlite3.connect('health-tracker.db')
    cur = conn.cursor()

    cur.execute('''SELECT bpm, sys, dia FROM records WHERE user_id = ? 
                ORDER BY year DESC, month DESC, day DESC, time DESC LIMIT 1''', (session["user_id"],))
        
    rows = cur.fetchall()
    if not rows:
        return []
    recent_bpm = rows[0][0]
    recent_sys = rows[0][1]
    recent_dia = rows[0][2]

    suggestions = []

    # Children (0-12 years)
    if age < 13:
        if recent_bpm:
            if recent_bpm > 160:
                suggestions.append(bpm_recs["veryhigh"])
            elif recent_bpm > 130:
                suggestions.append(bpm_recs["high"])
            elif recent_bpm < 40: 
                suggestions.append(bpm_recs["verylow"])
            elif recent_bpm < 60:
                suggestions.append(bpm_recs["low"])

             
        if recent_sys:
            if recent_sys > 140:
                suggestions.append(sys_recs["veryhigh"])
            elif recent_sys > 120:
                suggestions.append(sys_recs["high"])
            elif recent_sys < 70:
                suggestions.append(sys_recs["verylow"])
            elif recent_sys < 90:
                suggestions.append(sys_recs["low"])


        if recent_dia:
            if recent_dia > 100:
                suggestions.append(dia_recs["veryhigh"])
            elif recent_dia > 80:
                suggestions.append(dia_recs["high"])
            elif recent_dia < 40:
                suggestions.append(dia_recs["verylow"])
            elif recent_dia < 50:
                suggestions.append(dia_recs["low"])
    
    # Adolescents (13-18 years)
    if 13 <= age <= 18:
        if recent_bpm:
            if recent_bpm > 140:
                suggestions.append(bpm_recs["veryhigh"])
            elif recent_bpm > 110:
                suggestions.append(bpm_recs["high"])
            elif recent_bpm < 40:
                suggestions.append(bpm_recs["verylow"])
            elif recent_bpm < 60:
                suggestions.append(bpm_recs["low"])
            
        if recent_sys:
            if recent_sys > 140:
                suggestions.append(sys_recs["veryhigh"])
            elif recent_sys > 130:
                suggestions.append(sys_recs["high"])
            elif recent_sys < 80:
                suggestions.append(sys_recs["verylow"])
            elif recent_sys < 90:
                suggestions.append(sys_recs["low"])
            
        if recent_dia:
            if recent_dia > 100:
                suggestions.append(dia_recs["veryhigh"])
            elif recent_dia > 90:
                suggestions.append(dia_recs["high"])
            elif recent_dia < 50:
                suggestions.append(dia_recs["verylow"])
            elif recent_dia < 60:
                suggestions.append(dia_recs["low"])

    # Adults (19-64 years)
    if 19 <= age <= 64:
        if recent_bpm:
            if recent_bpm > 120:
                suggestions.append(bpm_recs["veryhigh"])
            elif recent_bpm > 100:
                suggestions.append(bpm_recs["high"])
            elif recent_bpm < 50:
                suggestions.append(bpm_recs["verylow"])
            elif recent_bpm < 60:
                suggestions.append(bpm_recs["low"])
            
        if recent_sys:
            if recent_sys > 180:
                suggestions.append(sys_recs["veryhigh"])
            elif recent_sys > 140:
                suggestions.append(sys_recs["high"])
            elif recent_sys < 70:
                suggestions.append(sys_recs["verylow"])
            elif recent_sys < 90:
                suggestions.append(sys_recs["low"])

            
        if recent_dia:
            if recent_dia > 110:
                suggestions.append(dia_recs["veryhigh"])
            elif recent_dia > 90:
                suggestions.append(dia_recs["high"])
            elif recent_dia < 50:
                suggestions.append(dia_recs["verylow"])
            elif recent_dia < 60:
                suggestions.append(dia_recs["low"])

    # Seniors (65+ years)
    if age >= 65:
        if recent_bpm:
            if recent_bpm > 120:
                suggestions.append(bpm_recs["veryhigh"])
            elif recent_bpm > 100:
                suggestions.append(bpm_recs["high"])
            elif recent_bpm < 50:
                suggestions.append(bpm_recs["verylow"])
            elif recent_bpm < 60:
                suggestions.append(bpm_recs["low"])
            
        if recent_sys:
            if recent_sys > 180:
                suggestions.append(sys_recs["veryhigh"])
            elif recent_sys > 150:
                suggestions.append(sys_recs["high"])
            elif recent_sys < 70:
                suggestions.append(sys_recs["verylow"])
            elif recent_sys < 90:
                suggestions.append(sys_recs["low"])
            
        if recent_dia:
            if recent_dia > 110:
                suggestions.append(dia_recs["veryhigh"])
            elif recent_dia > 100:
                suggestions.append(dia_recs["high"])
            elif recent_dia < 50:
                suggestions.append(dia_recs["verylow"])
            elif recent_dia < 60:
                suggestions.append(dia_recs["low"])
    return suggestions

def login_required(f):  
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function