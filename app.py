import os

import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory, get_flashed_messages
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from functools import wraps
from helpers import calculate_age, get_suggestions, login_required


app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)



@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
@login_required
def index():
         conn = sqlite3.connect('health-tracker.db')
         cur = conn.cursor()

         cur.execute('''SELECT year, month, day, time, bpm, sys, dia, weight FROM records WHERE user_id = ? 
                     ORDER BY year DESC, month DESC, day DESC, time DESC''', (session["user_id"],))
        
         rows = cur.fetchall()

         cur.execute('''SELECT dob_year, dob_month, dob_day FROM users WHERE id = ?''', (session["user_id"],))
         dob = cur.fetchone()
         
         dob_year = dob[0]
         dob_month = dob[1]
         dob_day = dob[2]
    
         cur.close()
         conn.close()

         age = calculate_age(dob_year, dob_month, dob_day)
         suggestions = get_suggestions(age)
    
         return render_template("index.html", rows=rows, suggestions=suggestions)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must enter username", 'error')
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must enter password", 'error')
            return render_template("login.html")

        # Query database for username
        conn = sqlite3.connect('health-tracker.db')
        cur = conn.cursor()

        cur.execute("SELECT id, hash FROM users WHERE username = ?", (request.form.get("username"),))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0][1], request.form.get("password")
        ):
            flash("Invalid username and/or password", 'error')
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            flash("Must enter username", 'error')
            return render_template("register.html")
        
        elif not request.form.get("password"):
            flash("Must enter password", 'error')
            return render_template("register.html")
        
        new_username = request.form.get("username")
        new_password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        dob = request.form.get("dob")
        year = dob[0:4]
        month = dob[5:7]
        day = dob[8:10]
        print(f"Username: {new_username}")
        print(f"Password: {new_password}")
        print(f"Confirmation: {confirmation}")
        print(f"DOB: {dob}")
        print(f"Year: {year}, Month: {month}, Day: {day}")

        if new_password != confirmation:
            flash("Passwords must match", 'error')
            return render_template("register.html")
        
        conn = sqlite3.connect('health-tracker.db', autocommit=True)
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, hash, dob_year, dob_month, dob_day) VALUES (?, ?, ?, ?, ?)",
                       (new_username, generate_password_hash(new_password), int(year), int(month), int(day)))
        except sqlite3.IntegrityError:
            flash("username is taken/already in use", 'error')
            return render_template("register.html")
        cur.close()
        conn.close()
        flash("Successfully registered!", 'success')
        return render_template('login.html')

    
    else:
        return render_template("register.html")
    

@app.route("/enter", methods=["GET", "POST"])
def enter():
    if request.method == "POST":
         
         bpm = request.form.get("bpm")
         sys = (request.form.get("sys"))
         dia = (request.form.get("dia"))
         weight = (request.form.get("weight"))

         if not bpm and not sys and not dia and not weight:
             flash("At least one field must be filled", 'error')
             return render_template('enter.html')

         now = datetime.now()
    
         conn = sqlite3.connect('health-tracker.db', autocommit=True)
         cur = conn.cursor()

         cur.execute('''INSERT INTO records (bpm, sys, dia, weight, year, month, day, time, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (bpm, sys, dia, weight, now.year, now.month, now.day, now.strftime('%H:%M:%S'), session["user_id"]))
         
         cur.close()
         conn.close()

         flash("Successfully Logged Data!", 'success')
         return redirect("/")
    else:
        return render_template("enter.html")
