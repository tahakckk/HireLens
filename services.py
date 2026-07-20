"""Application services that coordinate persistence and external side effects."""

import sqlite3
import uuid

from repositories import RecruiterRepository


def delete_cv_with_file(cv_id, resolve_upload_path, logger, repository=None):
    """Delete a CV atomically while keeping its upload recoverable until commit."""
    repository = repository or RecruiterRepository()
    cv = repository.find_cv_file(cv_id)
    if not cv:
        return {"success": False, "message": "CV bulunamadı."}, 404

    filepath = resolve_upload_path(cv["file_path"])
    staged_path = None
    try:
        repository.begin_delete_cv(cv_id)
        if filepath and filepath.is_file():
            staged_path = filepath.with_name(
                f".deleting-{uuid.uuid4().hex}-{filepath.name}"
            )
            filepath.replace(staged_path)
        repository.commit()
    except (OSError, sqlite3.Error):
        repository.rollback()
        if staged_path and staged_path.exists():
            try:
                staged_path.replace(filepath)
            except OSError:
                logger.exception(
                    "Unable to restore CV file after database deletion failure"
                )
        logger.exception("CV deletion failed")
        return {
            "success": False,
            "message": "CV silinemedi. Lütfen tekrar deneyin.",
        }, 500

    if staged_path:
        try:
            staged_path.unlink()
        except OSError:
            logger.exception(
                "CV database records deleted but staged file cleanup failed"
            )
            return {
                "success": True,
                "message": (
                    "CV silindi; dosya temizliği başarısız oldu. "
                    "Sistem yöneticisine başvurun."
                ),
                "cleanup_pending": True,
            }, 200

    return {"success": True, "message": "CV silindi."}, 200
