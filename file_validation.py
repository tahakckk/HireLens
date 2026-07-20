"""Validation helpers for uploaded CV files."""

import os
import zipfile


def validate_cv_file(file_path: str) -> bool:
    """Verify the declared PDF/DOCX type matches the file's actual structure."""
    extension = os.path.splitext(file_path)[1].lower()

    if extension == '.pdf':
        with open(file_path, 'rb') as uploaded_file:
            return uploaded_file.read(5) == b'%PDF-'

    if extension == '.docx':
        try:
            with zipfile.ZipFile(file_path) as archive:
                names = set(archive.namelist())
                return '[Content_Types].xml' in names and 'word/document.xml' in names
        except (OSError, zipfile.BadZipFile):
            return False

    return False
