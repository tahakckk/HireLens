import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    # Flask oturum güvenliği ve şifreleme için kullanılan gizli anahtar.
    # Bu değer yalnızca çalışma ortamından sağlanmalıdır; kaynak kodda fallback yoktur.
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
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

    # Downloaded transformer files survive application restarts in this directory.
    MODEL_CACHE_DIR = os.environ.get(
        'MODEL_CACHE_DIR', os.path.join(BASE_DIR, '.model-cache')
    )

    @classmethod
    def validate(cls):
        """Fail closed instead of starting production with an insecure session key."""
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
            raise RuntimeError(
                'SECRET_KEY ortam değişkeni en az 32 karakterlik güvenli bir değer olmalıdır.'
            )
