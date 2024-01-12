from flask import Flask, render_template, request, redirect, url_for
import pyodbc
import tensorflow as tf
from tensorflow import keras
from keras.models import load_model
import pandas as pd
import numpy as np
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences


app = Flask(__name__)


model = load_model('model.h5')

# กำหนดการเชื่อมต่อกับ SQL Server
connection_string = 'DRIVER={SQL Server};' \
                    'SERVER=DESKTOP-UJ5T3UB\SQLEXPRESS;' \
                    'DATABASE=Jobbkk;' \
                    'Trusted_Connection=yes;'

max_words = 1000  # Set the maximum number of words for text processing

tokenizer = Tokenizer(num_words=max_words, oov_token="<OOV>")

@app.route('/home', methods=['GET'])
def home():
    # Create a connection and cursor
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    # Fetch data from SQL Server
    cursor.execute('SELECT * FROM JobTable')
    data = cursor.fetchall()

    # Close the connection
    conn.close()

    # Get the search query from the form
    search_query = request.args.get('position_name')

    # Send data and search query to the HTML template
    return render_template('home.html', data=data, search_query=search_query)

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
            # If a matching user is found, redirect to the '/home' page
            return redirect('/home')
        else:
            # If no matching user is found, display an error message
            error_message = 'Invalid username or password. Please try again.'
            return render_template('index.html', error_message=error_message)

    # If the request method is GET, simply render the index.html template
    return render_template('index.html')

@app.route('/Register', methods=['GET','POST'])
def Register():
    if request.method == 'POST':
        # Retrieve the submitted username, password, and confirm_password from the form
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password == '' or confirm_password == '':
            error_message = 'Please insert both passwords.'
            return render_template('register.html', error_message=error_message)
 
        # Check if passwords match
        if password != confirm_password:
            error_message = 'Passwords do not match. Please try again.'
            return render_template('register.html', error_message=error_message)

        # Connect to the SQL Server database
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Check if the username already exists in the UserTable
        cursor.execute('SELECT * FROM UserTable WHERE Username=?', (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            error_message = 'Username already exists. Please choose a different username.'
            conn.close()
            return render_template('register.html', error_message=error_message)

        # Insert the new user into the UserTable
        cursor.execute('INSERT INTO UserTable (Username, Password) VALUES (?, ?)', (username, password))
        conn.commit()

        # Close the database connection
        conn.close()

        # Redirect to the login page after successful registration
        return redirect(url_for('index'))

    # If the request method is GET, simply render the register.html template
    return render_template('register.html')


@app.route('/predict', methods=['GET'])
def predict():
    # Create a connection and cursor
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    # Fetch data from SQL Server for the specified position
    cursor.execute('SELECT position, rating FROM JobTable')
    job_data = cursor.fetchall()

    # Close the connection
    conn.close()

    if not job_data:
        # Handle the case where no data is found
        prediction = "No data found in the JobTable."
    else:
        # Extract the text data and ratings from the fetched records
        positions = [row[0] if row[0] is not None else "" for row in job_data]
        ratings = [row[1] for row in job_data]

        # Tokenize and convert text data to sequences
        tokenizer.fit_on_texts(positions)
        sequences = tokenizer.texts_to_sequences(positions)

        # Pad sequences to have consistent length
        padded_sequences = pad_sequences(sequences)

        # Predict using the model (assuming 'model' is loaded)
        prediction = model.predict(padded_sequences)

        # Combine positions with corresponding ratings and predicted scores
        result = list(zip(positions, ratings, prediction.flatten()))

    # Send data, search query, and prediction to the HTML template
    return render_template('predict.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)

# if __name__ == '__main__':
#     # Connect to the SQL Server database
#     conn = pyodbc.connect(connection_string)
#     cursor = conn.cursor()

#     try:
#         # Execute the DELETE_JOB stored procedure
#         cursor.execute('EXEC DELETE_JOB;')
#         conn.commit()
#         print("DELETE_JOB executed successfully.")
#     except Exception as e:
#         print(f"Error executing DELETE_JOB: {str(e)}")
#     finally:
#         # Close the database connection
#         conn.close()

#     # Run the Flask application
#     app.run(debug=True)


