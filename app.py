from flask import Flask, render_template, request, redirect, url_for, flash ,session
import pyodbc
import tensorflow as tf
from tensorflow import keras
from keras.models import load_model
import pandas as pd
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from flask_mail import Mail, Message
import random
import string

app = Flask(__name__)

app.secret_key = '0000'
# app.register_blueprint(forgot_password_bp, url_prefix='/')

model = load_model('model.h5')

max_words = 1000  # Set the maximum number of words for text processing
maxlen = 30000 

tokenizer = Tokenizer(num_words=max_words, oov_token="<OOV>")

# กำหนดการเชื่อมต่อกับ SQL Server
connection_string = 'DRIVER={SQL Server};' \
                    'SERVER=DESKTOP-UJ5T3UB\SQLEXPRESS;' \
                    'DATABASE=Jobbkk;' \
                    'Trusted_Connection=yes;'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'tester27531@gmail.com'
app.config['MAIL_PASSWORD'] = 'uzyt cfch xhgs jfnr'
app.config['MAIL_DEFAULT_SENDER'] = 'tester27531@gmail.com'

@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        # Retrieve the submitted username and password from the form
        username = request.form.get('username')
        password = request.form.get('password')

        # Connect to the SQL Server database
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Execute a query to check if the provided username and password match a record in the UserTable
        cursor.execute('SELECT * FROM UserTable WHERE Username=? AND Password=?', (username, password))
        user = cursor.fetchone()

        # Close the database connection
        conn.close()

        if user:
            session['logged_in'] = True
            session['username'] = username
            # If a matching user is found, redirect to the '/home' page
            return redirect('/predict')
        else:
            # If no matching user is found, display an error message
            error_message = 'Invalid username or password. Please try again.'
            return render_template('index.html', error_message=error_message)

    # If the request method is GET, simply render the index.html template
    return render_template('index.html')

@app.route('/Register', methods=['GET', 'POST'])
def Register():
    # Initialize form_data with empty values
    form_data = {'username': '', 'password': '', 'confirm_password': '', 'name': '', 'surname': '', 'phone': '', 'address': ''}

    if request.method == 'POST':
        # Retrieve the submitted data from the form
        form_data['username'] = request.form.get('username')
        form_data['password'] = request.form.get('password')
        form_data['confirm_password'] = request.form.get('confirm_password')
        form_data['name'] = request.form.get('name')
        form_data['surname'] = request.form.get('surname')
        form_data['phone'] = request.form.get('phone')
        form_data['address'] = request.form.get('address')

        if len(form_data['phone']) != 10:
            error_message = 'Please insert your phone number.'
        elif form_data['password'] == '' or form_data['confirm_password'] == '':
            error_message = 'Please insert both passwords.'
        elif len(form_data['password']) < 8:
            error_message = 'Password is too short.'
        elif form_data['password'] != form_data['confirm_password']:
            error_message = 'Passwords do not match. Please try again.'
        else:
            # Connect to the SQL Server database
            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()

            # Check if the username already exists in the UserTable
            cursor.execute('SELECT * FROM UserTable WHERE Username=?', (form_data['username'],))
            existing_user = cursor.fetchone()

            if existing_user:
                error_message = 'Username already exists. Please choose a different username.'
            else:
                # Insert the new user into the UserTable
                cursor.execute('INSERT INTO UserTable (username, password, name, surname, address, phone) VALUES (?, ?, ?, ?, ?, ?)', (form_data['username'], form_data['password'], form_data['name'], form_data['surname'], form_data['address'], form_data['phone']))
                conn.commit()

                # Close the database connection
                conn.close()

                session['logged_in'] = True
                session['username'] = form_data['username']

                # If a matching user is found, redirect to the '/predict' page
                return redirect(url_for('predict'))

        # If conditions are not met, render the register.html template with the error message and form_data
        return render_template('register.html', error_message=error_message, form_data=form_data)

    # If the request method is GET, simply render the register.html template with form_data
    return render_template('register.html', form_data=form_data)

