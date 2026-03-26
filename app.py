import os
import uuid
import zipfile
import subprocess

ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
    "jpg", "jpeg", "png", "txt"
}

import mimetypes

def allowed_file(filename):
    if not ("." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS):
        return False
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        return False
    if mime_type.startswith('application/') or mime_type.startswith('image/') or mime_type.startswith('text/'):
        return True
    return False

def generate_safe_filename(filename):
    ext = filename.rsplit(".", 1)[1].lower()
    safe_name = secure_filename(filename.rsplit(".", 1)[0])[:50]
    return f"{uuid.uuid4().hex}_{safe_name}.{ext}"

from pathlib import Path
from datetime import datetime, timedelta
from threading import Thread

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import email_service
import secrets

# --- PDF Manipulation Libraries ---
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from pdf2docx import Converter
try:
    from docx2pdf import convert as docx2pdf_convert
except ImportError:
    docx2pdf_convert = None
from PIL import Image
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import pytesseract
from pdf2image import convert_from_path
import pdfkit
from pptx import Presentation
from pptx.util import Inches
import pdfplumber

# AI Libraries
import openai

# Signatures
try:
    from pyhanko.sign import signers
    from pyhanko.pdf_utils.writer import copy_into_new_writer
    from pyhanko.pdf_utils.reader import PdfFileReader
except ImportError:
    pass

# Load environment
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


app = Flask(__name__)
# 🔐 SECURITY CONFIG
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
PRIVATE_UPLOAD_DIR = INSTANCE_DIR / "private_uploads"
PRIVATE_OUTPUT_DIR = INSTANCE_DIR / "private_outputs"

INSTANCE_DIR.mkdir(exist_ok=True)
PRIVATE_UPLOAD_DIR.mkdir(exist_ok=True)
PRIVATE_OUTPUT_DIR.mkdir(exist_ok=True)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-insecure-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///app.db")

max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "16"))
app.config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

is_production = os.getenv("FLASK_ENV", "development").lower() == "production"
app.config["SESSION_COOKIE_SECURE"] = is_production
app.config["REMEMBER_COOKIE_SECURE"] = is_production

app.config["WTF_CSRF_TIME_LIMIT"] = 3600

csrf = CSRFProtect(app)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "10 per minute"],
    storage_uri="memory://",
)

csp = {
    "default-src": "'self'",
    "img-src": ["'self'", "data:"],
    "style-src": ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com", "https://fonts.googleapis.com"],
    "font-src": ["'self'", "https://cdnjs.cloudflare.com", "https://fonts.gstatic.com"],
    "script-src": ["'self'", "'unsafe-inline'"],
}

Talisman(
    app,
    force_https=is_production,
    strict_transport_security=is_production,
    content_security_policy=csp,
    frame_options="DENY",
    referrer_policy="strict-origin-when-cross-origin"
)

ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
    "jpg", "jpeg", "png", "txt"
}

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

import logging
from logging.handlers import RotatingFileHandler
if not app.debug:
    os.makedirs('instance/logs', exist_ok=True)
    file_handler = RotatingFileHandler('instance/logs/security.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('VijayPDF secure startup')

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f"Server Error: {error}")
    return render_template('500.html'), 500

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

with app.app_context():
    db.create_all()

# --- Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    failed_logins = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    # OTP Fields
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Password Reset Fields
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    files = db.relationship("UserFile", backref="owner", lazy=True)
class UserFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False, unique=True)
    stored_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)    

class ConversionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(100), nullable=False)
    converted_filename = db.Column(db.String(100), nullable=True)
    conversion_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Helpers ---
def save_uploaded_files(files):
    saved_paths = []

    for f in files:
        if not f or not f.filename:
            continue

        if not allowed_file(f.filename):
            raise Exception(f"File type not allowed: {f.filename}")

        safe_name = generate_safe_filename(f.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)

        f.save(path)
        saved_paths.append((path, f.filename))

    return saved_paths

def log_history(original, converted, type_name):
    if current_user.is_authenticated:
        db.session.add(ConversionHistory(original_filename=original, converted_filename=converted, conversion_type=type_name, user_id=current_user.id))
        db.session.commit()

# ======================================================================
# 1. ORGANIZE PDF FUNCTIONS
# ======================================================================
def merge_pdf_func(files_list, out_path):
    merger = PdfMerger()
    for fp in files_list:
        merger.append(fp)
    merger.write(out_path)
    merger.close()

