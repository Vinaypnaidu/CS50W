import os
from flask import Flask, session, render_template, request, flash, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from functools import wraps
import requests

def login_required(f):
    """
    Decorate routes to require login.
    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_name") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


app = Flask(__name__)

# Check for environment variable
if not os.getenv('DATABASE_URL'):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Set up database
engine = create_engine(os.getenv('DATABASE_URL'))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/", methods=["GET","POST"])
@login_required
def index():
    return render_template("loggedin.html")
    

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    if request.method == "POST":
        session.clear()
        user_name = request.form.get("username")
        password = request.form.get("password")
        rows = db.execute("SELECT * FROM users WHERE user_name = :user_name",{"user_name":user_name}).fetchone()
        if rows is None:
            return "Please Register!"
        pass1 = db.execute("SELECT password FROM users WHERE user_name = :user_name",
                          {"user_name":user_name}).fetchone()
        if str(pass1[0]) != password:
            return "Invalid password!"
    
        session["user_name"] = user_name
        return redirect(url_for("index"))
    
        
        
        
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    if request.method == "POST":
        user_name = request.form.get("username")
        password = request.form.get("password")
        try:
            db.execute("INSERT INTO users (user_name,password) VALUES (:user_name,:password)", {"user_name":user_name,"password":password})
            db.commit()
            return "Registered!"
        except:    
            return "Username taken"
        
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/search",  methods = ["GET","POST"])
@login_required
def search():
    results = []
    results1 = []
    results2 = []
    results3 = []
    isbn = (request.form.get("isbn"))
    try:
        title = ((request.form.get("title")).lower()).capitalize()
    except:
        title = ""
        pass    
    author = (request.form.get("author"))
    if title != "" :
        results1 = db.execute("SELECT * FROM books WHERE title ILIKE CONCAT('%', :title, '%')  LIMIT 5", {"title":title}).fetchall()
    if isbn != "" :
        results2 = db.execute("SELECT * FROM books WHERE isbn ILIKE CONCAT('%', :isbn, '%')  LIMIT 5", {"isbn":isbn}).fetchall()
    if author != "" :
        results3 = db.execute("SELECT * FROM books WHERE author ILIKE CONCAT('%', :author, '%')  LIMIT 5", {"author":author}).fetchall()
    if title == "" and isbn == "" and author == "":
        return "Please enter one of them!"            
    if str(results1) == "[]" and str(results2) == "[]" and str(results3) == "[]":
        return "No matching results!"
    string1 = ""    
    results = list(results1) + list(results2) + list(results3)
    return render_template("bookpage.html", results = results)

@app.route("/display", methods = ["GET","POST"])
@login_required
def display():
    if request.method == "POST":
        res = request.form.get("result")
        isbn = res[2:12]
        info = ""
        for char in res:
            if char == "(" or char == ")" :
                pass
            else:
                info += char
        info = info.split(",")
        if len(info) == 5:
            info[1] = info[1] + info[2]  
            info.pop(2)
        isbn2 = isbn[0:11] 
        query = requests.get("https://www.goodreads.com/book/review_counts.json",params={"key": "sJ64q22VcdDEm7CMSDmCg", "isbns": isbn2}).json()
        avgrating = query["books"][0]["average_rating"]
        ratingcount = query["books"][0]["ratings_count"]
                    
        detail = list(db.execute("SELECT rating,review,user_name FROM details WHERE isbn = :isbn", {"isbn":isbn}).fetchall())
        return render_template("details.html", info = info, isbn2 = isbn2, detail = detail, avgrating = avgrating, ratingcount = ratingcount )  
    
@app.route("/review",  methods = ["GET","POST"])
@login_required
def submitreviw():    
    if request.method == "POST":
        review = request.form.get("review")
        rating = request.form.get("rating")
        isbn = request.form.get("isbn")
        user_name = session['user_name']
        result = db.execute("SELECT * FROM details WHERE isbn = :isbn AND user_name = :user_name", {"isbn":isbn, "user_name":user_name}).fetchone()
        if result is not None:
            return "You can submit only one review for a book!"
        db.execute("INSERT INTO details (review,rating,isbn,user_name) VALUES (:review,:rating,:isbn,:user_name)", {"review":review, "rating":rating, "isbn":isbn, "user_name":user_name})
        db.commit()
        return "Submitted"
    if request.method == "GET":
        return render_template("review.html") 
 
 
@app.route("/api/<isbn>", methods=['GET'])
@login_required
def myapi(isbn):
    row = db.execute("SELECT title, author, year, isbn FROM books WHERE isbn = :isbn", {"isbn":isbn})
    if row.rowcount != 1:
        return jsonify({"Error": "ISBN not found!"}), 404
    tmp = row.fetchone()
    json = {}
    tmp = list(tmp)
    
    json["title"] = tmp[0] 
    json["author"] = tmp[1]
    json["year"] = int(tmp[2])
    json["isbn"] = tmp[3]
    
    row1 = db.execute("SELECT COUNT(review) AS review_count, AVG(rating) AS average_score FROM details WHERE isbn = :isbn GROUP BY isbn", {"isbn":isbn})
    if row1.rowcount != 1:
        json["review_count"] = 0
        json["average_score"] = 0
    else:
        tmp1 = row1.fetchone()
        tmp1 = list(tmp1)
        json["review_count"] = int(tmp1[0])
        json["average_score"] = float(tmp1[1])    
    return jsonify(json)
        
import requests
res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "sJ64q22VcdDEm7CMSDmCg", "isbns": "9781632168146"})
print(res.json())        
