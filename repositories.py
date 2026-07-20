"""All SQL access for HireLens."""


class RecruiterRepository:
    def __init__(self, db):
        self.db = db

    def dashboard_stats(self):
        return {
            "cv_count": self.db.execute("SELECT COUNT(*) FROM cvs").fetchone()[0],
            "job_count": self.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
            "match_count": self.db.execute("SELECT COUNT(DISTINCT job_id) FROM matches").fetchone()[0],
        }

    def recent_cvs(self):
        return self.db.execute(
            "SELECT id, filename, extracted_skills, uploaded_at FROM cvs ORDER BY uploaded_at DESC LIMIT 5"
        ).fetchall()

    def recent_jobs(self):
        return self.db.execute(
            "SELECT id, title, required_skills, created_at FROM jobs ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

    def list_cvs(self):
        return self.db.execute(
            "SELECT id, filename, file_path, extracted_skills, uploaded_at, experience_months FROM cvs ORDER BY uploaded_at DESC"
        ).fetchall()

    def create_cv(self, values):
        self.db.execute(
            "INSERT INTO cvs (id, filename, file_path, original_text, cleaned_text, extracted_skills, timeline, experience_months, skill_recency, metadata, embedding, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        self.db.commit()

    def list_jobs(self):
        return self.db.execute(
            "SELECT id, title, required_skills, must_have_skills, description, created_at FROM jobs ORDER BY created_at DESC"
        ).fetchall()

    def create_job(self, values):
        self.db.execute(
            "INSERT INTO jobs (id, title, description, cleaned_description, required_skills, must_have_skills, nice_to_have_skills, embedding, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        self.db.commit()

    def find_job(self, job_id):
        return self.db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    def list_cvs_for_matching(self):
        return self.db.execute("SELECT * FROM cvs").fetchall()

    def replace_matches(self, job_id, matches):
        self.db.execute("DELETE FROM matches WHERE job_id = ?", (job_id,))
        self.db.executemany(
            "INSERT INTO matches (id, job_id, cv_id, match_score, matching_skills, semantic_matches, missing_skills, extra_skills, timeline_gaps, experience_score, coverage_percent, text_similarity, format_score, keyword_score, section_score, language_match, missing_must_haves, sections_found, cv_lang, job_lang, title_match_bonus, is_disqualified, penalty_applied, is_pretty_resume, detail_metrics) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            matches,
        )
        self.db.commit()

    def get_results(self, job_id):
        return self.db.execute(
            "SELECT m.*, c.filename, c.extracted_skills as cv_skills, c.experience_months FROM matches m JOIN cvs c ON m.cv_id = c.id WHERE m.job_id = ? ORDER BY m.is_disqualified ASC, m.match_score DESC",
            (job_id,),
        ).fetchall()

    def find_cv_file(self, cv_id):
        return self.db.execute("SELECT file_path, filename FROM cvs WHERE id = ?", (cv_id,)).fetchone()

    def begin_delete_cv(self, cv_id):
        self.db.execute("BEGIN")
        self.db.execute("DELETE FROM matches WHERE cv_id = ?", (cv_id,))
        self.db.execute("DELETE FROM cvs WHERE id = ?", (cv_id,))

    def commit_delete_cv(self):
        self.db.commit()

    def rollback_delete_cv(self):
        self.db.rollback()

    def delete_job(self, job_id):
        self.db.execute("DELETE FROM matches WHERE job_id = ?", (job_id,))
        self.db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        self.db.commit()


class JobSearchRepository:
    def __init__(self, db):
        self.db = db

    def execute(self, statement, params=()):
        return self.db.execute(statement, params)

    def commit(self):
        self.db.commit()

    def list_profiles(self):
        return self.db.execute(
            "SELECT id, original_filename, extracted_skills, created_at FROM user_profiles ORDER BY created_at DESC"
        ).fetchall()

    def list_sessions(self):
        return self.db.execute(
            "SELECT s.*, p.original_filename FROM job_search_sessions s JOIN user_profiles p ON s.profile_id = p.id ORDER BY s.created_at DESC LIMIT 10"
        ).fetchall()

    def create_profile(self, values):
        self.db.execute(
            "INSERT INTO user_profiles (id, original_filename, original_text, profile_data, extracted_skills, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            values,
        )
        self.db.commit()

    def get_profile(self, profile_id):
        return self.db.execute("SELECT * FROM user_profiles WHERE id = ?", (profile_id,)).fetchone()

    def create_session(self, values):
        self.db.execute(
            "INSERT INTO job_search_sessions (id, profile_id, job_url, job_data, optimized_cv, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        self.db.commit()

    def find_session(self, session_id):
        return self.db.execute("SELECT * FROM job_search_sessions WHERE id = ?", (session_id,)).fetchone()

    def delete_session(self, session_id):
        self.db.execute("DELETE FROM job_search_sessions WHERE id = ?", (session_id,))
        self.db.commit()

    def delete_profile(self, profile_id):
        self.db.execute("DELETE FROM job_search_sessions WHERE profile_id = ?", (profile_id,))
        self.db.execute("DELETE FROM user_profiles WHERE id = ?", (profile_id,))
        self.db.commit()
