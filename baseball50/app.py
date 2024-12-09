import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from striprtf.striprtf import rtf_to_text
import csv
from gemini_ai import get_predictions


# Configure application
app = Flask(__name__)

# Custom Jinja filter for usd


def usd(num):
    return f"${num:,.2f}"


app.jinja_env.filters["usd"] = usd


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///baseball.db")

# List of dictionaries representing each teams name, location, and abbreviation
teams = [
    {"name": "Diamondbacks", "location": "Arizona", "abbr": "ARI"},
    {"name": "Braves", "location": "Atlanta", "abbr": "ATL"},
    {"name": "Orioles", "location": "Baltimore", "abbr": "BAL"},
    {"name": "Red Sox", "location": "Boston", "abbr": "BOS"},
    {"name": "White Sox", "location": "Chicago", "abbr": "CWS"},
    {"name": "Cubs", "location": "Chicago", "abbr": "CHC"},
    {"name": "Reds", "location": "Cincinnati", "abbr": "CIN"},
    {"name": "Guardians", "location": "Cleveland", "abbr": "CLE"},
    {"name": "Rockies", "location": "Colorado", "abbr": "COL"},
    {"name": "Tigers", "location": "Detroit", "abbr": "DET"},
    {"name": "Astros", "location": "Houston", "abbr": "HOU"},
    {"name": "Royals", "location": "Kansas City", "abbr": "KC"},
    {"name": "Angels", "location": "Los Angeles", "abbr": "LAA"},
    {"name": "Dodgers", "location": "Los Angeles", "abbr": "LAD"},
    {"name": "Marlins", "location": "Miami", "abbr": "MIA"},
    {"name": "Brewers", "location": "Milwaukee", "abbr": "MIL"},
    {"name": "Twins", "location": "Minnesota", "abbr": "MIN"},
    {"name": "Yankees", "location": "New York", "abbr": "NYY"},
    {"name": "Mets", "location": "New York", "abbr": "NYM"},
    {"name": "Athletics", "location": "Oakland", "abbr": "OAK"},
    {"name": "Phillies", "location": "Philadelphia", "abbr": "PHI"},
    {"name": "Pirates", "location": "Pittsburgh", "abbr": "PIT"},
    {"name": "Padres", "location": "San Diego", "abbr": "SD"},
    {"name": "Giants", "location": "San Francisco", "abbr": "SF"},
    {"name": "Mariners", "location": "Seattle", "abbr": "SEA"},
    {"name": "Cardinals", "location": "St. Louis", "abbr": "STL"},
    {"name": "Rays", "location": "Tampa Bay", "abbr": "TB"},
    {"name": "Rangers", "location": "Texas", "abbr": "TEX"},
    {"name": "Blue Jays", "location": "Toronto", "abbr": "TOR"},
    {"name": "Nationals", "location": "Washington", "abbr": "WSH"}
]

