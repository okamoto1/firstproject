import os, requests

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from flask_bcrypt import Bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from datetime import datetime

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
bcrypt = Bcrypt(app)


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET"])
def index():
    if session.get('logged_in') is None:
        return render_template("index.html")
    else:
        return redirect(url_for('logged', usuario = session['logged_in']))

#simple register function i didnt took to much attention to the security
@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        user = request.form.get("user")
        password = request.form.get("password")
        if not user or not password:
            return render_template("register.html", message1 = "2", usuario = "red", senha = "red")
        else:
            alo = db.execute("SELECT * FROM registro1 WHERE username = :user", {"user": user})
            pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            if alo.rowcount == 0:
                db.execute("INSERT INTO registro1 (username, password) VALUES (:user, :password)", {"user": user, "password": pw_hash})
                db.commit()
                return redirect(url_for('login'))
            else:
                return render_template("register.html", usuario = "red", message1 = '1')
    else:
        return render_template("register.html")

#login function
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        user = request.form.get("user")
        password = request.form.get("password")
        alo1 = db.execute("SELECT * FROM registro1 WHERE username = :user", {"user": user})
        if alo1.rowcount == 1:
            if bcrypt.check_password_hash(alo1.fetchone().password, password):
                session['logged_in'] = user
                return redirect(url_for("index"))
            else:
                return render_template("login.html", senha = "red")
        else:
            return render_template("login.html", usuario = "red")
    else:
        return render_template("login.html")

@app.route("/logged/<usuario>")
def logged(usuario):
    return render_template("logged.html", usuario = usuario)

@app.route("/search", methods=["GET","POST"])
def search():
    search = request.form.get("search")
    if not search:
        return render_template("search.html")
    titulo = db.execute("SELECT * FROM titles WHERE LOWER(title) LIKE LOWER(:title)", {"title": '%'+search+'%'})
    autor = db.execute("SELECT * FROM author JOIN titles ON author_book_id = book_id WHERE LOWER(author) LIKE LOWER(:author)", {"author": '%'+search+'%'})
    isbn = db.execute("SELECT * FROM isbn JOIN titles ON id = book_id WHERE LOWER(isbn) LIKE LOWER(:isbn)", {"isbn": '%'+search+'%'})
    if titulo.rowcount != 0 or autor.rowcount != 0 or isbn.rowcount != 0:
        if titulo.rowcount > 1 or autor.rowcount > 1 or isbn.rowcount > 1:
            message = "Encontramos os seguintes titulos: "
            return render_template("search.html", message = message, este = titulo.fetchall(), este1 = autor.fetchall(), este2 = isbn.fetchall())
        else:
            message = "Encontramos o seguinte titulo: "
            return render_template("search.html", message = message, este = titulo.fetchall(), este1 = autor.fetchall(), este2 = isbn.fetchall())
    else:
        return render_template("search.html", message = "Não encontramos nenhum livro ou autor")


@app.route("/books/<string:titulo>", methods=['POST', 'GET'])
def books(titulo):
    teste = db.execute("SELECT * FROM titles JOIN author ON book_id = author_book_id JOIN isbn ON book_id = id WHERE title = :title", {"title": titulo})
    teste1 = db.execute("SELECT * FROM titles JOIN author ON book_id = author_book_id JOIN isbn ON book_id = id WHERE title = :title", {"title": titulo})
    review = db.execute("SELECT * FROM titles JOIN review ON book_id = review_book_id WHERE title = :title", {"title": titulo})
    rate = db.execute("SELECT * FROM rate JOIN titles ON rate_id = book_id WHERE title = :title", {"title": titulo})
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "OrGTgzNvHyNRgbgvS9boA", "isbns": teste1.fetchone().isbn})

    if res.status_code != 200:
        message3, message4 = None, None
    else:
        books = res.json().get('books')
        message3 = books[0].get('id')
        message4 = books[0].get('ratings_count')
    if review.rowcount != 0:
        message1 = review.fetchall()
    if rate.rowcount == 0:
        message2 = 'there is no rating yet'
    else:
        j, somador =  0, 0
        while j < rate.rowcount:
            for i in rate.fetchall():
                somador = i.rate + somador
            j = j + 1
        message2 = somador/rate.rowcount
    if session.get('logged_in') is None:
        return render_template("books.html", message = teste.fetchall(), message1 = message1, message2 = message2, message3 = message3, message4 = message4, error = 'erro')
    else:
        return render_template("books.html", message = teste.fetchall(), message1 = message1, message2 = message2, message3 = message3, message4 = message4)

#i used this to insert my review because every time that i refreshed my page it would input the same data even if the input was empty
@app.route("/books/<string:titulo>/rev", methods=['POST', 'GET'])
def inserir(titulo):
    getreview = request.form.get("review")
    if request.method == "POST":
        if not getreview:
            return redirect(url_for('books', titulo = titulo))
        else:
            alo = db.execute("SELECT * FROM titles JOIN author ON book_id = author_book_id JOIN isbn ON book_id = id WHERE title = :title", {"title": titulo})
            db.execute("INSERT INTO review VALUES(:rev, :review_book_id, :user, :date)", {"review_book_id": alo.fetchone().id, "rev": getreview, "user": session['logged_in'], "date": datetime.now()})
            db.commit()
        return redirect(url_for('books', titulo = titulo))
    else:
        return redirect(url_for('books', titulo = titulo))

@app.route("/books/<string:titulo>/rating", methods=['POST', 'GET'])
def rate(titulo):
    getrate = request.form.get("rate")
    if request.method == "POST":
        if not getrate:
            return redirect(url_for('books', titulo = titulo, vazio = True))
        else:
            alo = db.execute("SELECT * FROM titles JOIN author ON book_id = author_book_id JOIN isbn ON book_id = id WHERE title = :title", {"title": titulo})
            db.execute("INSERT INTO rate VALUES(:rate, :rate_id)", {"rate": getrate, "rate_id": alo.fetchone().id})
            db.commit()
            return redirect(url_for('books', titulo = titulo))
    else:
        return redirect(url_for('books', titulo = titulo))

@app.route("/api", methods=['GET'])
def api1():
    return render_template("api.html", message = 'oi')

@app.route("/api/<isbn>", methods=['GET'])
def api(isbn):
    alo = db.execute("SELECT * FROM titles JOIN author ON book_id = author_book_id JOIN isbn ON book_id = id JOIN rate ON book_id = rate_id WHERE isbn = :isbn", {'isbn': isbn})
    if alo.rowcount == 0:
        return jsonify({"error"}), 422
    else:
        book = alo.fetchone()
        review = db.execute("SELECT * FROM review WHERE review_book_id = :book_id", {'book_id': book.id})
        return jsonify({"title": book.title, "author": book.author, "year": book.year, "isbn":book.isbn, "review_count":review.rowcount, "avarage_score":book.rate })


#simple logout function
@app.route("/logout")
def logout():
    if session.get('logged_in') is None:
        return render_template('index.html', alert = "You are not logged")  
    else:
        session.pop('logged_in', None)
        return redirect(url_for('index'))
