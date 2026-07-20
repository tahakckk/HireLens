"""Named persistence operations for recruiter and job-search workflows."""

from database import get_db


class RecruiterRepository:
    def __init__(self, connection=None):
        self.db = connection or get_db()

    def dashboard(self):
        return {
            **self.stats(),
            "recent_cvs": self.db.execute(
                "SELECT id, filename, extracted_skills, uploaded_at "
                "FROM cvs ORDER BY uploaded_at DESC LIMIT 5"
            ).fetchall(),
            "recent_jobs": self.db.execute(
                "SELECT id, title, required_skills, created_at "
                "FROM jobs ORDER BY created_at DESC LIMIT 5"
            ).fetchall(),
        }

    def stats(self):
        return {
            "cv_count": self.db.execute("SELECT COUNT(*) FROM cvs").fetchone()[0],
            "job_count": self.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
            "match_count": self.db.execute(
                "SELECT COUNT(DISTINCT job_id) FROM matches"
            ).fetchone()[0],
        }

    def list_cvs(self):
        return self.db.execute(
            "SELECT id, filename, file_path, extracted_skills, uploaded_at, "
            "experience_months FROM cvs ORDER BY uploaded_at DESC"
        ).fetchall()

    def list_all_cvs(self):
        return self.db.execute("SELECT * FROM cvs").fetchall()

    def find_cv_file(self, cv_id):
        return self.db.execute(
            "SELECT file_path, filename FROM cvs WHERE id = ?", (cv_id,)
        ).fetchone()

    def create_cv(self, cv):
        self.db.execute(
            """INSERT INTO cvs (id, filename, file_path, original_text, cleaned_text,
               extracted_skills, timeline, experience_months, skill_recency,
               metadata, embedding, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cv["id"], cv["filename"], cv["file_path"], cv["original_text"],
                cv["cleaned_text"], cv["extracted_skills"], cv["timeline"],
                cv["experience_months"], cv["skill_recency"], cv["metadata"],
                cv["embedding"], cv["uploaded_at"],
            ),
        )
        self.db.commit()

    def list_jobs(self):
        return self.db.execute(
            "SELECT id, title, required_skills, must_have_skills, description, "
            "created_at FROM jobs ORDER BY created_at DESC"
        ).fetchall()

    def find_job(self, job_id):
        return self.db.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()

    def create_job(self, job):
        self.db.execute(
            """INSERT INTO jobs (id, title, description, cleaned_description,
               required_skills, must_have_skills, nice_to_have_skills,
               embedding, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job["id"], job["title"], job["description"],
                job["cleaned_description"], job["required_skills"],
                job["must_have_skills"], job["nice_to_have_skills"],
                job["embedding"], job["created_at"],
            ),
        )
        self.db.commit()

    def replace_matches(self, job_id, matches):
        self.db.execute("DELETE FROM matches WHERE job_id = ?", (job_id,))
        for match in matches:
            self.db.execute(
                """INSERT INTO matches (
                    id, job_id, cv_id, match_score, matching_skills,
                    semantic_matches, missing_skills, extra_skills,
                    timeline_gaps, experience_score, coverage_percent,
                    text_similarity, format_score, keyword_score, section_score,
                    language_match, missing_must_haves, sections_found, cv_lang,
                    job_lang, title_match_bonus, is_disqualified, penalty_applied,
                    is_pretty_resume, detail_metrics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                tuple(match[key] for key in (
                    "id", "job_id", "cv_id", "match_score", "matching_skills",
                    "semantic_matches", "missing_skills", "extra_skills",
                    "timeline_gaps", "experience_score", "coverage_percent",
                    "text_similarity", "format_score", "keyword_score",
                    "section_score", "language_match", "missing_must_haves",
                    "sections_found", "cv_lang", "job_lang", "title_match_bonus",
                    "is_disqualified", "penalty_applied", "is_pretty_resume",
                    "detail_metrics",
                )),
            )
        self.db.commit()

    def list_matches_for_job(self, job_id):
        return self.db.execute(
            """SELECT m.*, c.filename, c.extracted_skills AS cv_skills,
                      c.experience_months
               FROM matches m JOIN cvs c ON m.cv_id = c.id
               WHERE m.job_id = ?
               ORDER BY m.is_disqualified ASC, m.match_score DESC""",
            (job_id,),
        ).fetchall()

    def begin_delete_cv(self, cv_id):
        self.db.execute("BEGIN")
        self.db.execute("DELETE FROM matches WHERE cv_id = ?", (cv_id,))
        self.db.execute("DELETE FROM cvs WHERE id = ?", (cv_id,))

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def delete_job(self, job_id):
        self.db.execute("DELETE FROM matches WHERE job_id = ?", (job_id,))
        self.db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        self.db.commit()


class JobSearchRepository:
    def __init__(self, connection=None):
        self.db = connection or get_db()

    def list_profiles(self):
        return self.db.execute(
            "SELECT id, original_filename, extracted_skills, created_at "
            "FROM user_profiles ORDER BY created_at DESC"
        ).fetchall()

    def list_recent_sessions(self, limit=10):
        return self.db.execute(
            """SELECT s.*, p.original_filename
               FROM job_search_sessions s
               JOIN user_profiles p ON s.profile_id = p.id
               ORDER BY s.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()

    def create_profile(self, profile):
        self.db.execute(
            """INSERT INTO user_profiles (id, original_filename, original_text,
               profile_data, extracted_skills, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                profile["id"], profile["original_filename"],
                profile["original_text"], profile["profile_data"],
                profile["extracted_skills"], profile["created_at"],
            ),
        )
        self.db.commit()

    def find_profile(self, profile_id):
        return self.db.execute(
            "SELECT * FROM user_profiles WHERE id = ?", (profile_id,)
        ).fetchone()

    def create_session(self, session):
        self.db.execute(
            """INSERT INTO job_search_sessions (id, profile_id, job_url,
               job_data, optimized_cv, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session["id"], session["profile_id"], session["job_url"],
                session["job_data"], session["optimized_cv"],
                session["status"], session["created_at"],
            ),
        )
        self.db.commit()

    def find_session(self, session_id):
        return self.db.execute(
            "SELECT * FROM job_search_sessions WHERE id = ?", (session_id,)
        ).fetchone()

    def delete_profile(self, profile_id):
        self.db.execute(
            "DELETE FROM job_search_sessions WHERE profile_id = ?", (profile_id,)
        )
        self.db.execute("DELETE FROM user_profiles WHERE id = ?", (profile_id,))
        self.db.commit()

    def delete_session(self, session_id):
        self.db.execute(
            "DELETE FROM job_search_sessions WHERE id = ?", (session_id,)
        )
        self.db.commit()
