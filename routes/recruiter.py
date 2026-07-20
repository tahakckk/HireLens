import json
import os
import sqlite3
import uuid

import numpy as np
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from database import get_db
from file_parser import parse_file
from job_scraper import scrape_linkedin_job, validate_linkedin_url
from routes.helpers import clean_text
from routes.helpers import allowed_file, get_upload_path, remove_upload_file, validate_saved_cv

recruiter_bp = Blueprint("recruiter", __name__)

def embedding_to_bytes(embedding: np.ndarray) -> bytes:
    return embedding.tobytes()


@recruiter_bp.route('/')
def index():

    db = get_db()
    cv_count = db.execute("SELECT COUNT(*) FROM cvs").fetchone()[0]
    job_count = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    match_count = db.execute("SELECT COUNT(DISTINCT job_id) FROM matches").fetchone()[0]

    recent_cvs = db.execute(
        "SELECT id, filename, extracted_skills, uploaded_at FROM cvs ORDER BY uploaded_at DESC LIMIT 5"
    ).fetchall()

    recent_jobs = db.execute(
        "SELECT id, title, required_skills, created_at FROM jobs ORDER BY created_at DESC LIMIT 5"
    ).fetchall()

    return render_template('index.html',
                           cv_count=cv_count,
                           job_count=job_count,
                           match_count=match_count,
                           recent_cvs=recent_cvs,
                           recent_jobs=recent_jobs)

@recruiter_bp.route('/upload-cv', methods=['GET', 'POST'])
def upload_cv():

    if request.method == 'POST':
        if 'files' not in request.files:
            flash('Dosya seçilmedi.', 'error')
            return redirect(request.url)

        files = request.files.getlist('files')
        uploaded_count = 0
        errors = []

        for file in files:
            filepath = None
            if file.filename == '':
                continue

            if not allowed_file(file.filename):
                errors.append(f"'{file.filename}' — sadece PDF ve DOCX dosyaları desteklenmektedir.")
                continue

            try:

                filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
                file.save(filepath)

                if not validate_saved_cv(Path(filepath)):
                    errors.append(f"'{filename}' — dosya içeriği geçersiz veya desteklenmiyor.")
                    continue

                parse_result = parse_file(filepath)
                raw_text = parse_result['text']
                warnings = parse_result['warnings']

                if not raw_text or len(raw_text.strip()) < 50:
                    errors.append(f"'{filename}' — PDF/DOCX'den yeterli metin çıkarılamadı.")
                    remove_upload_file(Path(filepath))
                    continue

                if warnings:
                    session['upload_warnings'] = warnings

                extracted_info = current_app.extensions["nlp_engine"].extract_cv_info(raw_text)

                cleaned = clean_text(raw_text)

                embedding = current_app.extensions["nlp_engine"].encode_text(raw_text)

                cv_id = str(uuid.uuid4())
                db = get_db()
                db.execute(
                    """INSERT INTO cvs (id, filename, file_path, original_text, cleaned_text,
                       extracted_skills, timeline, experience_months, skill_recency, metadata, embedding, uploaded_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (cv_id, filename, unique_name, raw_text, cleaned,
                     json.dumps(extracted_info.get('skills', [])),
                     json.dumps(extracted_info.get('timeline', [])),
                     extracted_info.get('total_experience_months', 0),
                     json.dumps(extracted_info.get('skill_recency', {})),
                     json.dumps({'warnings': warnings}),
                     embedding_to_bytes(embedding),
                     datetime.now().isoformat())
                )
                db.commit()

                uploaded_count += 1

            except Exception:
                current_app.logger.exception('CV upload failed')
                remove_upload_file(Path(filepath) if filepath else None)
                errors.append(f"'{file.filename}' — CV işlenemedi. Lütfen geçerli bir PDF veya DOCX deneyin.")

        if uploaded_count > 0:
            flash(f'{uploaded_count} CV başarıyla yüklendi ve analiz edildi!', 'success')
        if errors:
            for err in errors:
                flash(err, 'error')

        return redirect(url_for('recruiter.upload_cv'))

    db = get_db()
    cvs = db.execute(
        "SELECT id, filename, file_path, extracted_skills, uploaded_at, experience_months FROM cvs ORDER BY uploaded_at DESC"
    ).fetchall()

    return render_template('upload_cv.html', cvs=cvs)

@recruiter_bp.route('/job-analysis', methods=['GET', 'POST'])
def job_analysis():

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        custom_skills = request.form.get('custom_skills', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()

        if linkedin_url:
            if not validate_linkedin_url(linkedin_url):
                flash('Geçersiz LinkedIn URL formatı.', 'error')
                return redirect(request.url)

            scrape_res = scrape_linkedin_job(linkedin_url)
            if not scrape_res['success']:
                flash('LinkedIn ilanı çekilemedi: ' + scrape_res.get('error', 'Hata'), 'error')
                return redirect(request.url)

            title = scrape_res['title']
            description = scrape_res['description']

            custom_skills = ""

        if not title:
            flash('İş ilanı başlığı boş olamaz.', 'error')
            return redirect(request.url)

        if not description:
            flash('İş ilanı açıklaması boş olamaz.', 'error')
            return redirect(request.url)

        try:

            cleaned_desc = clean_text(description)

            extracted_skills = current_app.extensions["nlp_engine"].extract_skills(description)

            if custom_skills:
                user_skills = [s.strip().lower() for s in custom_skills.split(',') if s.strip()]
                extracted_skills = sorted(list(set(extracted_skills + user_skills)))

            job_reqs = current_app.extensions["nlp_engine"].extract_job_requirements(description)
            must_have = job_reqs['must_have_skills']
            nice_to_have = job_reqs['nice_to_have_skills']

            if custom_skills:
                for s in user_skills:
                    if s not in must_have:
                        must_have.append(s)
                must_have = sorted(list(set(must_have)))

            embedding = current_app.extensions["nlp_engine"].encode_text(description)

            job_id = str(uuid.uuid4())
            db = get_db()
            db.execute(
                """INSERT INTO jobs (id, title, description, cleaned_description,
                   required_skills, must_have_skills, nice_to_have_skills,
                   embedding, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job_id, title, description, cleaned_desc,
                 json.dumps(extracted_skills),
                 json.dumps(must_have),
                 json.dumps(nice_to_have),
                 embedding_to_bytes(embedding),
                 datetime.now().isoformat())
            )
            db.commit()

            must_count = len(must_have)
            nice_count = len(nice_to_have)
            total = len(extracted_skills)
            flash(
                f'İş ilanı "{title}" kaydedildi! '
                f'{total} yetenek tespit edildi '
                f'({must_count} zorunlu, {nice_count} tercih edilen).',
                'success'
            )
            return redirect(url_for('recruiter.job_analysis'))

        except Exception as e:
            flash(f'Hata: {str(e)}', 'error')
            return redirect(request.url)

    db = get_db()
    jobs = db.execute(
        "SELECT id, title, required_skills, must_have_skills, description, created_at FROM jobs ORDER BY created_at DESC"
    ).fetchall()

    return render_template('job_analysis.html', jobs=jobs)

