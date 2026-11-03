import os
import subprocess
from flask import Flask, render_template, url_for, redirect, flash, request, jsonify, abort, Response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from datetime import datetime
import time
import urllib.parse
# ------------------------
# App Initialization & Config
# ------------------------
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'database.db')
app.config['SECRET_KEY'] = 'thisisasecretkey'
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'profile_pics')

# ------------------------
# Extensions & User Loader
# ------------------------
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------
# Database Model
# ------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    full_name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(80), nullable=False)
    profile_pic = db.Column(db.String(120), nullable=False, default='default.jpg')
    join_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    bio = db.Column(db.String(140), nullable=True, default="This user has not set a bio yet.")

# ------------------------
# Main Application Routes
# ------------------------
@app.route('/')
def landing(): return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('feed'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and bcrypt.check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('feed'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('feed'))
    if request.method == 'POST':
        hashed_password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        new_user = User(username=request.form.get('username'), full_name=request.form.get('full_name'), password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/feed')
@login_required
def feed(): return render_template('feed.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'full_name' in request.form or 'bio' in request.form:
            current_user.full_name = request.form.get('full_name')
            current_user.bio = request.form.get('bio')
            db.session.commit()
            flash('Your profile information has been updated!', 'success')
            return redirect(url_for('profile'))
    return render_template('profile.html', user=current_user)

@app.route('/upload_temp_image', methods=['POST'])
@login_required
def upload_temp_image():
    if 'temp_image' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    file = request.files['temp_image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    if file:
        filename = f"temp_{int(time.time())}_{secure_filename(file.filename)}"
        filepath = os.path.join(instance_path, filename)
        file.save(filepath)
        return jsonify({'success': True, 'filename': filename})
    return jsonify({'success': False, 'error': 'File upload failed'})

@app.route('/crop_and_save', methods=['POST'])
@login_required
def crop_and_save():
    data = request.get_json()
    temp_filename = data.get('filename')
    
    x = urllib.parse.unquote(data.get('x'))
    y = urllib.parse.unquote(data.get('y'))
    width = urllib.parse.unquote(data.get('width'))
    height =urllib.parse.unquote(data.get('height'))
    print(x)

    if not temp_filename:
        return jsonify({'success': False, 'error': 'Missing temporary filename.'})

    temp_input_path = os.path.join(instance_path, temp_filename)
    
    final_filename = f"cropped_{temp_filename}"
    temp_output_path = os.path.join(instance_path, f"out_{final_filename}")

    crop_binary_path = os.path.join(basedir, 'static', 'profile_pics', 'crop_image')
    subproc_env = os.environ.copy()
    subproc_env['LD_LIBRARY_PATH'] = '/usr/local/lib'
    
    inputs = [temp_input_path, temp_output_path, str(x), str(y), str(width), str(height)]
    stderr = 0
    try:
        proc = subprocess.Popen([crop_binary_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=subproc_env)
        stdout, stderr = proc.communicate('\n'.join(inputs) + '\n')

        if proc.returncode != 0:
            raise Exception(f"Crop binary failed: {stderr}")

        final_save_path = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)
        os.rename(temp_output_path, final_save_path)

        current_user.profile_pic = final_filename
        db.session.commit()
        
        flash('Profile picture updated successfully!', 'success')
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': f'{crop_binary_path}  '+ str(stderr) +' ' + str(stdout)})
    finally:
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)

# === INTENTIONALLY VULNERABLE FILE SERVING ROUTE FOR LFI LAB ===
@app.route('/serve_file')
def serve_file():
    filename = request.args.get('filename')
    if not filename:
        abort(404)

    # The flag lives in this process's environment (RCTF_FLAG) — keep /proc
    # out of reach so the LFI alone cannot read it.
    if '/proc' in filename:
        abort(404)

    # DANGEROUS: Determine base path but do not sanitize 'filename'
    base_path = instance_path if filename.startswith('temp_') else app.static_folder
    filepath = os.path.join(base_path, filename)
    
    try:
        # DANGEROUS: Open the constructed path in binary mode.
        with open(filepath, 'rb') as f:
            content = f.read()
        return Response(content, mimetype='application/octet-stream')
    except FileNotFoundError:
        abort(404)
    except Exception as e:
        return f"An error occurred: {e}", 500
# =========================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='0.0.0.0')
