import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    # NOT: Flask oturum güvenliği ve şifreleme için kullanılan gizli anahtar
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-jobs-match-secret-2024')
    
    # NOT: Yüklenen CV'lerin geçici olarak saklanacağı klasör yolu
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    
    # NOT: Aday ve iş eşleşme verilerinin kaydedileceği SQLite veritabanı dosyası
    DATABASE = os.path.join(BASE_DIR, 'database.db')
    
    # NOT: Maksimum yüklenebilir dosya boyutu (16 MB limit)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # NOT: Kabul edilen CV dosya formatları
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
    
    # NOT: Semantik benzerlik hesaplamasında yerel olarak çalıştırılan Sentence-BERT modeli
    SBERT_MODEL = 'paraphrase-multilingual-MiniLM-L12-v2'
    
    # NOT: Metin içerisindeki yetenek anahtar kelimelerini tanımak için kullanılan spaCy modeli
    SPACY_MODEL = 'en_core_web_sm'