@recruiter_bp.route('/match/<job_id>', methods=['POST'])
def run_match(job_id):

    db = get_db()

    job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        flash('İş ilanı bulunamadı.', 'error')
        return redirect(url_for('recruiter.job_analysis'))

    cvs = db.execute("SELECT * FROM cvs").fetchall()
    if not cvs:
        flash('Henüz yüklenmiş CV bulunmuyor. Önce CV yükleyin.', 'error')
        return redirect(url_for('recruiter.upload_cv'))

    db.execute("DELETE FROM matches WHERE job_id = ?", (job_id,))

    for cv_row in cvs:

        cv = dict(cv_row)

        cv_metadata = json.loads(cv.get('metadata') or '{}')
        pdf_warnings = cv_metadata.get('warnings', [])

        ats_result = current_app.extensions["nlp_engine"].calculate_ats_score(
            cv_text=cv.get('original_text', ''),
            job_description=job['description'],
            pdf_warnings=pdf_warnings
        )

        job_skills = current_app.extensions["nlp_engine"].extract_skills(job['description'])
        cv_skills = json.loads(cv.get('extracted_skills', '[]'))
        gap = current_app.extensions["nlp_engine"].semantic_gap_analysis(job_skills, cv_skills)

        match_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO matches (
                id, job_id, cv_id, match_score, matching_skills,
                semantic_matches, missing_skills, extra_skills,
                timeline_gaps, experience_score, coverage_percent,
                text_similarity, format_score, keyword_score,
                section_score, language_match, missing_must_haves,
                sections_found, cv_lang, job_lang, title_match_bonus,
                is_disqualified, penalty_applied, is_pretty_resume, detail_metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                match_id, job_id, cv['id'], ats_result['final_score'],
                json.dumps(gap['exact_matches']),
                json.dumps(gap['semantic_matches']),
                json.dumps(gap['missing_skills']),
                json.dumps(gap['extra_skills']),
                json.dumps(cv.get('gaps_detected', [])),
                0,
                gap['coverage_percent'],
                0,
                ats_result['format_score'],
                ats_result['keyword_score'],
                ats_result['section_score'],
                1 if ats_result['language_match'] else 0,
                json.dumps(ats_result['missing_must_haves']),
                json.dumps(ats_result['sections_found']),
                ats_result['cv_lang'],
                ats_result['job_lang'],
                ats_result['title_match_bonus'],
                ats_result['is_disqualified'],
                ats_result['penalty_applied'],
                ats_result['is_pretty_resume'],
                json.dumps(ats_result['detail_metrics'])
            )
        )

    db.commit()
    return redirect(url_for('recruiter.results', job_id=job_id))

