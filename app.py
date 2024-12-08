from flask import Flask, request, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import pandas as pd
from model import analyze_reviews 
from flask import send_from_directory


app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Initialize the database
with app.app_context():
    db.create_all()

# Route for the landing page
@app.route('/')
def landing_page():
    return render_template('index.html')

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle login logic here
        # For now, redirect to a placeholder dashboard
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

# Helper function to check allowed file extensions
# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route: Dashboard (File Upload)
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        # Check if a file is included in the request
        if 'file' not in request.files:
            flash('No file uploaded. Please select a file.')
            return redirect(request.url)

        file = request.files['file']

        # Check if a file is selected
        if file.filename == '':
            flash('No file selected. Please choose a file to upload.')
            return redirect(request.url)

        # Validate the file type
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Save the file
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)

            # Process the uploaded file
            try:
                # Load the dataset
                dataset = pd.read_csv(file_path, sep=",")  # Assuming CSV is comma-separated
                dataset.columns = dataset.columns.str.strip().str.lower()  # Normalize column names

                # Required columns for processing
                required_columns = {'review_id', 'product_id', 'review_body', 'product_title'}
                if not required_columns.issubset(dataset.columns):
                    missing_columns = required_columns - set(dataset.columns)
                    flash(f"The uploaded file is missing required columns: {', '.join(missing_columns)}")
                    return redirect(request.url)

                # Set index to 'review_id'
                dataset.set_index("review_id", inplace=True)

                # Analyze reviews and detect fake reviews
                remove_reviews = analyze_reviews(dataset)

                # Mark fake reviews in the dataset
                dataset['fake_review'] = dataset.index.isin(remove_reviews)

                # Save results to a new file
                result_file = os.path.join(app.config['UPLOAD_FOLDER'], f"results_{filename}")
                dataset.to_csv(result_file)

                # Redirect to the results page
                return redirect(url_for('results', result_file=f"results_{filename}"))
            except Exception as e:
                # Handle any errors during processing
                flash(f"Error processing file: {e}")
                return redirect(request.url)
        else:
            flash('Invalid file format. Only CSV files are allowed.')
            return redirect(request.url)

    # Render the upload form if GET request
    return render_template('dashboard.html')

# Route: Results
@app.route('/results')
def results():
    result_file = request.args.get('result_file')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], result_file)

    try:
        # Load the results file
        data = pd.read_csv(file_path)

        # Render the table in HTML
        return render_template(
            'results.html',
            tables=data.to_html(classes='table table-striped', index=False),
            filename=result_file
        )
    except Exception as e:
        return f"Error loading results: {e}"



# Route for downloading the results file
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
