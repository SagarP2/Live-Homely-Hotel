from flask import Flask, render_template, url_for, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import pymysql

app = Flask(__name__)
app.secret_key = os.urandom(24)
# Configure session to last for 30 days
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Use SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

# Room model
class Room(db.Model):
    room_id = db.Column(db.Integer, primary_key=True)
    room_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    availability = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    room_image = db.Column(db.String(100))
    amenity = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
# Booking model
class Booking(db.Model):
    booking_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.room_id'), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', backref='bookings')
    room = db.relationship('Room', backref='bookings')

# Drop and recreate all tables (development only)
with app.app_context():
    db.drop_all()
    db.create_all()
    
    # Create admin user if doesn't exist
    admin = User.query.filter_by(username='admin').first()
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

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/index')
def index():
    # Redirect to dashboard if already logged in
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect to dashboard if already logged in
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            # Setup session permanence (cookie will last for 30 days)
            session.permanent = True
            
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect to dashboard if already logged in
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
        
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
            
            # Log the user in after registration
            user = User.query.filter_by(username=username).first()
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            session.permanent = True
            
            flash('Registration successful! Welcome to LiveHomely.', 'success')
            return redirect(url_for('user_dashboard'))
    
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    return redirect(url_for('home'))

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user's bookings sorted by creation date (newest first)
    bookings = Booking.query.filter_by(user_id=session['user_id']).order_by(Booking.created_at.desc()).all()
    
    return render_template('user_dashboard.html', username=session['username'], bookings=bookings)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    
    # Get sort parameters from request
    sort_rooms_by = request.args.get('sort_rooms_by', 'created_at')
    sort_rooms_order = request.args.get('sort_rooms_order', 'desc')
    
    sort_bookings_by = request.args.get('sort_bookings_by', 'created_at')
    sort_bookings_order = request.args.get('sort_bookings_order', 'desc')
    
    # Get rooms with sorting
    if sort_rooms_by == 'price':
        if sort_rooms_order == 'desc':
            rooms = Room.query.order_by(Room.price.desc()).all()
        else:
            rooms = Room.query.order_by(Room.price).all()
    elif sort_rooms_by == 'room_type':
        if sort_rooms_order == 'desc':
            rooms = Room.query.order_by(Room.room_type.desc()).all()
        else:
            rooms = Room.query.order_by(Room.room_type).all()
    else:  # default sort by created_at
        if sort_rooms_order == 'desc':
            rooms = Room.query.order_by(Room.created_at.desc()).all()
        else:
            rooms = Room.query.order_by(Room.created_at).all()
    
    # Get bookings with sorting
    if sort_bookings_by == 'check_in':
        if sort_bookings_order == 'desc':
            bookings = Booking.query.order_by(Booking.check_in.desc()).all()
        else:
            bookings = Booking.query.order_by(Booking.check_in).all()
    elif sort_bookings_by == 'status':
        if sort_bookings_order == 'desc':
            bookings = Booking.query.order_by(Booking.status.desc()).all()
        else:
            bookings = Booking.query.order_by(Booking.status).all()
    else:  # default sort by created_at
        if sort_bookings_order == 'desc':
            bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        else:
            bookings = Booking.query.order_by(Booking.created_at).all()
    
    return render_template(
        'admin_dashboard.html', 
        username=session['username'], 
        rooms=rooms, 
        bookings=bookings,
        sort_rooms_by=sort_rooms_by,
        sort_rooms_order=sort_rooms_order,
        sort_bookings_by=sort_bookings_by,
        sort_bookings_order=sort_bookings_order
    )

@app.route('/rooms')
def rooms():
    return render_template('room.html')

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if 'user_id' not in session:
        flash('Please login to book a room', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        room_id = request.form['room_id']
        check_in = request.form['check_in']
        check_out = request.form['check_out']
        guests = request.form['guests']
        
        # Convert string dates to date objects
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        
        # Validate dates
        if check_in_date < datetime.now().date():
            flash('Check-in date cannot be in the past!', 'danger')
            return redirect(url_for('booking'))
        
        if check_out_date <= check_in_date:
            flash('Check-out date must be after check-in date!', 'danger')
            return redirect(url_for('booking'))
        
        # Check if room is available for the selected dates
        room = Room.query.get(room_id)
        if not room or not room.availability:
            flash('Selected room is not available!', 'danger')
            return redirect(url_for('booking'))
        
        # Create booking
        new_booking = Booking(
            user_id=session['user_id'],
            room_id=room_id,
            check_in=check_in_date,
            check_out=check_out_date,
            guests=guests,
            status='pending'
        )
        
        # Mark room as unavailable
        room.availability = False
        
        db.session.add(new_booking)
        db.session.commit()
        
        flash('Booking submitted successfully! Awaiting confirmation.', 'success')
        return redirect(url_for('user_dashboard'))
    
    # Get available rooms for booking form
    available_rooms = Room.query.filter_by(availability=True).all()
    
    return render_template('booking.html', rooms=available_rooms)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/forgot_password')
def forgot_password():
    return render_template('forgotpassword.html')

@app.route('/reset_password')
def reset_password():
    return render_template('resetpassword.html')

@app.route('/add_room', methods=['GET', 'POST'])
def add_room():
    if 'user_id' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        room_type = request.form['room_type']
        price = float(request.form['price'])
        description = request.form['description']
        amenity = request.form['amenity']
        
        new_room = Room(
            room_type=room_type, 
            price=price, 
            description=description, 
            amenity=amenity
        )
        
        db.session.add(new_room)
        db.session.commit()
        
        flash('Room added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_room.html')

@app.route('/cancel_booking/<int:booking_id>')
def cancel_booking(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only cancel their own bookings
    if booking.user_id == session['user_id'] or session['is_admin']:
        booking.status = 'cancelled'
        
        # Make the room available again
        room = Room.query.get(booking.room_id)
        room.availability = True
        
        db.session.commit()
        flash('Booking cancelled successfully!', 'success')
    else:
        flash('You are not authorized to cancel this booking!', 'danger')
    
    if session['is_admin']:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))

@app.route('/confirm_booking/<int:booking_id>')
def confirm_booking(booking_id):
    if 'user_id' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    
    booking = Booking.query.get_or_404(booking_id)
    booking.status = 'confirmed'
    db.session.commit()
    
    flash('Booking confirmed successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_booking/<int:booking_id>')
def delete_booking(booking_id):
    if 'user_id' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    
    booking = Booking.query.get_or_404(booking_id)
    
    # Make room available again
    room = Room.query.get(booking.room_id)
    room.availability = True
    
    db.session.delete(booking)
    db.session.commit()
    
    flash('Booking deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_room/<int:room_id>')
def delete_room(room_id):
    if 'user_id' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    
    room = Room.query.get_or_404(room_id)
    
    # Check if there are active bookings for this room
    active_bookings = Booking.query.filter_by(room_id=room_id).filter(Booking.status != 'cancelled').all()
    
    if active_bookings:
        flash('Cannot delete room with active bookings!', 'danger')
    else:
        db.session.delete(room)
        db.session.commit()
        flash('Room deleted successfully!', 'success')
    
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