# locking pagesif the user is not logged in


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# displays the players that the user currently owns based on the free agents page
@app.route("/")
@login_required
def index():

    # Finds amount of cash that user has
    cash = db.execute(
        'SELECT cash FROM users WHERE id = ?', session["user_id"]
    )[0]["cash"]

    # Finds batters that the user owns
    batters = db.execute('''
        SELECT * FROM batters WHERE id IN
        (SELECT player_id FROM holdings WHERE user_id = ?)''', session["user_id"])

    # Finds pitchers that the user owns
    pitchers = db.execute('''
        SELECT * FROM pitchers WHERE id IN
        (SELECT player_id FROM holdings WHERE user_id = ?)''', session["user_id"])

    return render_template("index.html", batters=batters, pitchers=pitchers, cash=cash)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            print("must provide username", 403)
            return render_template("error.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            print("must provide password", 403)
            return render_template("error.html")

        rows = db.execute(
            'SELECT * FROM users WHERE username = ?', request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            print("invalid username and/or password", 403)
            return render_template("loginerror.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# logout page that redirects back to the login


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via GET (as by submitting a form via POST)
    if request.method == "GET":
        # Since nothing is submitted, just render
        return render_template("register.html")

    else:
        # set user's input as variables
        username = request.form.get("username")
        password = request.form.get("password")

        # Make sure the user submitted username and password
        if not username or not password:
            print("Please submit both username and password", 400)
            return render_template("error.html")

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Check if username already exsists using try/return
        try:
            # Insert new user into database
            db.execute("INSERT INTO users(username, hash) VALUES(?, ?)", username, hashed_password)
        except ValueError:
            print("Username already taken", 400)
            return render_template("error.html")

        # Get the rows from the datatable
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        # Log the user-in (remember that they logged in)
        session["user_id"] = rows[0]["id"]

        # Initialize the cash variable

    # Back to register page
    return redirect("/login")


# rules python
@app.route("/rules")
@login_required
def rules():

    # Find current cash to display:
    cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]
    return render_template("rules.html", cash=cash)


@app.route("/simulation", methods=["GET", "POST"])
@login_required
def simulation():
    # Find current cash to display:
    cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]

    # displaying simulation page
    if request.method == "GET":
        return render_template("simulation.html", cash=cash)

    if request.method == "POST":

        # Get year of simulation
        try:
            year = int(request.form.get("year"))
        except ValueError:
            return render_template("error.html", cash=cash, text="Please enter a valid integer")

        # Check that year is a valid integer between 1901 and 2024
        if (year < 1900) or (year > 2030):
            return render_template("error.html", cash=cash, text="Please enter a valid year between 1900 and 2039")

        # Find current batters on roster
        batters = db.execute('''SELECT * FROM batters WHERE id IN
        (SELECT player_id FROM holdings WHERE user_id = ?)''', session["user_id"])

        # Find current pitchers on roster
        pitchers = db.execute('''SELECT * FROM pitchers WHERE id IN
        (SELECT player_id FROM holdings WHERE user_id = ?)''', session["user_id"])

        csv_file1 = "owned_batters.csv"

        # Write the owned batters to a CSV file
        csv_file1 = "owned_batters.csv"
        with open(csv_file1, "w", newline="") as file:
            # Extract the keys of the first dictionary as the header row
            fieldnames = batters[0].keys()

            # Create a DictWriter object
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            # Write the header row
            writer.writeheader()

            # Write the data rows
            writer.writerows(batters)

        # Write the owned pitchers to a CSV file
        csv_file2 = "owned_pitchers.csv"
        with open(csv_file2, "w", newline="") as file:
            # Extract the keys of the first dictionary as the header row
            fieldnames = pitchers[0].keys()

            # Create a DictWriter object
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            # Write the header row
            writer.writeheader()

            # Write the data rows
            writer.writerows(pitchers)

        # Get prediction from Gemini results
        prediction = (get_predictions(csv_file1, csv_file2, year))

        # Empty csv files when done
        with open('owned_batters.csv', 'w') as file:
            pass

        with open('owned_pitchers.csv', 'w') as file:
            pass

        return render_template("simulated.html", cash=cash, prediction=prediction)


@app.route("/simulated", methods=["GET", "POST"])
@login_required
def simulated():
    # Find current cash to display:
    cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]

    # displaying simulation page
    if request.method == "GET":
        return render_template("simulated.html", cash=cash)
    if request.method == "POST":
        return redirect("/")

# Player Search Python


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    # Find current cash to display:
    cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]

    if request.method == "GET":
        return render_template("search.html", cash=cash)

    # If method is POST:
    player_name = request.form.get("player")

    # Runs a SQL query to find batters that match the input name
    matches = db.execute(
        'SELECT Name, Pos, Age, AVG, H, HR, id FROM batters WHERE name LIKE ?', player_name)

    # Runs a SQL query to find pitchers that match the input name, and add those players to the list of matches
    matches.extend(db.execute(
        'SELECT Name, AGE, ERA, W, L, WHIP, id FROM pitchers WHERE name LIKE ?', player_name))

    # Checks if there are no matches:
    if not matches:
        return render_template("error.html", text="No matches!", cash=cash)

    return render_template("searched.html", cash=cash, matches=matches)


