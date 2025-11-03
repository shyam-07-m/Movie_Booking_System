from flask import Flask, render_template, request, redirect, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flash messages

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",  # Change if needed
    password="123456789@123456789",  # Change to your MySQL password
    database="moviebooking"
)
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/movies')
    return redirect('/login')
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "success")
    return redirect('/login')


# Home Page - Show available movies, bookings, and canceled bookings
@app.route('/')
def index():
    cursor = db.cursor()

    # Fetch movies
    cursor.execute("SELECT * FROM movies")
    movies = cursor.fetchall()

    cursor.close()
    return render_template("index.html", movies=movies)

# Register Route - Register a new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        cursor = db.cursor()
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        db.commit()
        cursor.close()

        flash("Registration successful! Please log in.", "success")
        return redirect('/login')

    return render_template("register.html")

# Login Route - Login for registered users
@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()  # This ensures no previous session or messages linger

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            return redirect('/movies')
        else:
            flash("Invalid credentials, please try again.", "error")
            return redirect('/login')

    return render_template("login.html")


# Movies Page - Show available movies with booking options
@app.route('/movies')
def movies():
    if 'user_id' not in session:
        flash("Please log in first.", "error")
        return redirect('/login')

    cursor = db.cursor()
    cursor.execute("SELECT * FROM movies")
    movies = cursor.fetchall()

    cursor.close()
    return render_template("movies.html", movies=movies)

# Book Ticket Route
@app.route('/book/<int:movie_id>', methods=['POST'])
def book_ticket(movie_id):
    if 'user_id' not in session:
        flash("Please log in first.", "error")
        return redirect('/login')

    user_id = session['user_id']
    seats = int(request.form['seats'])

    cursor = db.cursor()
    cursor.execute("SELECT available_seats FROM movies WHERE id = %s", (movie_id,))
    available_seats = cursor.fetchone()[0]

    if seats > available_seats:
        flash("Not enough seats available!", "error")
        return redirect('/movies')

    cursor.execute("INSERT INTO bookings (user_id, movie_id, seats) VALUES (%s, %s, %s)", (user_id, movie_id, seats))
    db.commit()

    cursor.execute("UPDATE movies SET available_seats = available_seats - %s WHERE id = %s", (seats, movie_id))
    db.commit()

    cursor.close()
    flash("Your seat is confirmed!", "success")
    return redirect('/movies')

# Cancel Booking Route
@app.route('/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if 'user_id' not in session:
        flash("Please log in first.", "error")
        return redirect('/login')

    cursor = db.cursor()

    # Get booking details
    cursor.execute("SELECT movie_id, user_id, seats FROM bookings WHERE id = %s", (booking_id,))
    booking = cursor.fetchone()

    if booking:
        movie_id, user_id, seats = booking

        # Insert canceled booking into database
        cursor.execute("INSERT INTO canceled_bookings (movie_id, user_id, seats) VALUES (%s, %s, %s)", (movie_id, user_id, seats))
        db.commit()

        # Delete booking from database
        cursor.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
        db.commit()

        # Restore seats in movies table
        cursor.execute("UPDATE movies SET available_seats = available_seats + %s WHERE id = %s", (seats, movie_id))
        db.commit()

        flash("Your booking has been canceled.", "success")

    cursor.close()
    return redirect('/movies')
@app.route('/booking/confirmation/<int:booking_id>')
def booking_confirmation(booking_id):
    cursor = db.cursor()
    cursor.execute("SELECT movies.name, bookings.seats FROM bookings JOIN movies ON bookings.movie_id = movies.id WHERE bookings.id = %s", (booking_id,))
    booking = cursor.fetchone()
    cursor.close()

    if booking:
        movie_name, seats = booking
        return render_template("booking_confirmation.html", movie_name=movie_name, seats=seats, booking_id=booking_id)
    else:
        flash("Booking not found!", "error")
        return redirect('/movies')
@app.route('/cancellation/confirmation/<int:booking_id>')
def cancellation_confirmation(booking_id):
    cursor = db.cursor()
    cursor.execute("SELECT movies.name, canceled_bookings.seats FROM canceled_bookings JOIN movies ON canceled_bookings.movie_id = movies.id WHERE canceled_bookings.id = %s", (booking_id,))
    canceled_booking = cursor.fetchone()
    cursor.close()

    if canceled_booking:
        movie_name, seats = canceled_booking
        return render_template("cancellation_confirmation.html", movie_name=movie_name, seats=seats)
    else:
        flash("Cancellation not found!", "error")
        return redirect('/movies')

@app.route('/mybookings')
def my_bookings():
    if 'user_id' not in session:
        flash("Please log in first.", "error")
        return redirect('/login')

    user_id = session['user_id']
    cursor = db.cursor()
    cursor.execute("""
        SELECT bookings.id, movies.name, bookings.seats
        FROM bookings
        JOIN movies ON bookings.movie_id = movies.id
        WHERE bookings.user_id = %s
    """, (user_id,))
    bookings = cursor.fetchall()
    cursor.close()

    return render_template("mybookings.html", bookings=bookings)


if __name__ == '__main__':
    app.run(debug=True)
