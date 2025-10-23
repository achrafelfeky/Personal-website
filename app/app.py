from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from flask_caching import Cache
from dotenv import load_dotenv
import os


load_dotenv()
app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


cache = Cache(config={'CACHE_TYPE': 'SimpleCache'}) 
cache.init_app(app)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin.login'


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
project_bp = Blueprint('projects', __name__, url_prefix='/projects')


ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    tech_stack = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=True)      
    live_link = db.Column(db.String(120), nullable=True)
    githup = db.Column(db.String(120), nullable=True)


class User(UserMixin):
    id = 1
    username = ADMIN_USERNAME
    role = "admin"

@login_manager.user_loader
def load_user(user_id):
    if int(user_id) == 1:
        return User()
    return None


def admin_only(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("هذه الصفحة للمشرف فقط", "danger")
            return redirect(url_for('admin.login'))  
        return func(*args, **kwargs)
    return decorated_view


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            user = User()
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        else:
            flash("خطأ في اسم المستخدم أو كلمة المرور", "danger")
    return render_template('login.html')


@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح", "success")
    return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
@login_required
@admin_only  
@cache.cached(timeout=60, key_prefix='dashboard_page') 
def dashboard():
    total_project = Project.query.count()
    projects = Project.query.all()
    return render_template('dashboard.html', total_project=total_project, projects=projects)


@project_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_only
def add_project():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        tech_stack = request.form['tech_stack']
        githup = request.form['githup']
        live_link = request.form['live_link']
        image_url = request.form['image_url']

        new_project = Project(
            title=title, description=description, tech_stack=tech_stack,
            githup=githup, live_link=live_link, image_url=image_url
        )
        db.session.add(new_project)
        db.session.commit()
        flash('تم إضافة المشروع بنجاح', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('add_project.html')


@project_bp.route('/edit/<int:project_id>', methods=['GET', 'POST'])
@login_required
@admin_only
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if request.method == 'POST':
        project.title = request.form['title']
        project.description = request.form['description']
        project.tech_stack = request.form['tech_stack']
        project.githup = request.form['githup']
        project.live_link = request.form['live_link']
        project.image_url = request.form['image_url']
        db.session.commit()
        flash('تم تعديل المشروع', 'info')
        return redirect(url_for('admin.dashboard'))
    return render_template('edit_project.html', project=project)


@project_bp.route('/delete/<int:project_id>', methods=['POST'])
@login_required
@admin_only
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash("تم حذف المشروع ", "warning")
    return redirect(url_for('admin.dashboard'))


@project_bp.route('/<int:project_id>')
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project.html', project=project)

@app.route('/')
def home():
    projects = Project.query.all()  
    return render_template('home.html', projects=projects)

app.register_blueprint(admin_bp)
app.register_blueprint(project_bp)

with app.app_context():
    db.create_all()


# Run
if __name__ == '__main__':
    app.run(debug=True)
