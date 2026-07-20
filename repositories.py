"""Database repositories. SQL is intentionally contained in this module."""
class BaseRepository:
    def __init__(self, db):
        self._db = db
    def execute(self, statement, params=()):
        return self._db.execute(statement, params)
    def commit(self):
        self._db.commit()
    def rollback(self):
        self._db.rollback()

class RecruiterRepository(BaseRepository):
    pass

class JobSearchRepository(BaseRepository):
    pass