@app.route('/predict', methods=['GET'])
def predict():
    # Get the search query from the user input
    search_query = request.args.get('search_query', '').strip()

    # Fetch data from the JobTable in the SQL Server database
    query = "SELECT Position, Company FROM JobTable"
    
    conn = pyodbc.connect(connection_string)
    data = pd.read_sql_query(query, conn)
    conn.close()

    position_texts = data['Position'].astype(str).tolist()

    if not position_texts:
        # Handle the case where no data is found for the specified position
        prediction = "No data found for the specified position."
    else:
        if search_query:
            # Filter positions based on the search query
            filtered_positions = [position for position in position_texts if search_query.lower() in position.lower()]

            filtered_companies = data[data['Position'].isin(filtered_positions)]['Company'].tolist()

            if not filtered_positions:
                # Handle the case where no positions match the search query
                prediction = f"No matching positions found for '{search_query}'."
            else:
                # Tokenize and convert text data to sequences
                tokenizer.fit_on_texts(filtered_positions)
                sequences = tokenizer.texts_to_sequences(filtered_positions)

                # Pad sequences to have consistent length
                padded_sequences = pad_sequences(sequences, maxlen=maxlen)

                # Predict using the model
                predictions = model.predict(padded_sequences)

                # Extract the predicted scores for each position
                scores = predictions.flatten()

                # Combine positions with corresponding scores
                position_scores = list(zip(filtered_positions, filtered_companies, scores))

                # Sort positions based on predicted scores
                sorted_positions = sorted(position_scores, key=lambda x: x[2], reverse=True)

                # Select the top recommendations (adjust 'top_n' based on your preference)
                top_n = 10
                recommended_positions = sorted_positions[:top_n]

                # Format recommendations for display
                recommendation_text = "\n".join([f"{position} at {company}: {score}" for position, company, score in recommended_positions])

                # Set the recommendation text
                prediction = recommendation_text
        else:
            # If no search query, use all positions
            # (You can adjust this part based on your application logic)
            prediction = "Please enter a search query to get recommendations."

    # Send data, search query, and prediction to the HTML template
    return render_template('predict.html', prediction=prediction, search_query=search_query)

mail = Mail(app)
# In-memory storage for password reset tokens (you should use a database in production)
password_reset_tokens = {}

def execute_sql_query(query, params=None):
    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Check if the username already exists in the UserTable
        cursor.execute('SELECT * FROM UserTable WHERE Username=?', (email,))
        existing_user = cursor.fetchone()
        # Check if the email exists in your user database
        # If yes, generate a random token and store it
        if existing_user:
            user_id = existing_user[0]
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            password_reset_tokens[token] = user_id

            # Send email with reset link
            reset_link = url_for('reset_password', token=token, _external=True)
            send_reset_email(email, reset_link)

            flash('An email with instructions to reset your password has been sent.')
            return redirect(url_for('forgot_password'))

        else:
            flash('Email address not found.')

    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if token in password_reset_tokens:
        if request.method == 'POST':
            new_password = request.form.get('new_password')
            
            # Update the user's password in your database using a SQL query
            user_id = password_reset_tokens[token]
            update_query = "UPDATE UserTable SET password = ? WHERE userid = ?"
            execute_sql_query(update_query, (new_password, user_id))
            
            flash('Your password has been successfully reset.')
            del password_reset_tokens[token]
            return redirect(url_for('index'))

        return render_template('reset_password.html', token=token)

    else:
        flash('Invalid or expired token.')
        return redirect(url_for('forgot_password'))

def send_reset_email(email, reset_link):
    subject = 'Password Reset Request'
    body = f'Click the following link to reset your password: {reset_link}'
    msg = Message(subject, recipients=[email], body=body)
    mail.send(msg)

@app.route('/profile')
def profile():
    if not session.get('logged_in'):
        return redirect(url_for('index'))

    # Fetch user information from the database
    user = get_user_information(session['username'])

    return render_template('profile.html', user=user)

def authenticate_user(username, password):
    # Connect to the database and authenticate the user
    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            # Replace 'UserTable' with your actual table name
            query = '''
            SELECT COUNT(*) 
            FROM UserTable 
            WHERE Username=? AND Password=?
            '''
            cursor.execute(query, (username, password))
            result = cursor.fetchone()

    # Return True if the username and password match, False otherwise
    return result[0] == 1 if result else False

def get_user_information(username):
    # Connect to the database and fetch user information
    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            # Replace 'UserTable' with your actual table name
            cursor.execute('SELECT name, surname, phone, address FROM UserTable WHERE username=?', (username,))
            user_data = cursor.fetchone()

    # Return user information as a dictionary
    if user_data:
        user = {
            'name': user_data[0],
            'lastname': user_data[1],
            'phone': user_data[2],
            'address': user_data[3],
        }
        return user
    else:
        return None
    
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if not session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Get the new username and password from the form
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        lastname = request.form.get('lastname')
        phone = request.form.get('phone')
        address = request.form.get('address')

        # Validate and update the user information
        if username and password and name and lastname and phone and address:
            # Check if the old password is correct
            if authenticate_user(session['username'], password):
                # Update the session information (optional)
                session['username'] = username

                # Update the user information in the database or your data store
                update_user_information(session['username'], password, name, lastname, phone, address)

                flash('User information updated successfully.')
            else:
                flash('password is incorrect.')
        else:
            flash('Please provide all required information.')

    user = get_user_information(session['username'])
    return render_template('profile.html', user=user)

def update_user_information(username, password, name, lastname, phone, address):
    # Connect to the database and update user information
    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            # Replace 'UserTable' with your actual table name
            update_query = '''
            UPDATE UserTable 
            SET Password=?, Name=?, surname=?, Phone=?, Address=? 
            WHERE Username=?
            '''
            cursor.execute(update_query, (password, name, lastname, phone, address, username))
            conn.commit()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
    
if __name__ == '__main__':
    app.run(debug=True)