@app.route('/api/view_roster', methods=['GET'])
def view_roster():
    username = request.args.get('username')
    if username in user_rosters:
        return jsonify(success=True, roster=user_rosters[username])
    return jsonify(success=False, message="User not found.")


# Choosing team page

@app.route("/chooseteam", methods=["POST", "GET"])
@login_required
def chooseteam():
    if request.method == "GET":

        # Finds user's cash amount
        cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]
        return render_template("chooseteam.html", teams=teams, cash=cash)

    if request.method == "POST":
        # Retrieve the team name from the request
        team = request.form.get("team")

        # Let user own all pitchers from chosen team
        db.execute('''
            INSERT INTO holdings (user_id, player_id)
            SELECT ?, id
            FROM pitchers
            WHERE team = ?
        ''', session["user_id"], team)

        # Let user own all batters from chosen team
        db.execute('''
            INSERT INTO holdings (user_id, player_id)
            SELECT ?, id
            FROM batters
            WHERE team = ?
        ''', session["user_id"], team)

        return redirect("/")


@app.route("/sellbatter", methods=["POST"])
@login_required
def sellbatter():
    player_id = request.form.get("player_id")
    avg = db.execute(
        'SELECT AVG FROM batters WHERE id = ?', player_id
    )[0]["AVG"]
    value = float(avg) * 10000 + 2000

    # Find user's current cash
    current_cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]

    # Update user's cash
    db.execute(
        'UPDATE users SET cash = ? WHERE id = ?', value + current_cash, session["user_id"]
    )

    # Remove sold player from user's holding
    db.execute(
        'DELETE FROM holdings WHERE user_id = ? AND player_id = ?', session["user_id"], player_id
    )

    return redirect("/")


@app.route("/sellpitcher", methods=["POST"])
@login_required
def sellpitcher():
    player_id = request.form.get("player_id")
    avg = db.execute(
        'SELECT ERA FROM pitchers WHERE id = ?', player_id
    )[0]["ERA"]
    value = float(avg) * 1000

    # Find user's current cash
    current_cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]

    # Update user's cash
    db.execute(
        'UPDATE users SET cash = ? WHERE id = ?', value + current_cash, session["user_id"]
    )

    # Remove sold player from user's holding
    db.execute(
        'DELETE FROM holdings WHERE user_id = ? AND player_id = ?', session["user_id"], player_id
    )

    return redirect("/")


@app.route("/freeagents", methods=["GET", "POST"])
@login_required
def freeagents():
    if request.method == "GET":

        # Finds user's current cash to display
        cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]

        # Picks 10 random unowned pitchers
        freepitchers = db.execute(
            '''SELECT * FROM pitchers WHERE id NOT IN
            (SELECT player_id FROM holdings WHERE id = ?) ORDER BY RANDOM() LIMIT 10''', session["user_id"])

        # Picks 10 random unowned batters
        freebatters = db.execute(
            '''SELECT * FROM batters WHERE id NOT IN
            (SELECT player_id FROM holdings WHERE id = ?) ORDER BY RANDOM() LIMIT 10''', session["user_id"])

        return render_template("freeagents.html", freepitchers=freepitchers, freebatters=freebatters, cash=cash)

# Buys a player from the freeagents page