@recruiter_bp.route('/results/<job_id>')
def results(job_id):

    db = get_db()

    job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        flash('İş ilanı bulunamadı.', 'error')
        return redirect(url_for('recruiter.index'))

    matches = db.execute("""
        SELECT m.*, c.filename, c.extracted_skills as cv_skills, c.experience_months
        FROM matches m
        JOIN cvs c ON m.cv_id = c.id
        WHERE m.job_id = ?
        ORDER BY m.is_disqualified ASC, m.match_score DESC
    """, (job_id,)).fetchall()

    return render_template('results.html', job=job, matches=matches)

@recruiter_bp.route('/api/delete-cv/<cv_id>', methods=['DELETE'])
def delete_cv(cv_id):

    db = get_db()
    cv = db.execute("SELECT file_path FROM cvs WHERE id = ?", (cv_id,)).fetchone()
    if not cv:
        return jsonify({'success': False, 'message': 'CV bulunamadı.'}), 404

    filepath = get_upload_path(cv['file_path'])
    staged_path = None
    try:
        db.execute('BEGIN')
        db.execute("DELETE FROM matches WHERE cv_id = ?", (cv_id,))
        db.execute("DELETE FROM cvs WHERE id = ?", (cv_id,))

        if filepath and filepath.is_file():
            staged_path = filepath.with_name(f'.deleting-{uuid.uuid4().hex}-{filepath.name}')
            filepath.replace(staged_path)

        db.commit()
    except (OSError, sqlite3.Error):
        db.rollback()
        if staged_path and staged_path.exists():
            try:
                staged_path.replace(filepath)
            except OSError:
                current_app.logger.exception('Unable to restore CV file after database deletion failure')
        current_app.logger.exception('CV deletion failed')
        return jsonify({'success': False, 'message': 'CV silinemedi. Lütfen tekrar deneyin.'}), 500

    if staged_path:
        try:
            staged_path.unlink()
        except OSError:
            current_app.logger.exception('CV database records deleted but staged file cleanup failed')
            return jsonify({
                'success': True,
                'message': 'CV silindi; dosya temizliği başarısız oldu. Sistem yöneticisine başvurun.',
                'cleanup_pending': True,
            })

    return jsonify({'success': True, 'message': 'CV silindi.'})

@recruiter_bp.route('/api/delete-job/<job_id>', methods=['DELETE'])
def delete_job(job_id):

    db = get_db()
    db.execute("DELETE FROM matches WHERE job_id = ?", (job_id,))
    db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    db.commit()
    return jsonify({'success': True, 'message': 'İş ilanı silindi.'})

@recruiter_bp.route('/download_cv/<cv_id>')
def download_cv_file(cv_id):

    db = get_db()
    cv = db.execute("SELECT file_path, filename FROM cvs WHERE id = ?", (cv_id,)).fetchone()
    if not cv or not cv['file_path']:
        flash('Dosya bulunamadı veya eski bir CV olduğu için silinmiş.', 'error')
        return redirect(url_for('recruiter.upload_cv'))

    filepath = get_upload_path(cv['file_path'])
    if not filepath or not filepath.is_file():
        flash('Fiziksel dosya sunucuda bulunamadı.', 'error')
        return redirect(url_for('recruiter.upload_cv'))

    from flask import send_from_directory
    return send_from_directory(filepath.parent, filepath.name, as_attachment=True, download_name=cv['filename'])

@recruiter_bp.route('/api/stats')
def api_stats():

    db = get_db()
    return jsonify({
        'cv_count': db.execute("SELECT COUNT(*) FROM cvs").fetchone()[0],
        'job_count': db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        'match_count': db.execute("SELECT COUNT(DISTINCT job_id) FROM matches").fetchone()[0],
    })

@recruiter_bp.app_template_filter('parse_json')
def parse_json_filter(value):

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

@recruiter_bp.app_template_filter('format_date')
def format_date_filter(value):

    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime('%d.%m.%Y %H:%M')
    except (ValueError, TypeError):
        return value

