from flask import Flask, render_template, url_for, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename  # For secure file names
import os
from datetime import datetime

# Initialize Flask App
app = Flask(__name__)
app.secret_key = os.urandom(24)

# MySQL Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:0918@localhost/hotel_project'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)

# Initialize Database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# -----------------------
# Database Models
# -----------------------

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


# Room Model
class Room(db.Model):
    room_id = db.Column(db.Integer, primary_key=True)  # Matches your table schema
    room_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    availability = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)
    room_image = db.Column(db.String(100), nullable=True)
    amenity = db.Column(db.Text, nullable=True)

# Booking Model
class Booking(db.Model):
    booking_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.room_id'), nullable=False)  # Referencing 'room.room_id'
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')

    # Relationships
    user = db.relationship('User', backref=db.backref('bookings', lazy=True))
    room = db.relationship('Room', backref=db.backref('bookings', lazy=True))

# -----------------------
# Database Initialization
# -----------------------
# Admin creation script
with app.app_context():
    db.create_all()

    # Check if admin user exists
    admin = User.query.filter_by(username='admin', is_admin=True).first()
    
    if not admin:
        admin_password = generate_password_hash('admin123')
        admin_user = User(
            username='admin',
            email='admin@hotel.com',
            password=admin_password,
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created. Username: admin, Password: admin123")
    else:
        print("Admin user already exists.")

# -----------------------
# Routes
# -----------------------

@app.route('/')
def home():
    """ Home page with room listings """
    rooms = Room.query.all()  # Fetch all rooms from the database
    return render_template('home.html', rooms=rooms)  # ✅ Pass rooms to the template



@app.route('/index')
def index():
    if 'user_id' in session:
        return redirect(url_for('user_dashboard') if not session['is_admin'] else url_for('admin_dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        print("✅ Session Detected:", session)  # Debug session data
        return redirect(url_for('admin_dashboard' if session.get('is_admin') else 'user_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin  # Set the admin flag correctly
            session.permanent = True

            print("🔍 After Login Session:", session)  # Debug session data
            return redirect(url_for('admin_dashboard' if user.is_admin else 'user_dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('index.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard' if session['is_admin'] else 'user_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()

        if existing_user:
            flash('Username already exists', 'warning')
        elif existing_email:
            flash('Email already registered', 'warning')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful!', 'success')
            return redirect(url_for('login'))

    return render_template('index.html')


@app.route('/about')
def about():
    """Display the About Us page"""
    return render_template('about.html')



@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Handle Forgot Password"""
    if request.method == 'POST':
        email = request.form.get('email')
        # Dummy logic to simulate password reset
        flash(f'Password reset link sent to {email}.', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')



# Debug: Print all registered routes
print("Registered routes:")
for rule in app.url_map.iter_rules():
    print(rule.endpoint, rule.rule)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# -----------------------
# USER_DASHBOARD
# -----------------------


@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    bookings = Booking.query.filter_by(user_id=session['user_id']).all()
    return render_template('user_dashboard.html', bookings=bookings)





@app.route('/base')
def base():
    return render_template('base.html')

# -----------------------
# ADMIN_SITE
# -----------------------



# ✅ Admin dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    """ Admin Dashboard with Rooms and Bookings """
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Please log in as admin!", "danger")
        return redirect(url_for('index'))

    try:
        # Use SQLAlchemy ORM query with relationships
        bookings = (
            db.session.query(Booking)
            .join(User, Booking.user_id == User.id)
            .join(Room, Booking.room_id == Room.room_id)
            .add_columns(
                Booking.booking_id,
                User.username.label('username'),
                Room.room_type.label('room_type'),
                Booking.check_in,
                Booking.check_out,
                Booking.guests,
                Booking.status
            )
            .order_by(Booking.check_in.desc())
            .all()
        )

        return render_template('admin_dashboard.html', bookings=bookings)

    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('base'))






@app.route('/admin_logout')
def admin_logout():
    """Admin Logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('home'))


# -----------------------
# BOOKING
# -----------------------


@app.route('/book/<int:room_id>', methods=['GET', 'POST'])
def booking(room_id):
    if 'user_id' not in session:
        flash('Please log in to book a room.', 'danger')
        return redirect(url_for('index'))

    room = Room.query.get_or_404(room_id)

    if not room.availability:
        flash('This room is already booked.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        check_in = datetime.strptime(request.form['check_in'], '%Y-%m-%d')
        check_out = datetime.strptime(request.form['check_out'], '%Y-%m-%d')
        guests = int(request.form['guests'])
        
        new_booking = Booking(
            user_id=session['user_id'],
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            status='pending'
        )
        db.session.add(new_booking)

        # Update room availability
        room.availability = False
        db.session.commit()

        flash('Room booked successfully! We will shortly inform you.', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('booking.html', room=room)



# Route to handle booking submission
@app.route('/submit_booking', methods=['POST'])
def submit_booking():
    room_id = None  # Initialize room_id
    if request.method == 'POST':
        try:
            user_id = int(request.form['user_id'])
            room_id = int(request.form['room_id'])
            check_in = datetime.strptime(request.form['check_in'], '%Y-%m-%d')
            check_out = datetime.strptime(request.form['check_out'], '%Y-%m-%d')
            guests = int(request.form['guests'])

            # Insert booking into the database
            new_booking = Booking(
                user_id=user_id,
                room_id=room_id,
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                status='pending'
            )

            db.session.add(new_booking)
            db.session.commit()
            
            flash('Booking Successful!', 'success')
            return redirect(url_for('home'))  # Redirect to home or confirmation page

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            if room_id is not None:
                return redirect(url_for('booking', room_id=room_id))
            else:
                return redirect(url_for('home'))  # Fallback redirect




@app.route('/accept_booking/<int:booking_id>')
def accept_booking(booking_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    booking = Booking.query.get_or_404(booking_id)
    booking.status = 'confirmed'
    db.session.commit()
    flash('Booking confirmed.', 'success')

    return redirect(url_for('admin_dashboard'))



# ✅ Cancel booking
@app.route('/cancel_booking/<int:booking_id>')
def cancel_booking(booking_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    booking = Booking.query.get_or_404(booking_id)
    
    # Update room availability when booking is cancelled
    room = Room.query.get(booking.room_id)
    if room:
        room.availability = True

    booking.status = 'cancelled'
    db.session.commit()
    flash('Booking cancelled.', 'danger')

    return redirect(url_for('admin_dashboard'))


# -----------------------
# ROOMS
# -----------------------


# ✅ Keep this route (or choose the one you want to keep)
@app.route('/rooms')
def rooms():
    """Display all available rooms"""
    if 'user_id' not in session:
        flash('Please login to view available rooms.', 'warning')
        return redirect(url_for('login'))

    available_rooms = Room.query.filter_by(availability=True).all()
    
    return render_template('room.html', rooms=available_rooms)




UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create the folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)



ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """ Check if the uploaded file has an allowed extension """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Upload configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'

@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        
        if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            flash('File uploaded successfully!', 'success')
            return redirect(url_for('upload'))
        else:
            flash('No file selected!', 'danger')

    return render_template('upload.html')




# Route to add room from admin side
@app.route('/add_room', methods=['GET', 'POST'])  # ✅ Allow POST and GET
def add_room():
    if request.method == 'POST':
        room_type = request.form['room_type']
        price = float(request.form['price'])
        availability = 'availability' in request.form
        description = request.form['description']
        amenity = request.form['amenity']
        
        image = request.files['image']
        if image:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

            # Add the room to the database
            new_room = Room(
                room_type=room_type,
                price=price,
                availability=availability,
                description=description,
                amenity=amenity,
                room_image=image_filename
            )
            
            db.session.add(new_room)
            db.session.commit()
            
            flash('Room added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))  # Redirect to the dashboard
        
    # Render the form
    return render_template('add_room.html')


@app.route('/delete_room/<int:room_id>')
def delete_room(room_id):
    if 'user_id' not in session or not session['is_admin']:
        return redirect(url_for('index'))

    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted successfully!', 'success')

    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
