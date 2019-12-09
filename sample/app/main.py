# coding: utf-8

from datetime import datetime
import os

from flask import flash, Flask, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, LoginManager, logout_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.debug import DebuggedApplication
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Length

from app import commands

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://{}:{}@{}:3306/{}'.format(
    os.getenv('MYSQL_USERNAME', 'web_user'),
    os.getenv('MYSQL_PASSWORD', 'password'),
    os.getenv('MYSQL_HOST', 'db'), os.getenv('MYSQL_DATABASE', 'sample_app'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'this is something special'

if app.debug:
    app.wsgi_app = DebuggedApplication(app.wsgi_app, True)

db = SQLAlchemy(app)
commands.init_app(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id) if user_id else None


def format_blog_post_date(date):
    # We could pull the format out into a constants object that we could use throughout the app
    return datetime.strftime(date, '%B %d, %Y')


def get_posts(page, result_count):
    paginated_posts = Post.query.paginate(page, result_count, False)
    posts = paginated_posts.items
    for post in posts:
        post.pub_date = format_blog_post_date(post.pub_date)
        if post.user_full_name is None:
            post.user_full_name = 'Anonymous'
    paginated_posts.items = posts
    return paginated_posts


def generate_about_me():
    random_string = 'Vestibulum id ligula porta felis euismod semper. '
    for item in range(4):
        random_string = random_string + random_string
    return random_string


class Profile:
    def __init__(self, name, email, image=None, about=None):
        self.name = name
        self.email = email
        if image is None:
            image = 'https://drinkscoaster.files.wordpress.com/2014/03/bill-murray.jpg?w=788'
        self.image = image
        if about is None:
            about = generate_about_me()
        self.about = about


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(120))

    def __repr__(self):
        return '<User %r>' % self.email

    def check_password(self, password):
        return self.password == password


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    body = db.Column(db.Text)
    pub_date = db.Column(db.DateTime)
    user_full_name = db.Column(db.String(30))

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship(
        'Category', backref=db.backref('posts', lazy='dynamic'))

    def __init__(self, title, body, category, user_full_name, pub_date=None):
        self.title = title
        self.body = body
        if pub_date is None:
            pub_date = datetime.utcnow()
        self.pub_date = pub_date
        self.category = category
        self.user_full_name = user_full_name

    def __repr__(self):
        return '<Post %r %r %r %r>' % (self.title, self.body, datetime.strftime(self.pub_date, '%B %d, %Y'), self.user_full_name)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Category %r>' % self.name


@app.route("/")
def index():
    # There are magic numbers being passed into the methods below, such as how many entries to show in pagination
    # A better way to do this would be to extract this into a Config class that we could instantiate for various scenarios
    # In Node, we might keep track of these kinds of constants in the .env file which would then in turn make things
    # all good for using different environments (just not sure the best approach in python)
    page = request.args.get('page', 1, type=int)
    posts = get_posts(page, 10)
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None

    return render_template('index.html', active='home', posts=posts.items, next_url=next_url, prev_url=prev_url)


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.user = None

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        user = User.query.filter_by(email=self.email.data).one_or_none()
        if user:
            password_match = user.check_password(self.password.data)
            if password_match:
                self.user = user
                return True

        self.password.errors.append('Invalid email and/or password specified.')
        return False


class CreatePostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    post_body = StringField('Post', validators=[Length(min=10)])

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.user = None

    def validate(self):
        rv = FlaskForm.validate(self)
        return rv


def submit_post(post):
    db.session.add(post)
    db.session.commit()


@app.route('/create-post/', methods=['GET', 'POST'])
def create_post():
    form = CreatePostForm()

    if form.validate_on_submit():
        # The user_full_name would ultimately be dynamic, stored in the Profile table mentioned in the about me route
        # We could also link this profile table to the posts table through a foreign key, but honestly that would be cumbersome
        # to have to make two requests to get all of the info we need
        post = Post(title=form.title.data, body=form.post_body.data, category=Category('categoryA'), user_full_name='David')
        submit_post(post)
        flash('Post Created!')
        return redirect(url_for('index'))

    return render_template('create-post.html', form=form)


@app.route('/auth/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        login_user(form.user)
        flash('Logged in successfully.')
        return redirect(request.args.get('next') or url_for('index'))

    return render_template('login.html', form=form)


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(request.args.get('next') or url_for('index'))


@app.route('/account/')
@login_required
def account():
    return render_template('account.html', user=current_user)


@app.route('/about-me/')
# @login_required
def about_me():
    # Probably would have a table that stores profile information separate from the user table
    # would then call a method get_profile_user(id) to pass in the correct data to the about page
    profile = Profile('David Becker', 'email@gmail.com')
    return render_template('about-me.html', profile=profile, active='about-me')


@app.before_first_request
def initialize_data():
    # just make sure we have some sample data, so we can get started.
    user = User.query.filter_by(email='blogger@sample.com').one_or_none()
    if user is None:
        user = User(email='blogger@sample.com', password='password')
        db.session.add(user)
        db.session.commit()


if __name__ == "__main__":
    app.run()