def split_pdf_func(in_path, out_zip):
    doc = fitz.open(in_path)
    with zipfile.ZipFile(out_zip, 'w') as zf:
        for i in range(len(doc)):
            ndoc = fitz.open()
            ndoc.insert_pdf(doc, from_page=i, to_page=i)
            tpath = out_zip.replace('.zip', f'_pg{i+1}.pdf')
            ndoc.save(tpath)
            zf.write(tpath, f'page_{i+1}.pdf')
            os.remove(tpath)

def remove_pages_func(in_path, out_path, pages_str):
    doc = fitz.open(in_path)
    # Ex: "1,3,5" -> convert to 0-indexed [0, 2, 4]
    try:
        pgs = [int(p.strip())-1 for p in pages_str.split(',')]
        # Delete reverse order to avoid index shifts
        for p in sorted(pgs, reverse=True):
            if 0 <= p < len(doc):
                doc.delete_page(p)
    except:
        raise Exception("Invalid page range format. Use e.g. '1,3,5'")
    doc.save(out_path)

def extract_pages_func(in_path, out_path, pages_str):
    doc = fitz.open(in_path)
    try:
        pgs = [int(p.strip())-1 for p in pages_str.split(',')]
        doc.select(pgs)
    except:
        raise Exception("Invalid page format.")
    doc.save(out_path)

def organize_pdf_func(in_path, out_path, order_str):
    doc = fitz.open(in_path)
    try:
        pgs = [int(p.strip())-1 for p in order_str.split(',')]
        doc.select(pgs)
    except:
        raise Exception("Invalid page order format.")
    doc.save(out_path)

def scan_to_pdf_func(image_paths, out_path):
    images = [Image.open(fp).convert('RGB') for fp in image_paths]
    if images:
        images[0].save(out_path, save_all=True, append_images=images[1:])

# ======================================================================
# 2. OPTIMIZE PDF FUNCTIONS
# ======================================================================
def compress_pdf_func(in_path, out_path):
    doc = fitz.open(in_path)
    doc.save(out_path, garbage=4, deflate=True)

def repair_pdf_func(in_path, out_path):
    # fitz will rewrite broken xref tables automatically stringently
    doc = fitz.open(in_path)
    doc.save(out_path, clean=True)

def ocr_pdf_func(in_path, out_txt):
    imgs = convert_from_path(in_path, poppler_path=r"C:\poppler\Library\bin")
    text = "\n".join([pytesseract.image_to_string(i) for i in imgs])
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(text)

# ======================================================================
# 3. CONVERT TO PDF FUNCTIONS
# ======================================================================
def jpg_to_pdf_func(image_paths, out_path):
    scan_to_pdf_func(image_paths, out_path)

def word_to_pdf_func(in_path, out_path):
    if docx2pdf_convert is None:
        raise Exception("Word to PDF is not available on this server.")
    docx2pdf_convert(os.path.abspath(in_path), os.path.abspath(out_path))

def powerpoint_to_pdf_func(in_path, out_path):
    # Requires comtypes (Windows only + MS Office installed)
    try:
        import comtypes.client
        powerpoint = comtypes.client.CreateObject("Powerpoint.Application")
        powerpoint.Visible = 1
        deck = powerpoint.Presentations.Open(os.path.abspath(in_path))
        deck.SaveAs(os.path.abspath(out_path), 32) # formatType = 32 for pdf
        deck.Close()
        powerpoint.Quit()
    except Exception as e:
        raise Exception("PowerPoint to PDF failed. Ensure MS PowerPoint is installed on this Windows server. " + str(e))

def excel_to_pdf_func(in_path, out_path):
    df = pd.read_excel(in_path)
    doc = SimpleDocTemplate(out_path, pagesize=letter)
    data = [df.columns.values.tolist()] + df.values.tolist()
    d_str = [[str(item) for item in row] for row in data]
    t = Table(d_str)
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
    doc.build([t])

def html_to_pdf_func(in_path, out_path):
    # Note: Requires system wkhtmltopdf
    try:
        pdfkit.from_file(in_path, out_path)
    except OSError:
        raise Exception("HTML to PDF requires wkhtmltopdf installed on the system.")