@app.route("/buy", methods=["POST"])
@login_required
def buy():
    player_id = request.form.get("player_id")

    owned = db.execute(
        'SELECT player_id FROM holdings WHERE user_id = ? AND player_id = ?', session["user_id"], player_id)

    if owned:
        return render_template("error.html", text="player already owned", cash=cash)

    # If player_id < 1000, the player is batter
    # Calculate batter price
    if int(player_id) < 1000:
        avg = db.execute(
            'SELECT AVG FROM batters WHERE id = ?', player_id
        )[0]["AVG"]
        price = float(avg) * 10000 + 2000

    # Else calculate pitcher price
    else:
        era = db.execute(
            'SELECT ERA FROM pitchers WHERE id = ?', player_id
        )[0]["ERA"]
        price = float(era) * 1000

    # Find user's current cash
    current_cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]

    if current_cash < price:
        return render_template("error.html", text="not enough money", cash=cash)

    # Update user's cash to reflect purchase
    db.execute('UPDATE users SET cash = ? WHERE id = ?', current_cash - price, session["user_id"])

    # Update user's owned players
    db.execute('INSERT INTO holdings (user_id, player_id) values (?, ?)',
               session["user_id"], player_id)

    return redirect("/")


# Trade Page
@app.route("/trade_roster", methods=["GET", "POST"])
@login_required
def trade_roster():
    # Insert trade request into the database

    if request.method == "POST":

        try:
            target_user_id = int(request.form.get("target_user_id"))
            offered_player_id = int(request.form.get("offered_player_id"))
            requested_player_id = int(request.form.get("requested_player_id"))
            print(session["user_id"])
            print(target_user_id)
            print(offered_player_id)
            print(requested_player_id)
            db.execute('''
                INSERT INTO table_requests(from_user, to_user, offered_player_id, requested_player_id)
                VALUES (?, ?, ?, ?)
            ''', session["user_id"], target_user_id, offered_player_id, requested_player_id)
            return redirect("/")

        except ValueError:
            print("Trade did not work", 400)
            cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]
            return render_template("error.html", cash=cash)


@app.route("/trade", methods=["GET", "POST"])
@login_required
def trade():
    # Finds current cash to display

    cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]

    if request.method == "GET":
        # Fetch user's batters
        user_batters = db.execute('''
            SELECT * FROM batters WHERE id IN (SELECT player_id FROM holdings WHERE user_id = ?)
        ''', session["user_id"])

        # Fetch user's pitchers
        user_pitchers = db.execute('''
            SELECT * FROM pitchers WHERE id IN (SELECT player_id FROM holdings WHERE user_id = ?)
        ''', session["user_id"])

        # Combine the results
        user_roster = user_batters
        user_roster.extend(user_pitchers)

        # Placeholder for other user's data if no username is searched yet
        other_user_id = None
        other_user_batters = []
        other_user_pitchers = []

        # Render the trade page with user roster and cash
        return render_template("trade.html", roster=user_roster, cash=cash, other_user_id=other_user_id,
                               other_user_batters=other_user_batters, other_user_pitchers=other_user_pitchers)

    if request.method == "POST":
        # Collect trade request details
        target_username = request.form.get("username")
        offered_player_name = request.form.get("offered_player_name")
        requested_player_name = request.form.get("requested_player_name")
        offered_player_id = request.form.get("offered_player_id")

        # print(offered_player_id)

        # Ensure valid target user
        target_user_id = db.execute(
            "SELECT id FROM users WHERE username = ?", target_username)[0]["id"]
        if not target_user_id:
            return render_template("error.html", text="Target user does not exist.")

        # Fetch other user's batters and pitchers
        other_user_batters = db.execute('''
            SELECT * FROM batters WHERE id IN (SELECT player_id FROM holdings WHERE user_id = ?)
        ''', target_user_id)

        other_user_pitchers = db.execute('''
            SELECT * FROM pitchers WHERE id IN (SELECT player_id FROM holdings WHERE user_id = ?)
        ''', target_user_id)

        # Combine the results
        other_user_roster = other_user_batters
        other_user_roster.extend(other_user_pitchers)

        # If only searching for the other user's roster
        if not offered_player_name and not requested_player_name:
            # Fetch user's batters
            user_batters = db.execute('''
                SELECT * FROM batters WHERE id IN (SELECT player_id FROM holdings WHERE user_id = ?)
            ''', target_user_id)

            # Fetch user's pitchers
            user_pitchers = db.execute('''
                SELECT * FROM pitchers WHERE id IN (SELECT player_id FROM holdings WHERE user_id = ?)
            ''', target_user_id)

            # Combine the results
            user_roster = user_batters
            user_roster.extend(user_pitchers)

            return render_template("trade_roster.html", roster=user_roster, cash=cash, offered_player_id=offered_player_id, other_user_id=target_user_id,
                                   other_user_roster=other_user_roster)

        # Get player IDs based on names
        offered_player = db.execute(
            "SELECT id FROM batters WHERE Name = ? UNION SELECT id FROM pitchers WHERE Name = ?", offered_player_name, offered_player_name)
        requested_player = db.execute(
            "SELECT id FROM batters WHERE Name = ? UNION SELECT id FROM pitchers WHERE Name = ?", requested_player_name, requested_player_name)

        if not offered_player or not requested_player:
            return render_template("error.html", text="One or both player names are invalid.")

        offered_player_id = offered_player[0]["id"]
        requested_player_id = requested_player[0]["id"]

        # Ensure user does not own the requested player
        ownership_check = db.execute(
            "SELECT player_id FROM holdings WHERE user_id = ? AND player_id = ?",
            session["user_id"], requested_player_id
        )
        if ownership_check:
            return render_template("error.html", text="You already own the requested player.")


