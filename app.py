from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User
import os
import  io
import redis
from PIL import  Image, ImageDraw, ImageFont
from flask import Response
from sqlalchemy import or_


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

@login_manager.unauthorized_handler
def unauthorized():
    flash('You must be logged in to access this page.', 'error')
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    return session.query(User).get(user_id)

#For Admins

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
        return redirect(url_for('admin'))

    return render_template('newrestaurant.html')

@app.route('/admin/<int:restaurant_id>/delete/', methods=['POST'])
@login_required
def delete(restaurant_id):

    try:
        itemToDelete = session.query(Restaurant).filter_by(id=restaurant_id).one_or_none()
        if not itemToDelete:
            flash("Restaurant not found.", 'error')
            return redirect(url_for('admin'))

        session.delete(itemToDelete)
        session.commit()
        flash("Restaurant Deleted!", 'success')
    except Exception as e:
        flash(f"An error occurred: {e}", 'error')
    return redirect(url_for('admin'))

from PIL import Image, ImageDraw, ImageFont

def generate_captcha_image(captcha_code):
    # Create a blank image with white background
    width, height = 120, 50
    image = Image.new('RGB', (width, height), color='white')

    # Initialize drawing context
    draw = ImageDraw.Draw(image)


    # Neon color for the text
    neon_color = (0, 0, 255)  # Neon blue
    glow_color = (255, 105, 180,80)  # Semi-transparent green for glow effect
    glow_color2 = (0, 255, 0 , 80)
    # Set font (you can customize the font)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        font = ImageFont.load_default()

    # Calculate the text size using textbbox (recommended method in Pillow 8.0+)
    text_bbox = draw.textbbox((0, 0), captcha_code, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Calculate position to center the text
    position = ((width - text_width) // 2, (height - text_height) // 2)

    # Add the CAPTCHA text to the image
     # Create a glowing effect by drawing shadows
    for offset in range(3, 0, -1):  # Draw shadow around the text
        draw.text((position[0] + offset, position[1] + offset), captcha_code, fill=glow_color, font=font)
    # for offset in range(4, 0, -1):  # Draw shadow around the text
    #     draw.text((position[0] + offset, position[1] + offset), captcha_code, fill=glow_color2, font=font)

    # Now draw the actual text on top
    draw.text(position, captcha_code, fill=neon_color, font=font)
    # Optionally, you can add random noise or lines for additional security

    # Return the image
    return image


    
def generate_captcha(length=4, use_digits=True, use_letters=True, use_both=True):
    # Define possible characters for CAPTCHA
    if use_both:
        characters = string.ascii_letters + string.digits  # Both letters and digits
    elif use_digits:
        characters = string.digits  # Only digits
    elif use_letters:
        characters = string.ascii_letters  # Only letters
    else:
        characters = string.digits  # Default to digits if no valid choice
    
    # Generate the CAPTCHA by randomly selecting characters
    captcha_code = ''.join(random.choice(characters) for _ in range(length))
    
    return captcha_code.upper()

@app.route('/captcha_image/')
def captcha_image():
    captcha_code = generate_captcha()
    
    # Save the CAPTCHA text to session
    session['captcha_solution'] = captcha_code
    
    # Generate CAPTCHA image
    image = generate_captcha_image(captcha_code)
    
    # Convert the image to a byte stream
    img_io = io.BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)
    
    # Return the image as a response with the correct content type
    return Response(img_io, mimetype='image/png')

@app.route('/refresh_captcha', methods=['GET'])
def refresh_captcha():
    captcha_code = generate_captcha()
    session['captcha_solution'] = captcha_code  # Store the new solution in the session
    # Return the new CAPTCHA code or image URL (adjust based on your implementation)
    return render_template('login.html', captcha=captcha_code)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    
    # if 'captcha_solution' not in session or request.args.get('refresh_captcha'):
    #     captcha_code = generate_captcha()
    #     session['captcha_solution'] = captcha_code

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        captcha_answer = request.form['captcha']
        # refresh_captcha = request.method=='GET'? True:False

        # Check CAPTCHA solution
        if captcha_answer != session.get('captcha_solution'):
            flash('Invalid CAPTCHA ! Please try again.', 'error')
            captcha_code = generate_captcha()  # Generate new CAPTCHA if answer is wrong
            session['captcha_solution'] = captcha_code
            return render_template('login.html', captcha=captcha_code)


        # Clear CAPTCHA solution after successful validation
        session.pop('captcha_solution', None)

        # Validate username and password
        user = db_session.query(User).filter_by(username=username).first()
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


@app.route('/admin/<int:restaurant_id>/menu/new/', methods=['GET', 'POST'])
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
@app.route('/admin/<int:restaurant_id>/<int:menu_id>/edit', methods=['GET', 'POST'])
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

@app.route('/admin/<int:restaurant_id>/<int:menu_id>/delete', methods=['GET', 'POST'])
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


# For Users
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/user_login/', methods=['GET', 'POST'])
def user_login():
    
    if 'captcha_solution' not in session or request.args.get('refresh_captcha'):
        captcha_code = generate_captcha()
        session['captcha_solution'] = captcha_code

    if request.method == 'POST':
    
        username = request.form['username']
        password = request.form['password']
        
        captcha_answer = request.form['captcha']

        # Check CAPTCHA solution
        if captcha_answer != session.get('captcha_solution'):
            flash('Invalid CAPTCHA ! Please try again.', 'error')
            captcha_code = generate_captcha()  # Generate new CAPTCHA if answer is wrong
            session['captcha_solution'] = captcha_code
            return render_template('login.html', captcha=captcha_code)


        # Clear CAPTCHA solution after successful validation
        session.pop('captcha_solution', None)

        # Validate username and password
        user = db_session.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            
            login_user(user)
            flash(f'Welcome {username}!', 'success')
            return redirect(url_for('restaurants'))
        else:
            flash('Invalid username or password', 'error')

    captcha_code = session.get('captcha_solution', None)
    return render_template('user_login.html', captcha=captcha_code)





@app.route('/restaurants/')
def restaurants():
    restaurants = session.query(Restaurant).all()
    return render_template('restaurants.html', restaurants=restaurants)


@app.route('/search', methods=['GET'])
def search_restaurant():
    query = request.args.get('query', '').strip()  # Get the search term
    
    if query:
        # Search logic
        results = (
            db_session.query(Restaurant)
            .filter(Restaurant.name.ilike(f"%{query}%"))
            .all()
        )
        if not results:
            flash("No results were Found !",'error')
            return redirect(url_for('restaurants'))
    else:
        # Show all restaurants if no query
        results = db_session.query(Restaurant).all()

    # Pass the query and results to the template
    return render_template('restaurants.html', query=query, restaurants=results)

@app.route('/restaurants/JSON/')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(RestaurantNames = [i.serialize() for i in restaurants])

@app.route('/restaurants/<int:restaurant_id>/')
def UserMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()
    return render_template('user_menu.html', restaurant=restaurant, items=items)

@app.route('/restaurants/<int:restaurant_id>/usermenu/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()
    return render_template('menu.html', restaurant=restaurant, items=items)

@app.route('/restaurants/<int:restaurant_id>/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()
    return jsonify(MenuItems = [i.serialize for i in items])
