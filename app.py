from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User
import os

app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(24)

# Database setup
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)

@app.route('/')
def home():
    return render_template('index.html')

@login_manager.unauthorized_handler
def unauthorized():
    flash('You must be logged in to access this page.', 'error')
    return redirect(url_for('login'))

@app.route('/restaurants/')
def restaurants():
    restaurants = session.query(Restaurant).all()
    return render_template('restaurants.html', restaurants=restaurants)

@app.route('/restaurants/<int:restaurant_id>/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()
    return jsonify(MenuItems = [i.serialize for i in items])

@login_manager.user_loader
def load_user(user_id):
    return session.query(User).get(user_id)

@app.route('/admin/')
@login_required
def admin():
    restaurants = session.query(Restaurant).all()
    return render_template('admin_restaurants.html', restaurants=restaurants)

@app.route('/restaurants/new/', methods=['GET', 'POST'])
@login_required

def newRestaurant():
    if request.method == 'POST':
        name = request.form.get('name')
        restaurant1 = Restaurant(name=name)
        session.add(restaurant1)
        session.commit()
        return redirect(url_for('restaurants'))

    return render_template('newrestaurant.html')

@app.route('/restaurants/JSON/')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(RestaurantNames = [i.serialize() for i in restaurants])

@app.route('/restaurants/<int:restaurant_id>/')
def UserMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()
    return render_template('user_menu.html', restaurant=restaurant, items=items)

@app.route('/restaurants/<int:restaurant_id>/menu/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()
    return render_template('menu.html', restaurant=restaurant, items=items)

@login_manager.user_loader
def load_user(user_id):
    return session.query(User).get(user_id)

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = session.query(User).filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('restaurants'))

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if username already exists
        if session.query(User).filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))

        # Hash the password before saving
        hashed_password = generate_password_hash(password)

        new_user = User(username=username, password=hashed_password, role='user')
        session.add(new_user)
        session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/restaurants/<int:restaurant_id>/menu/new/', methods=['GET', 'POST'])
@login_required
def newMenuItem(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')

        if not name or not price:
            flash('Name and Price are required fields!', 'error')
            return redirect(url_for('newMenuItem', restaurant_id=restaurant_id))

        try:
            price = float(price)
        except ValueError:
            flash('Invalid price value. Please enter a valid number.', 'error')
            return redirect(url_for('newMenuItem', restaurant_id=restaurant_id))

        new_item = MenuItem(
            name=name,
            description=description,
            price=price,
            restaurant_id=restaurant.id
        )

        # Add to session and commit to the database
        session.add(new_item)
        session.commit()
        flash('New menu item added successfully!', 'success')
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant.id))

    return render_template('newmenuitem.html', restaurant=restaurant)

# Protect routes requiring login
@app.route('/restaurants/<int:restaurant_id>/<int:menu_id>/edit', methods=['GET', 'POST'])
@login_required
def editMenuItem(restaurant_id, menu_id):    
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        session.add(editedItem)
        session.commit()
        flash('Menu item edited successfully!', 'success')
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('editmenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=editedItem)

@app.route('/restaurants/<int:restaurant_id>/<int:menu_id>/delete', methods=['GET', 'POST'])
@login_required
def deleteMenuItem(restaurant_id, menu_id):
    itemToDelete = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("Item Deleted!", 'success')
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('deletemenuitem.html', item=itemToDelete)