@app.route("/trade_requests", methods=["GET", "POST"])
@login_required
def trade_requests():
    if request.method == "GET":
        cash = db.execute('SELECT cash FROM users WHERE id = ?', session["user_id"])[0]["cash"]

        # Fetch user's incoming trade requests
        # Create temporary table to combine batters and pitchers, filled with the name and player_id of every player
        db.execute('''
            CREATE TEMPORARY TABLE temp_trade_players (
            player_id INTEGER,
            player_name TEXT )
        ''')

        db.execute('''
            INSERT INTO temp_trade_players (player_id, player_name)
            SELECT id, name
            FROM pitchers
            UNION
            SELECT id, name
            FROM batters
        ''')

        # Find the names of the players from the trade requests
        trade_requests = db.execute('''
            SELECT
                id,
                tr.offered_player_id,
                n1.player_name AS offered_player_name,
                tr.requested_player_id,
                n2.player_name AS requested_player_name
            FROM
                table_requests tr
            LEFT JOIN
                temp_trade_players n1 ON tr.offered_player_id = n1.player_id
            LEFT JOIN
                temp_trade_players n2 ON tr.requested_player_id = n2.player_id
            WHERE to_user = ?''', session["user_id"]
                                    )

        # Drop temporary table once done
        db.execute('DROP TABLE temp_trade_players')

        return render_template("trade_requests.html", trade_requests=trade_requests, cash=cash)

    if request.method == "POST":
        # Handle trade acceptance or rejection
        trade_id = request.form.get("trade_id")
        action = request.form.get("action")

        if action == "accept":
            # Execute the trade
            trade = db.execute('''
                SELECT from_user, offered_player_id, requested_player_id
                FROM table_requests WHERE id = ?
            ''', trade_id)[0]

            from_user_id = trade["from_user"]
            offered_player_id = trade["offered_player_id"]
            requested_player_id = trade["requested_player_id"]

            # Update ownership
            db.execute('''
                UPDATE holdings SET user_id = ? WHERE player_id = ?
            ''', session["user_id"], offered_player_id)
            db.execute('''
                UPDATE holdings SET user_id = ? WHERE player_id = ?
            ''', from_user_id, requested_player_id)

        # Remove the trade request after processing
        db.execute('DELETE FROM table_requests WHERE id = ?', trade_id)

        return redirect("/trade_requests")
