from flask import Flask, render_template, request, redirect, session, send_from_directory
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
app.secret_key = "secret123"

# ================= MONGODB =================
client = MongoClient("mongodb+srv://Rakesh:rakesh123@cluster0.lhxzbbg.mongodb.net/")
db = client["recruitment_db"]

jobs_collection = db["jobs"]
applications_collection = db["applications"]

# ================= EMAIL =================
SENDER_EMAIL = "crakeshm1003@gmail.com"
APP_PASSWORD = "uxwt cglj levn svjx"

# ================= EMAIL FUNCTION =================
def send_email(to_email, subject, body, attachment=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # attachment
        if attachment and os.path.exists(attachment):
            with open(attachment, "rb") as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={os.path.basename(attachment)}'
                )
                msg.attach(part)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()

    except Exception as e:
        print("Email Error:", e)

# ================= HOME =================
@app.route('/')
def index():
    jobs = list(jobs_collection.find())
    return render_template("index.html", jobs=jobs)

# ================= APPLY =================
@app.route('/apply/<job_id>', methods=['GET', 'POST'])
def apply(job_id):
    job = jobs_collection.find_one({"_id": ObjectId(job_id)})

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        experience = request.form['experience']
        skills = request.form['skills']
        ctc = request.form['ctc']

        file = request.files.get('resume')

        filename = ""
        filepath = ""

        if file and file.filename != "":
            if not os.path.exists("uploads"):
                os.makedirs("uploads")

            filename = file.filename
            filepath = os.path.join("uploads", filename)
            file.save(filepath)

        applications_collection.insert_one({
            "name": name,
            "email": email,
            "job": job['title'],
            "skills": skills,
            "experience": experience,
            "ctc": ctc,
            "resume": filename,
            "status": "Pending"
        })

        # USER EMAIL
        send_email(
            email,
            "Application Submitted",
            f"Dear {name},\n\nYour application for {job['title']} has been submitted successfully.\n\nHR Team"
        )

        # ADMIN EMAIL
        send_email(
            SENDER_EMAIL,
            "New Application Received",
            f"{name} applied for {job['title']}",
            attachment=filepath
        )

        return render_template("apply.html", job=job, success=True)

    return render_template("apply.html", job=job)

# ================= VIEW RESUME =================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

# ================= ADMIN LOGIN =================
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']

        if password == "admin123":
            session['admin'] = True
            return redirect('/admin')
        else:
            return render_template("admin_login.html", error="Wrong Password")

    return render_template("admin_login.html")

# ================= ADMIN PANEL =================
@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect('/admin_login')

    applications = list(applications_collection.find())
    return render_template("admin.html", applications=applications)

# ================= SELECT / REJECT =================
@app.route('/update_status/<id>', methods=['POST'])
def update_status(id):
    status = request.form['status']

    applications_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": status}}
    )

    user = applications_collection.find_one({"_id": ObjectId(id)})

    if status == "selected":
        send_email(
            user['email'],
            "Application Selected",
            f"Dear {user['name']},\n\nCongratulations! You have been selected for {user['job']}.\n\nHR Team"
        )
    else:
        send_email(
            user['email'],
            "Application Rejected",
            f"Dear {user['name']},\n\nWe regret to inform you that you were not selected.\n\nHR Team"
        )

    return redirect('/admin')

# ================= RUN =================
if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    app.run(host="0.0.0.0", port=5000, debug=True)