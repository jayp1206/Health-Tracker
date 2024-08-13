import os

import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory, get_flashed_messages
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from functools import wraps
from helpers import calculate_age, get_suggestions, login_required, healthy, zip_filter


app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.jinja_env.filters['zip'] = zip_filter

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
    session["shared_view_id"] = None
    session["shared_view_username"] = None
    conn = sqlite3.connect('health-tracker.db')
    cur = conn.cursor()

    cur.execute('''SELECT year, month, day, time, bpm, sys, dia, weight, id FROM records WHERE user_id = ? 
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
    suggestions = get_suggestions(age, session["user_id"])
    
    return render_template("index.html", rows=rows, suggestions=suggestions)

@app.route("/delete_entry", methods={"POST"})
def delete_entry():
    delete_record_id = request.form.get("record_id")

    conn = sqlite3.connect('health-tracker.db')
    cur = conn.cursor()

    cur.execute('''DELETE FROM records WHERE id = ?''', (delete_record_id,))
    conn.commit()

    cur.close()
    conn.close()
    flash("Sucessfully deleted entry", 'success')
    return redirect("/")


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
        
        elif not request.forn.get("dob"):
            flash("Must enter Date of Birth", 'error')
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
        
        conn = sqlite3.connect('health-tracker.db')
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, hash, dob_year, dob_month, dob_day) VALUES (?, ?, ?, ?, ?)",
                       (new_username, generate_password_hash(new_password), int(year), int(month), int(day)))
            conn.commit()
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
@login_required
def enter():
    session["shared_view_id"] = None
    session["shared_view_username"] = None
    if request.method == "POST":
         
        bpm = request.form.get("bpm")
        sys = (request.form.get("sys"))
        dia = (request.form.get("dia"))
        weight = (request.form.get("weight"))

        if not bpm and not sys and not dia and not weight:
            flash("At least one field must be filled", 'error')
            return render_template('enter.html')

        now = datetime.now()

        year = 0
        month = 0
        day = 0
        time = ""

        if request.form.get("date"):
            date = request.form.get("date")
            year = date[0:4]
            month = date[5:7]
            day = date[8:10]
        else:
            year = now.year
            month = now.month
            day = now.day
        
        if request.form.get("time"):
            input_time = request.form.get("time")
            time_obj = datetime.strptime(input_time, '%H:%M')
            time = time_obj.strftime('%H:%M:%S')
        else:
            time = now.strftime('%H:%M:%S')
    
        conn = sqlite3.connect('health-tracker.db')
        cur = conn.cursor()

        cur.execute('''INSERT INTO records (bpm, sys, dia, weight, year, month, day, time, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (bpm, sys, dia, weight, year, month, day, time, session["user_id"]))
        conn.commit()
         
        cur.close()
        conn.close()

        flash("Successfully Logged Data!", 'success')
        return redirect("/")
    else:
        return render_template("enter.html")
    
@app.route("/share", methods=["GET", "POST"])
@login_required
def share():
    session["shared_view_id"] = None
    session["shared_view_username"] = None

    if request.method == "GET":
        conn = sqlite3.connect('health-tracker.db')
        cur = conn.cursor()

        cur.execute('''SELECT id, username FROM users WHERE id IN (
                    SELECT owner_id FROM shared WHERE viewer_id = ?)''', (session["user_id"],))

        accessible_users = cur.fetchall()

        cur.execute('''SELECT id, username FROM users WHERE id IN (
                    SELECT viewer_id FROM shared WHERE owner_id = ?)''', (session["user_id"],))
            
        shared_users = cur.fetchall()

        cur.close()
        conn.close()
        return render_template("share.html", accessible_users=accessible_users, shared_users=shared_users)
    else:
        if not request.form.get("share-user"):
            flash("Must enter username to share with", 'error')
            return redirect("/share")

        new_shared_user = request.form.get("share-user")

        conn = sqlite3.connect('health-tracker.db')
        cur = conn.cursor()

        cur.execute('''SELECT username FROM users WHERE id IN (
                    SELECT viewer_id FROM shared WHERE owner_id = ?)''', (session["user_id"],))
        
        shared_users = cur.fetchall()

        cur.execute('''SELECT username FROM users WHERE id != ?''', (session["user_id"],))

        all_users = cur.fetchall()

        cur.execute('''SELECT username FROM users WHERE id = ?''', (session["user_id"],))

        current_user = cur.fetchone()[0]

        if new_shared_user == current_user:
            cur.close()
            conn.close()
            flash("You cannot share with yourself", 'error')
            return redirect("/share")
        
        for user in shared_users:
            if new_shared_user == user[0]:
                cur.close()
                conn.close()
                flash(f"Already sharing with {new_shared_user}", 'error')
                return redirect("/share")
        
        for user in all_users:
            if new_shared_user == user[0]:
                break
        else:
            cur.close()
            conn.close()
            flash(f"{new_shared_user} is not an valid user", 'error')
            return redirect("/share")
        
        cur.execute("SELECT id FROM users WHERE username = ?", (new_shared_user,))
        new_shared_user_id = cur.fetchone()[0]
        
        cur.execute('''INSERT INTO shared (owner_id, viewer_id) VALUES (?, ?)''', (session["user_id"], new_shared_user_id))
        conn.commit()

        cur.close()
        conn.close()
        flash(f"Successfully shared with {new_shared_user}", 'success')
        return redirect("/share")
    
@app.route("/unshare", methods=["POST"])
def unshare():
    remove_user_id = request.form.get("user_id")
    remove_username = request.form.get("username")

    conn = sqlite3.connect('health-tracker.db')
    cur = conn.cursor()

    cur.execute("DELETE FROM shared WHERE owner_id = ? AND viewer_id = ?", (session["user_id"], remove_user_id))
    conn.commit()

    cur.close()
    conn.close()
    flash(f"Stopped sharing with {remove_username}", 'success')
    return redirect("/share")


@app.route("/shared_data", methods=["GET", "POST"])
@login_required
def shared_data():
    if request.method == "POST":
        session["shared_view_id"] = request.form.get("user_id")
        session["shared_view_username"] = request.form.get("username")
        return redirect("/shared_data")
    else:
         if not session["shared_view_id"]:
             return redirect("/share")
         conn = sqlite3.connect('health-tracker.db')
         cur = conn.cursor()

         cur.execute('''SELECT year, month, day, time, bpm, sys, dia, weight, id FROM records WHERE user_id = ? 
                     ORDER BY year DESC, month DESC, day DESC, time DESC''', (session["shared_view_id"],))
        
         rows = cur.fetchall()

         cur.execute('''SELECT dob_year, dob_month, dob_day FROM users WHERE id = ?''', (session["shared_view_id"],))
         dob = cur.fetchone()
         
         dob_year = dob[0]
         dob_month = dob[1]
         dob_day = dob[2]
    
         cur.close()
         conn.close()

         age = calculate_age(dob_year, dob_month, dob_day)
         suggestions = get_suggestions(age, session["shared_view_id"])
    
         return render_template("shared_data.html", rows=rows, suggestions=suggestions, username=session["shared_view_username"])
    
@app.route("/bpm_graph")
@login_required
def bpm_graph():
    session["shared_view_id"] = None
    session["shared_view_username"] = None
    conn = sqlite3.connect('health-tracker.db')
    cur = conn.cursor()

    cur.execute('''SELECT year, month, day, time, bpm FROM records WHERE user_id = ? 
                ORDER BY year ASC, month ASC, day ASC, time ASC''', (session["user_id"],))

    data = cur.fetchall()
    
    dates = [f"{row[0]}-{row[1]:02d}-{row[2]:02d}" for row in data]
    times = [row[3] for row in data]
    bpms = [row[4] for row in data]

    datetimes = [f"{date}T{time}" for date, time in zip(dates, times)]

    cur.execute('''SELECT dob_year, dob_month, dob_day FROM users WHERE id = ?''', (session["user_id"],))
    dob = cur.fetchall()
    healthy_results = healthy(calculate_age(dob[0][0], dob[0][1], dob[0][2]), "bpm")

    cur.close()
    conn.close()

    return render_template("bpm_graph.html", owner="Your", datetimes=datetimes, bpms=bpms, max_healthy=healthy_results[0], min_healthy=healthy_results[1])

@app.route("/shared_bpm_graph")
@login_required
def shared_bpm_graph():
    if not session["shared_view_id"]:
        return redirect("/share")
    
    conn = sqlite3.connect('health-tracker.db')
    cur = conn.cursor()

    cur.execute('''SELECT year, month, day, time, bpm FROM records WHERE user_id = ? 
                ORDER BY year ASC, month ASC, day ASC, time ASC''', (session["shared_view_id"],))

    data = cur.fetchall()
    
    dates = [f"{row[0]}-{row[1]:02d}-{row[2]:02d}" for row in data]
    times = [row[3] for row in data]
    bpms = [row[4] for row in data]

    datetimes = [f"{date}T{time}" for date, time in zip(dates, times)]

    cur.execute('''SELECT dob_year, dob_month, dob_day FROM users WHERE id = ?''', (session["shared_view_id"],))
    dob = cur.fetchall()
    healthy_results = healthy(calculate_age(dob[0][0], dob[0][1], dob[0][2]), "bpm")

    cur.close()
    conn.close()

    return render_template("bpm_graph.html", owner=f"{session['shared_view_username']}'s", datetimes=datetimes, bpms=bpms, max_healthy=healthy_results[0], min_healthy=healthy_results[1])

@app.route("/weight_graph")
@login_required
def weight_graph():
    session["shared_view_id"] = None
    session["shared_view_username"] = None
    conn = sqlite3.connect('health-tracker.db')
    cur = conn.cursor()

    cur.execute('''SELECT year, month, day, time, weight FROM records WHERE user_id = ? 
                ORDER BY year ASC, month ASC, day ASC, time ASC''', (session["user_id"],))

    data = cur.fetchall()
    
    dates = [f"{row[0]}-{row[1]:02d}-{row[2]:02d}" for row in data]
    times = [row[3] for row in data]
    weights = [row[4] for row in data]

    datetimes = [f"{date}T{time}" for date, time in zip(dates, times)]

    cur.close()
    conn.close()

    return render_template("weight_graph.html", owner="Your", datetimes=datetimes, weights=weights)

@app.route("/shared_weight_graph")
@login_required
def shared_weight_graph():
    if not session["shared_view_id"]:
        return redirect("/share")
    
    conn = sqlite3.connect('health-tracker.db')
    cur = conn.cursor()

    cur.execute('''SELECT year, month, day, time, weight FROM records WHERE user_id = ? 
                ORDER BY year ASC, month ASC, day ASC, time ASC''', (session["shared_view_id"],))

    data = cur.fetchall()
    
    dates = [f"{row[0]}-{row[1]:02d}-{row[2]:02d}" for row in data]
    times = [row[3] for row in data]
    weights = [row[4] for row in data]

    datetimes = [f"{date}T{time}" for date, time in zip(dates, times)]

    cur.close()
    conn.close()

    return render_template("weight_graph.html", owner=f"{session['shared_view_username']}'s", datetimes=datetimes, weights=weights)

@app.route("/bp_graph")
@login_required
def bp_graph():
    session["shared_view_id"] = None
    session["shared_view_username"] = None
    conn = sqlite3.connect('health-tracker.db')
    cur = conn.cursor()

    cur.execute('''SELECT year, month, day, time, sys, dia FROM records WHERE user_id = ? 
                ORDER BY year ASC, month ASC, day ASC, time ASC''', (session["user_id"],))

    data = cur.fetchall()
    
    dates = [f"{row[0]}-{row[1]:02d}-{row[2]:02d}" for row in data]
    times = [row[3] for row in data]
    syss = [row[4] for row in data]
    dias = [row[5] for row in data]

    datetimes = [f"{date}T{time}" for date, time in zip(dates, times)]

    cur.execute('''SELECT dob_year, dob_month, dob_day FROM users WHERE id = ?''', (session["user_id"],))
    dob = cur.fetchall()
    sys_healthy_results = healthy(calculate_age(dob[0][0], dob[0][1], dob[0][2]), "sys")
    dia_healthy_results = healthy(calculate_age(dob[0][0], dob[0][1], dob[0][2]), "dia")

    cur.close()
    conn.close()

    return render_template("bp_graph.html", owner="Your", datetimes=datetimes, syss=syss, dias=dias, sys_max_healthy=sys_healthy_results[0], sys_min_healthy=sys_healthy_results[1], dia_max_healthy=dia_healthy_results[0], dia_min_healthy=dia_healthy_results[1])

@app.route("/shared_bp_graph")
@login_required
def shared_bp_graph():
    if not session["shared_view_id"]:
        return redirect("/share")
    
    conn = sqlite3.connect('health-tracker.db')
    cur = conn.cursor()

    cur.execute('''SELECT year, month, day, time, sys, dia FROM records WHERE user_id = ? 
                ORDER BY year ASC, month ASC, day ASC, time ASC''', (session["shared_view_id"],))

    data = cur.fetchall()
    
    dates = [f"{row[0]}-{row[1]:02d}-{row[2]:02d}" for row in data]
    times = [row[3] for row in data]
    syss = [row[4] for row in data]
    dias = [row[5] for row in data]

    datetimes = [f"{date}T{time}" for date, time in zip(dates, times)]

    cur.execute('''SELECT dob_year, dob_month, dob_day FROM users WHERE id = ?''', (session["shared_view_id"],))
    dob = cur.fetchall()
    sys_healthy_results = healthy(calculate_age(dob[0][0], dob[0][1], dob[0][2]), "sys")
    dia_healthy_results = healthy(calculate_age(dob[0][0], dob[0][1], dob[0][2]), "dia")

    cur.close()
    conn.close()

    return render_template("bp_graph.html", owner=f"{session['shared_view_username']}'s", datetimes=datetimes, syss=syss, dias=dias, sys_max_healthy=sys_healthy_results[0], sys_min_healthy=sys_healthy_results[1], dia_max_healthy=dia_healthy_results[0], dia_min_healthy=dia_healthy_results[1])