# ======================================================================
# 4. CONVERT FROM PDF FUNCTIONS
# ======================================================================
def pdf_to_jpg_func(in_path, out_zip):
   imgs = convert_from_path(in_path, poppler_path=r"C:\poppler\Library\bin")
   with zipfile.ZipFile(out_zip, 'w') as zf:
        for idx, img in enumerate(imgs):
            tmp = out_zip.replace('.zip', f'_{idx}.jpg')
            img.save(tmp, 'JPEG')
            zf.write(tmp, f'page_{idx+1}.jpg')
            os.remove(tmp)

def pdf_to_word_func(in_path, out_path):
    cv = Converter(in_path)
    cv.convert(out_path)
    cv.close()

def pdf_to_powerpoint_func(in_path, out_path):
    # Convert PDF pages to images then embed in PPTX
    imgs = convert_from_path(in_path, poppler_path=r"C:\poppler\Library\bin")
    prs = Presentation()
    for img in imgs:
        tmp = out_path.replace('.pptx', '_tmp.jpg')
        img.save(tmp)
        blank_slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(blank_slide_layout)
        slide.shapes.add_picture(tmp, 0, 0, width=prs.slide_width, height=prs.slide_height)
        os.remove(tmp)
    prs.save(out_path)

def pdf_to_excel_func(in_path, out_path):
    tables_data = []
    with pdfplumber.open(in_path) as pdf:
        for page in pdf.pages:
            tabs = page.extract_tables()
            for t in tabs:
                tables_data.extend(t)
    if not tables_data:
        raise Exception("No tables found in PDF.")
    df = pd.DataFrame(tables_data[1:], columns=tables_data[0])
    df.to_excel(out_path, index=False)

def pdf_to_pdfa_func(in_path, out_path):
    # Fallback Ghostscript invocation or error
    try:
        cmd = ['gs', '-dPDFA', '-dBATCH', '-dNOPAUSE', '-sProcessColorModel=DeviceRGB', '-sDEVICE=pdfwrite', f'-sOutputFile={out_path}', in_path]
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        raise Exception("Ghostscript (gs) is required for PDF/A conversion.")

# ======================================================================
# 5. EDIT PDF FUNCTIONS
# ======================================================================
def rotate_pdf_func(in_path, out_path, angle):
    doc = fitz.open(in_path)
    for p in doc:
        p.set_rotation(int(angle))
    doc.save(out_path)

def add_page_numbers_func(in_path, out_path):
    doc = fitz.open(in_path)
    for i, p in enumerate(doc):
        p.insert_text(fitz.Point(300, 800), str(i+1), fontsize=12)
    doc.save(out_path)

def add_watermark_func(in_path, out_path, text):
    doc = fitz.open(in_path)
    for p in doc:
        p.insert_text(fitz.Point(100, 400), text, fontsize=30, color=(1, 0, 0))
    doc.save(out_path)

def crop_pdf_func(in_path, out_path):
    doc = fitz.open(in_path)
    for p in doc:
        r = p.rect
        r.x0 += 50; r.y0 += 50; r.x1 -= 50; r.y1 -= 50 # simple 50pt crop
        p.set_cropbox(r)
    doc.save(out_path)

def edit_pdf_func(in_path, out_path, append_text):
    doc = fitz.open(in_path)
    if len(doc) > 0:
        doc[0].insert_text(fitz.Point(50, 50), append_text, fontsize=14, color=(0,0,1))
    doc.save(out_path)

# ======================================================================
# 6. SECURITY FUNCTIONS
# ======================================================================
def unlock_pdf_func(in_path, out_path, pwd):
    doc = fitz.open(in_path)
    doc.authenticate(pwd)
    doc.save(out_path)

def protect_pdf_func(in_path, out_path, pwd):
    doc = fitz.open(in_path)
    doc.save(out_path, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=pwd)

def sign_pdf_func(in_path, out_path, pfx_path, pfx_pass):
    signer = signers.SimpleSigner.load_pkcs12(pfx_path, pfx_pass.encode())
    with open(in_path, 'rb') as f:
        w = copy_into_new_writer(PdfFileReader(f))
        signers.sign_pdf(w, signers.PdfSignatureMetadata(field_name='Signature1'), signer=signer, in_place=True, out_file=open(out_path, 'wb'))

def redact_pdf_func(in_path, out_path, txt_to_redact):
    doc = fitz.open(in_path)
    for p in doc:
        inst = p.search_for(txt_to_redact)
        for i in inst:
            p.add_redact_annot(i, fill=(0,0,0))
        p.apply_redactions()
    doc.save(out_path)

