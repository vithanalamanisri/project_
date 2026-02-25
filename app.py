from flask import Flask, render_template, jsonify, request, Response, session
import json
import os
import sqlite3

app = Flask(__name__)
# Use an environment variable for the secret key in production, fallback for local testing
app.secret_key = os.environ.get('SECRET_KEY', 'emerald_master_secret_key_123')

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
def init_db():
    """Creates an SQLite database to store user saved roadmaps."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Create table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS saved_roadmaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            course TEXT NOT NULL,
            branch TEXT NOT NULL,
            year TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database when the app starts
init_db()

# Helper function to load JSON data
def load_data():
    file_path = os.path.join(os.path.dirname(__file__), 'data.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/roadmap', methods=['GET'])
def get_roadmap():
    return jsonify(load_data())

@app.route('/api/search', methods=['GET'])
def search_skills():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify({"error": "No search query provided"}), 400

    data = load_data()
    results = []
    for course, branches in data.items():
        for branch, years in branches.items():
            for year, details in years.items():
                all_skills = details.get('technical', []) + details.get('core', [])
                for skill in all_skills:
                    if query in skill.lower():
                        results.append({"course": course, "branch": branch, "year": year, "matched_skill": skill})
    return jsonify({"results": results, "count": len(results)})

@app.route('/api/export', methods=['GET'])
def export_roadmap():
    course, branch, year = request.args.get('course'), request.args.get('branch'), request.args.get('year')
    data = load_data()
    if not course or not branch or not year:
        return "Missing parameters", 400
    try:
        roadmap = data[course][branch][year]
        content = f"🎓 PATHFINDER ROADMAP 🎓\nCourse: {course}\nBranch: {branch}\nYear: {year}\n" + "="*40 + "\n\n"
        sections = [("📚 Core Subjects", "core"), ("🛠 Technical Skills", "technical"), ("🚀 Projects & Research", "projects"), 
                    ("📜 Professional Certifications", "certifications"), ("🏢 Internships & Practical", "internships"), 
                    ("💼 Career Trajectories", "career"), ("💡 Expert Advice", "advice")]
        for title, key in sections:
            if key in roadmap and roadmap[key]:
                content += f"{title}\n" + "-"*len(title) + "\n"
                for item in roadmap[key]: content += f" • {item}\n"
                content += "\n"
        filename = f"Roadmap_{course}_{branch}_Year{year}.txt".replace(" ", "_")
        return Response(content, mimetype="text/plain", headers={"Content-disposition": f"attachment; filename={filename}"})
    except KeyError:
        return "Roadmap not found", 404

# ==========================================
# 🔐 USER AUTHENTICATION & STORAGE
# ==========================================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    if email:
        session['user_email'] = email
        return jsonify({"success": True, "email": email})
    return jsonify({"success": False, "error": "Email is required"}), 400

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_email', None)
    return jsonify({"success": True})

@app.route('/api/session', methods=['GET'])
def check_session():
    if 'user_email' in session:
        return jsonify({"logged_in": True, "email": session['user_email']})
    return jsonify({"logged_in": False})

@app.route('/api/save', methods=['POST'])
def save_roadmap():
    if 'user_email' not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401
    
    data = request.json
    course, branch, year = data.get('course'), data.get('branch'), data.get('year')
    email = session['user_email']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM saved_roadmaps WHERE email=? AND course=? AND branch=? AND year=?", (email, course, branch, year))
    if c.fetchone():
        conn.close()
        return jsonify({"success": False, "error": "Roadmap already saved!"})
    
    c.execute("INSERT INTO saved_roadmaps (email, course, branch, year) VALUES (?, ?, ?, ?)", (email, course, branch, year))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Roadmap saved to profile!"})

@app.route('/api/saved_roadmaps', methods=['GET'])
def get_saved_roadmaps():
    if 'user_email' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    email = session['user_email']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT course, branch, year FROM saved_roadmaps WHERE email=?", (email,))
    rows = c.fetchall()
    conn.close()
    
    saved = [{"course": r[0], "branch": r[1], "year": r[2]} for r in rows]
    return jsonify(saved)

if __name__ == '__main__':
    # Render assigns a dynamic port. This ensures Flask listens to it correctly.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)