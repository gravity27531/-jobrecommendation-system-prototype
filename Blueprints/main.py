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

data = pd.read_csv('30000 .csv')

# Assuming 'position' is the name of the text column
position_texts = data['Name'].astype(str).tolist()

max_words = 1000  # Set the maximum number of words for text processing
maxlen = 30000 

tokenizer = Tokenizer(num_words=max_words, oov_token="<OOV>")

# กำหนดการเชื่อมต่อกับ SQL Server
connection_string = 'DRIVER={SQL Server};' \
                    'SERVER=DESKTOP-UJ5T3UB\SQLEXPRESS;' \
                    'DATABASE=Jobbkk;' \
                    'Trusted_Connection=yes;'

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
    # Get the search query from the user input
    search_query = request.args.get('search_query', '').strip()

    if not position_texts:
        # Handle the case where no data is found for the specified position
        prediction = "No data found for the specified position."
    else:
        if search_query:
            # Filter positions based on the search query
            filtered_positions = [position for position in position_texts if search_query.lower() in position.lower()]

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
                position_scores = list(zip(filtered_positions, scores))

                # Sort positions based on predicted scores
                sorted_positions = sorted(position_scores, key=lambda x: x[1], reverse=True)

                # Select the top recommendations (adjust 'top_n' based on your preference)
                top_n = 10
                recommended_positions = sorted_positions[:top_n]

                # Format recommendations for display
                recommendation_text = "\n".join([f"{position}: {score}" for position, score in recommended_positions])

                # Set the recommendation text
                prediction = recommendation_text
        else:
            # If no search query, use all positions
            # (You can adjust this part based on your application logic)
            prediction = "Please enter a search query to get recommendations."

    # Send data, search query, and prediction to the HTML template
    return render_template('predict.html', prediction=prediction, search_query=search_query)


if __name__ == '__main__':
    app.run(debug=True)




