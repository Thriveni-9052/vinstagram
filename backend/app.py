from flask import Flask, request, jsonify, render_template, session, redirect
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg','gif', 'webp', 'mp4'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
app.secret_key = "your_secret_key"
# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# ---------------- MODELS ---------------- #
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.String(300), default="")
    profile_pic = db.Column(db.String(300), default="default.png")
    followers = db.Column(db.Integer, default=0)
    following = db.Column(db.Integer, default=0)
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(500))
    caption = db.Column(db.String(200))
    likes = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) 
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
import os
with app.app_context():
    if os.environ.get("RESET_DB") == "true":
        db.drop_all()   # old tables delete
    db.create_all()     # fresh create
 
# ---------------- HOME ---------------- #
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/profile')
    return redirect('/login')
# ---------------- AUTH ---------------- #
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        bio = request.form.get('bio')

        file = request.files.get('profile_pic')
        profile_pic = "default.png"

        if file and file.filename != '':
            if not allowed_file(file.filename):
                return "Only images allowed"

            filename = secure_filename(file.filename)

            upload_folder = os.path.join(app.root_path, 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)

            profile_pic = filename

        hashed_password = generate_password_hash(password)

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "User already exists"

        new_user = User(
            username=username,
            password=hashed_password,
            bio=bio,
            profile_pic=profile_pic
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template('signup.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect('/profile')
        return "Invalid credeniitials"
    return render_template('login.html')
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logout success"})
# ---------------- POSTS ---------------- #
@app.route('/upload', methods=['POST'])
def upload():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Login required"}), 401

    caption = request.form.get("caption")
    file = request.files.get("image")
    image_url = request.form.get("image_url")

    if file and file.filename != '':
        if not allowed_file(file.filename):
            return jsonify({"message": "Only image/video allowed"}), 400

        filename = secure_filename(file.filename)

        upload_folder = os.path.join(app.root_path, 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        new_post = Post(
            image=filename,
            caption=caption,
            user_id=user_id
        )

    elif image_url:
        new_post = Post(
            image=image_url,
            caption=caption,
            user_id=user_id
        )
    else:
        return jsonify({"message": "Provide file or URL"}), 400

    db.session.add(new_post)
    db.session.commit()

    return redirect('/profile')
@app.route('/feed')
def feed():
    posts = Post.query.all()
    result = []
    for p in posts:
        user = db.session.get(User, p.user_id)
        comments = Comment.query.filter_by(post_id=p.id).all()
        comment_list = []
        for c in comments:
            u = db.session.get(User, c.user_id)
            comment_list.append({
                "text": c.text,
                "username": u.username if u else "Unknown"
            })
        result.append({
            "id": p.id,
            "image": p.image,
            "caption": p.caption,
            "likes": p.likes,
            "username": user.username if user else "Unknown",
            "comments": comment_list
        })
    return jsonify(result)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.root_path, 'uploads'), filename)
# ---------------- LIKE ---------------- #
@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"message": "Post not found"}), 404
    post.likes = (post.likes or 0) + 1
    db.session.commit()
    return jsonify({"likes": post.likes})
@app.route('/follow/<int:id>', methods=['POST'])
def follow_user(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({"message": "User not found"})
    user.followers = (user.followers or 0) + 1
    db.session.commit()
    return jsonify({"message": "Followed successfully"})
@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    data = request.get_json()   # ✅ important change
    text = data.get("text")
    if not text:
        return jsonify({"message": "Comment empty"}), 400
    user_id = session.get("user_id")
    new_comment = Comment(
        text=text,
        user_id=user_id,
        post_id=post_id
    )
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({"message": "Comment added"})
@app.route('/delete/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    user_id = session.get('user_id')
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"message": "Post not found"}), 404
    # 🔒 only owner can delete
    if post.user_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403
    # 🗑️ delete from DB
    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Deleted"})
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')   # ✅ correct indent
    user_id = session.get('user_id')   # ✅ no extra space
    posts = Post.query.filter_by(user_id=user_id).all()
    result = []
    for p in posts:
        comments = Comment.query.filter_by(post_id=p.id).all()
        comment_list = []
        for c in comments:
            user = db.session.get(User, c.user_id)
            comment_list.append({
                "id": c.id,
                "text": c.text,
                "username": user.username if user else "Unknown"
            })
        result.append({
            "id": p.id,
            "image": p.image,
            "caption": p.caption,
            "likes": p.likes,
            "comments": comment_list,
            "comment_count": len(comments)
        })
    user = db.session.get(User, user_id)
    
    return render_template('profile.html', posts=result, user=user)
@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect('/login')

    user = db.session.get(User, session['user_id'])

    if not user:
        return "User not found. Please login again."

    file = request.files.get('profile_pic')

    if file and file.filename != '':
        filename = secure_filename(file.filename)

        upload_folder = os.path.join(app.root_path, 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        user.profile_pic = filename
        db.session.commit()

    return redirect('/profile')
@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if comment:
        db.session.delete(comment)
        db.session.commit()
        return redirect('/profile')
    return "Comment not found"
# ---------------- RUN ---------------- #
if __name__ == '__main__':
    app.run(debug=True)