def compare_pdf_func(in1, in2, out_txt):
    t1 = "".join([p.get_text() for p in fitz.open(in1)])
    t2 = "".join([p.get_text() for p in fitz.open(in2)])
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write("Differences found." if t1 != t2 else "Documents are identical textually.")

# ======================================================================
# 7. AI FUNCTIONS
# ======================================================================
def ai_summarize_func(in_path):
    t = "".join([p.get_text() for p in fitz.open(in_path)])
    r = openai.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Summarize: " + t[:10000]}])
    return r.choices[0].message.content

def translate_pdf_func(in_path, lang):
    t = "".join([p.get_text() for p in fitz.open(in_path)])
    r = openai.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": f"Translate to {lang}: " + t[:4000]}])
    return r.choices[0].message.content

def chat_with_pdf_func(in_path, q):
    t = "".join([p.get_text() for p in fitz.open(in_path)])
    r = openai.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": f"Context: {t[:8000]}\nQuestion: {q}"}])
    return r.choices[0].message.content


# ======================================================================
# FLASK SINGLE-FILE ROUTER BINDINGS
# ======================================================================

def process_wrapper(func, ext=".pdf", multi=False, is_text=False):
    files = request.files.getlist('files[]')
    if not files: return jsonify({'error': 'No file provided'}), 400
    paths = save_uploaded_files(files)
    
    out_name = f"{uuid.uuid4().hex}{ext}"
    out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
    
    try:
        # Some endpoints return pure text
        if is_text:
            ans = func(paths[0][0])
            log_history(paths[0][1], "AI_TXT", request.path)
            return jsonify({'success': True, 'text_result': ans})
            
        if multi:
            func([p[0] for p in paths], out_path)
        else:
            func(paths[0][0], out_path)
        log_history(paths[0][1], out_name, request.path)
        return jsonify({'success': True, 'download_url': url_for('download_file', filename=out_name)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API Routes

# Display Web Routes

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route("/tools")
def tools():
    return render_template("tools.html")

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")

# Tool Pages
@app.route("/pdf-to-word")
def pdf_to_word():
    return render_template("tools/pdf_to_word.html")

@app.route("/word-to-pdf")
def word_to_pdf():
    return render_template("tools/word_to_pdf.html")

@app.route("/jpg-to-pdf")
def jpg_to_pdf():
    return render_template("tools/jpg_to_pdf.html")

@app.route("/pdf-to-jpg")
def pdf_to_jpg():
    return render_template("tools/pdf_to_jpg.html")

@app.route("/merge-pdf")
def merge_pdf():
    return render_template("tools/merge_pdf.html")

@app.route("/split-pdf")
def split_pdf():
    return render_template("tools/split_pdf.html")

@app.route("/compress-pdf")
def compress_pdf():
    return render_template("tools/compress_pdf.html")

# Info Pages
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact-support", methods=['GET', 'POST'])
def contact_support():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # 1. Send Internal Notification
        subject = f"New Contact Message - {name}"
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        email_service.send_email(os.getenv("EMAIL_USER"), f"New Contact Message - VijayPDF", body)
        
        # 2. Send Auto-Reply to User
        email_service.send_auto_reply(email, name)
        
        flash("Thank you for contacting VijayPDF.com. Our team will respond shortly.", "success")
        return render_template("contact.html", success=True)
        
    return render_template("contact.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy_policy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route('/api/merge', methods=['POST'])
@csrf.exempt
def route_merge(): return process_wrapper(lambda in_paths, out_path: merge_pdf_func(in_paths, out_path), multi=True)

@app.route('/api/split', methods=['POST'])
@csrf.exempt
def route_split(): return process_wrapper(lambda inp, out: split_pdf_func(inp, out), ext="_split.zip")

@app.route('/api/remove-pages', methods=['POST'])
@csrf.exempt
def route_rem(): return process_wrapper(lambda inp, out: remove_pages_func(inp, out, request.form.get('pages', '')))

@app.route('/api/extract-pages', methods=['POST'])
@csrf.exempt
def route_ext(): return process_wrapper(lambda inp, out: extract_pages_func(inp, out, request.form.get('pages', '')))

@app.route('/api/organize', methods=['POST'])
@csrf.exempt
def route_org(): return process_wrapper(lambda inp, out: organize_pdf_func(inp, out, request.form.get('pages', '')))

@app.route('/api/scan-to-pdf', methods=['POST'])
@csrf.exempt
def route_scan(): return process_wrapper(lambda inp, out: scan_to_pdf_func(inp, out), multi=True)

@app.route('/api/compress', methods=['POST'])
@csrf.exempt
def route_comp(): return process_wrapper(lambda inp, out: compress_pdf_func(inp, out))

@app.route('/api/repair', methods=['POST'])
@csrf.exempt
def route_rep(): return process_wrapper(lambda inp, out: repair_pdf_func(inp, out))

@app.route('/api/ocr', methods=['POST'])
@csrf.exempt
def route_ocr(): return process_wrapper(lambda inp, out: ocr_pdf_func(inp, out), ext=".txt")

@app.route('/api/jpg-to-pdf', methods=['POST'])
@csrf.exempt
def route_j2p(): return process_wrapper(lambda inp, out: jpg_to_pdf_func(inp, out), multi=True)

@app.route('/api/word-to-pdf', methods=['POST'])
@csrf.exempt
def route_w2p(): return process_wrapper(lambda inp, out: word_to_pdf_func(inp, out))

@app.route('/api/powerpoint-to-pdf', methods=['POST'])
@csrf.exempt
def route_p2p(): return process_wrapper(lambda inp, out: powerpoint_to_pdf_func(inp, out))

@app.route('/api/excel-to-pdf', methods=['POST'])
@csrf.exempt
def route_e2p(): return process_wrapper(lambda inp, out: excel_to_pdf_func(inp, out))

@app.route('/api/html-to-pdf', methods=['POST'])
@csrf.exempt
def route_h2p(): return process_wrapper(lambda inp, out: html_to_pdf_func(inp, out))

@app.route('/api/pdf-to-jpg', methods=['POST'])
@csrf.exempt
def route_p2j(): return process_wrapper(lambda inp, out: pdf_to_jpg_func(inp, out), ext=".zip")

@app.route('/api/pdf-to-word', methods=['POST'])
@csrf.exempt
def route_p2w(): return process_wrapper(lambda inp, out: pdf_to_word_func(inp, out), ext=".docx")

@app.route('/api/pdf-to-powerpoint', methods=['POST'])
@csrf.exempt
def route_p2pptx(): return process_wrapper(lambda inp, out: pdf_to_powerpoint_func(inp, out), ext=".pptx")

@app.route('/api/pdf-to-excel', methods=['POST'])
@csrf.exempt
def route_p2x(): return process_wrapper(lambda inp, out: pdf_to_excel_func(inp, out), ext=".xlsx")

@app.route('/api/pdf-to-pdfa', methods=['POST'])
@csrf.exempt
def route_p2a(): return process_wrapper(lambda inp, out: pdf_to_pdfa_func(inp, out))

@app.route('/api/rotate', methods=['POST'])
@csrf.exempt
def route_rot(): return process_wrapper(lambda inp, out: rotate_pdf_func(inp, out, request.form.get('angle', '90')))

@app.route('/api/add-page-numbers', methods=['POST'])
@csrf.exempt
def route_pn(): return process_wrapper(lambda inp, out: add_page_numbers_func(inp, out))

@app.route('/api/add-watermark', methods=['POST'])
@csrf.exempt
def route_wm(): return process_wrapper(lambda inp, out: add_watermark_func(inp, out, request.form.get('text', 'WATERMARK')))

@app.route('/api/crop', methods=['POST'])
@csrf.exempt
def route_crop(): return process_wrapper(lambda inp, out: crop_pdf_func(inp, out))

@app.route('/api/edit-pdf', methods=['POST'])
@csrf.exempt
def route_edit(): return process_wrapper(lambda inp, out: edit_pdf_func(inp, out, request.form.get('text', '')))

@app.route('/api/unlock', methods=['POST'])
@csrf.exempt
def route_unl(): return process_wrapper(lambda inp, out: unlock_pdf_func(inp, out, request.form.get('password', '')))

@app.route('/api/protect', methods=['POST'])
@csrf.exempt
def route_prot(): return process_wrapper(lambda inp, out: protect_pdf_func(inp, out, request.form.get('password', '')))

@app.route('/api/sign', methods=['POST'])
@csrf.exempt
def route_sign(): return process_wrapper(lambda inp, out: sign_pdf_func(inp, out, request.form.get('pfx'), request.form.get('password', '')))

@app.route('/api/redact', methods=['POST'])
@csrf.exempt
def route_redact(): return process_wrapper(lambda inp, out: redact_pdf_func(inp, out, request.form.get('text', '')))

@app.route('/api/compare', methods=['POST'])
@csrf.exempt
def route_comp_pdf(): 
    f = save_uploaded_files(request.files.getlist('files[]'))
    if len(f)<2: return jsonify({'error': 'Needs 2 files'}), 400
    out_name = f"{uuid.uuid4().hex}.txt"
    compare_pdf_func(f[0][0], f[1][0], os.path.join(app.config['OUTPUT_FOLDER'], out_name))
    return jsonify({'success':True, 'download_url': url_for('download_file', filename=out_name)})

@app.route('/api/summarize', methods=['POST'])
@csrf.exempt
def route_sum(): return process_wrapper(lambda inp: ai_summarize_func(inp), is_text=True)

@app.route('/api/translate', methods=['POST'])
@csrf.exempt
def route_trans(): return process_wrapper(lambda inp: translate_pdf_func(inp, request.form.get('language', 'Spanish')), is_text=True)

@app.route('/api/chat', methods=['POST'])
@csrf.exempt
def route_chat(): return process_wrapper(lambda inp: chat_with_pdf_func(inp, request.form.get('question', 'What is this document about?')), is_text=True)

# Main web routes
@app.route('/')
def index():
    total_conversions = 0
    recent_count = 0

    if current_user.is_authenticated:
        total_conversions = ConversionHistory.query.filter_by(user_id=current_user.id).count()
        recent_count = ConversionHistory.query.filter_by(user_id=current_user.id).order_by(ConversionHistory.id.desc()).limit(5).count()

    return render_template(
        'index.html',
        total_conversions=total_conversions,
        recent_count=recent_count
    )

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user:
            if user.locked_until and user.locked_until > datetime.utcnow():
                flash('Account locked due to multiple failed login attempts. Try again later.', 'danger')
                app.logger.warning(f'Locked login attempt for user: {username}')
                return render_template('login.html')
                
            if bcrypt.check_password_hash(user.password, password):
                user.failed_logins = 0
                user.locked_until = None
                db.session.commit()
                login_user(user)
                app.logger.info(f'Successful login for user: {username}')
                return redirect(url_for('index'))
            else:
                user.failed_logins += 1
                if user.failed_logins >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                    app.logger.warning(f'Account locked for user: {username}')
                db.session.commit()
                
        app.logger.warning(f'Failed login attempt for username: {username}')
        flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('register.html')
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Generate OTP
        otp = str(secrets.randbelow(1000000)).zfill(6)
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        user = User(username=username, email=email, password=hashed_password, otp=otp, otp_expiry=otp_expiry)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Send OTP Email
            email_service.send_otp_email(email, otp)
            
            flash('Account created! Please verify your email with the OTP sent.', 'info')
            return redirect(url_for('verify_otp', email=email))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            
    return render_template('register.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email')
    if request.method == 'POST':
        email = request.form.get('email')
        otp_input = request.form.get('otp')
        user = User.query.filter_by(email=email).first()
        
        if user and user.otp == otp_input and user.otp_expiry > datetime.utcnow():
            user.is_verified = True
            user.otp = None
            user.otp_expiry = None
            db.session.commit()
            flash('Email verified! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid or expired OTP.', 'danger')
            
    return render_template('verify_otp.html', email=email)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            email_service.send_password_reset_email(email, token)
        
        flash('If an account matches that email, a reset link has been sent.', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.reset_token_expiry < datetime.utcnow():
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        new_password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.password = hashed_password
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash('Password updated! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_password.html', token=token)

@app.route('/test-email')
def test_email_route():
    if email_service.test_connection():
        return "Test email sent successfully! Check your inbox (support@vijaypdf.com)."
    else:
        return "Failed to send test email. Check server logs and .env configuration."

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/history')
def history():
    user_history = ConversionHistory.query.filter_by(user_id=current_user.id).order_by(ConversionHistory.id.desc()).all()
    return render_template('history.html', history=user_history)
@app.route('/download/<filename>')
def download_file(filename):
    safe_filename = secure_filename(filename)
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], safe_filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_from_directory(app.config['OUTPUT_FOLDER'], safe_filename, as_attachment=True)
if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True, port=5000)

    # if __name__ == "__main__":
    #     app.run(debug=True)

