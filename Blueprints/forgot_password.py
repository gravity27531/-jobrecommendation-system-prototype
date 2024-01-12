from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash
import random
import pyodbc
import string
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'your_secret_key'

forgot_password_bp = Blueprint('forgot_password', __name__)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'tester27531@gmail.com'
app.config['MAIL_PASSWORD'] = 'uzyt cfch xhgs jfnr'
app.config['MAIL_DEFAULT_SENDER'] = 'tester27531@gmail.com'

mail = Mail(app)

# In-memory storage for password reset tokens (you should use a database in production)
password_reset_tokens = {}

connection_string = 'DRIVER={SQL Server};' \
                    'SERVER=DESKTOP-UJ5T3UB\SQLEXPRESS;' \
                    'DATABASE=Jobbkk;' \
                    'Trusted_Connection=yes;'

def execute_sql_query(query, params=None):
    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()

@forgot_password_bp.route('/forgot-password', methods=['GET', 'POST'])
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
            return redirect(url_for('forgot_password'))

        return render_template('reset_password.html', token=token)

    else:
        flash('Invalid or expired token.')
        return redirect(url_for('forgot_password'))

def send_reset_email(email, reset_link):
    subject = 'Password Reset Request'
    body = f'Click the following link to reset your password: {reset_link}'
    msg = Message(subject, recipients=[email], body=body)
    mail.send(msg)

if __name__ == '__main__':
    app.run(debug=True)
