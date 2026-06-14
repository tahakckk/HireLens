# HireLens - Akıllı Semantik Tarama ve Özgeçmiş Optimizasyon Platformu

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SentenceTransformers](https://img.shields.io/badge/Sentence--Transformers-SBERT-orange.svg)](https://sbert.net/)
[![spaCy](https://img.shields.io/badge/spaCy-3.5%2B-green.svg?logo=spacy&logoColor=white)](https://spacy.io/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-blue.svg?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)
[![English README](https://img.shields.io/badge/README-English-blue.svg)](README.md)

HireLens; veri gizliliğini koruyan, tamamen yerel (local-first) çalışan bir Yeni Nesil Başvuru Takip (ATS) ve Özgeçmiş Optimizasyon platformudur. Harici bulut LLM API'lerine bağımlı olmadan, Sentence-BERT gömmeleri (embeddings) ve spaCy varlık tanıma (NER) modellerini kullanarak bağlamsal tarama, semantik eşleştirme ve dosya yapısı denetimi gerçekleştirir.

---

## İçindekiler
1. [Proje Mimarisi](#proje-mimarisi)
2. [Öne Çıkan Özellikler](#öne-çıkan-özellikler)
3. [Kullanılan Teknolojiler](#kullanılan-teknolojiler)
4. [Arayüz Önizlemeleri](#arayüz-önizlemeleri)
5. [Adım Adım Kurulum Rehberi](#adım-adım-kurulum-rehberi)
6. [Çalıştırma Yönergesi](#çalıştırma-yönergesi)
7. [Veritabanı Şeması](#veritabanı-şeması)
8. [Kod Yorum Satırları (Hatırlatıcı Notlar)](#kod-yorum-satırları-hatırlatıcı-notlar)
9. [Lisans](#lisans)

---

## Proje Mimarisi

Sistem, iki taraflı (Aday ve İK Uzmanı) bir panel yapısına sahiptir:

```
[Aday Paneli]                    [İK Uzmanı Paneli]
      │                                  │
      ▼                                  ▼
┌────────────────────────────────────────────────────────┐
│                      Flask App                         │
└──────────────────────────┬─────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
┌──────────────┐                       ┌──────────────┐
│  NLP Motoru  │                       │ Dosya Okuyucu│
│  - SBERT     │                       │ - PyMuPDF    │
│  - spaCy NER │                       │ - python-docx│
└──────┬───────┘                       └──────┬───────┘
       │                                      │
       └──────────────────┬───────────────────┘
                          ▼
                  ┌──────────────┐
                  │ SQLite DB    │
                  │ - Embeddings │
                  │ - Gaps / ATS │
                  └──────────────┘
```

---

## Öne Çıkan Özellikler

### 1. Çift Yönlü İK Modülü
* **İK Paneli:** İK uzmanlarının iş ilanlarını sisteme tanımlamasına (veya LinkedIn'den otomatik çekmesine), başvuran adayların klasörünü tek seferde içe aktarmasına ve semantik olarak sıralanmış aday listesini görüntülemesine imkan tanır.
* **Aday Paneli:** İş arayanların kendi CV'lerini yükleyerek hedef ilana göre Scorecard denetiminden geçirmesine, biçimlendirme hatalarını görmesine ve ATS dostu, tek sütunlu optimize bir PDF çıktısı almasına olanak sağlar.

### 2. Semantik Eşleştirme ve SBERT
Geleneksel kelime eşleştirme sistemlerinin aksine (örneğin ilanda "Derin Öğrenme" arandığında aday CV'sindeki "Yapay Sinir Ağları" ifadesini kaçıran sistemler), HireLens Sentence-BERT (`paraphrase-multilingual-MiniLM-L12-v2`) modelini kullanır. CV ve iş tanımlarını 384 boyutlu vektör uzayına taşıyarak **Kosinüs Benzerliği (Cosine Similarity)** ile anlam ilişkisi kurar.

### 3. Scorecard 4.0 Değerlendirme Modeli
Her özgeçmiş, 4 temel kritere göre **100 puan** üzerinden değerlendirilir:
* **Görsel Düzen ve Parse Edilebilirlik (Max 40 Puan):** Çift sütunlu Canva şablonları gibi okuma sırasını bozan formatları tespit eder. Çift sütun tespiti halinde **15 puan ceza puanı (visual tax)** ve belgedeki uyarılar (eksik email, okunmayan karakter vb.) için **her uyarı başına -4 puan** kesinti uygular.
* **Bölüm Tamlığı (Max 20 Puan):** Özet, Deneyim, Eğitim, Yetenekler ve Sertifikalar bölümlerinin semantik varlığını kontrol eder. Her mevcut bölüm için **+4 puan** ekler.
* **Anahtar Kelime ve Rol Uyumu (Max 40 Puan):** Adayın son unvanı ile hedef iş unvanının semantik benzerliğini (SBERT) ve yetenek yoğunluğunu ölçer.
* **Diskalifiye Çarpanı:** İlanda belirtilen zorunlu (Must-Have) yeteneklerden eksik olan her bir madde için toplam puanı **%25 oranında düşürür** (taban sınır 0.2'dir).
* **Dil Bariyeri Cezası:** CV dili ile iş ilanı dilinin uyuşmaması durumunda toplam puandan **%10** kesinti yapar.

### 4. Dinamik Sütun Bölme Algoritması
Standart PDF okuyucular soldan sağa okuma yaptıkları için iki sütunlu belgelerde satırları birbirine karıştırır. HireLens, sayfa üzerinde **Gutter (Sütun Boşluğu) Analizi** yaparak sayfayı dikey olarak böler. Böylece sol ve sağ sütunlar birbirine karışmadan, doğru sırada metne dönüştürülür.

### 5. Halüsinasyonsuz CV Optimizasyonu
Adayın deneyimlerini baştan yazıp asılsız projeler veya unvanlar uyduran üretken yapay zekaların (Generative LLM'ler) aksine, HireLens **extractive (çıkarımsal)** bir yaklaşım kullanır. Adayın kendi cümlelerini iş ilanına benzerliklerine göre ağırlıklandırıp sıralar ve en alakalı başarıları en üste taşıyarak **ReportLab** ile standart ATS formatında temiz bir PDF üretir.

---

## Kullanılan Teknolojiler
* **Backend Framework:** Flask 3.0+
* **Vektör Kodlama:** SentenceTransformers (SBERT)
* **Varlık Tanıma (NER):** spaCy (EntityRuler eklentisiyle)
* **Dosya Ayrıştırma:** PyMuPDF (fitz), python-docx
* **PDF Oluşturma:** ReportLab
* **Veritabanı:** SQLite (WAL modunda eşzamanlı kilit engelleme aktiftir)

---

## Arayüz Önizlemeleri

### İK Sıralama ve Semantik Analiz Paneli
![Recruiter Ranking](screenshots/recutier_analysis.PNG)
*Adayların eşleşme oranları, eksik yetenekleri ve detaylı puan analizlerinin gösterildiği liste görünümü.*

### Aday Puan Kartı ve Öneri Arayüzü
![Candidate Portal](screenshots/candidate_portal.png)
*Özgeçmiş format uyarıları, eksik zorunlu yetenekler ve puan artırma ipuçlarını içeren analiz paneli.*

### İş İlanı Analiz Ekranı
![Job Analysis](screenshots/job_analysis.png)
*LinkedIn linkinden ilan bilgilerinin parse edilerek zorunlu ve tercih edilen yeteneklerin ayrıştırıldığı ekran.*

### Ana Yönetim Paneli
![Dashboard](screenshots/dashboard.PNG)
*Aktif iş ilanları ve aday sayılarını gösteren operasyonel gösterge paneli.*

---

## Adım Adım Kurulum Rehberi

Bu rehber, herhangi bir yazılım tecrübesi olmayan kullanıcıların bile uygulamayı **Windows** bilgisayarlarında kolayca çalıştırmaları için hazırlanmıştır.

### Adım 1: Python Kurulumu
1. Resmi web sitesinden **Python 3.10** veya daha yeni bir sürümü indirin: [Python İndir](https://www.python.org/downloads/).
2. Yükleyiciyi çalıştırın.
3. **ÇOK ÖNEMLİ:** Yükleyicinin ilk ekranında en altta yer alan **"Add python.exe to PATH"** (Python'ı PATH'e ekle) kutucuğunu işaretleyin. Bunu işaretlemezseniz komut satırı araçları çalışmayacaktır.
4. Kurulum adımlarını tamamlayın.

### Adım 2: Projeyi Klonlama ve Dizine Geçiş
1. Projeyi Git ile klonlayın (veya ZIP olarak indirip klasöre çıkartın):
   ```cmd
   git clone https://github.com/tahakckk/HireLens.git
   ```
2. Komut satırını açıp proje dizinine geçiş yapın:
   ```cmd
   cd HireLens
   ```

### Adım 3: Sanal Ortam (Virtual Environment) Oluşturma
Projenin ihtiyaç duyduğu paketlerin bilgisayarınızdaki diğer yazılımları etkilememesi için izole bir ortam oluşturun:
```cmd
python -m venv venv
```

Oluşturulan sanal ortamı aktif edin:
```cmd
venv\Scripts\activate
```
*(Komut satırının başında `(venv)` ifadesi belirecektir).*

### Adım 4: Gerekli Paketleri Yükleme
Uygulamanın çalışması için gereken tüm kütüphaneleri otomatik yükleyin:
```cmd
pip install -r requirements.txt
```
*(Bu işlem internet hızınıza bağlı olarak 2-4 dakika sürebilir; SentenceTransformers ve spaCy gibi büyük veri işleme paketleri kurulacaktır).*

### Adım 5: spaCy Dil Modelini İndirme
Aşağıdaki komutla kelime analizi yapacak spaCy modelini indirin:
```cmd
python -m spacy download en_core_web_sm
```

---

## Çalıştırma Yönergesi

1. Sanal ortamınızın aktif olduğundan emin olun (satırın başında `(venv)` yazmalıdır).
2. Uygulamayı başlatın:
   ```cmd
   python app.py
   ```
3. Terminalde şu şekilde bir çıktı göreceksiniz:
   ```
   ==================================================
     HireLens - Semantic Talent Matcher & ATS Engine
     Server running at: http://localhost:5000
   ==================================================
   ```
4. Tarayıcınızı açın (Chrome, Edge vb.) ve şu adrese gidin:
   [http://localhost:5000](http://localhost:5000)

---

## Veritabanı Şeması

Uygulama ilk kez çalıştığında SQLite veritabanı otomatik olarak oluşturulur. Tabloların yapısı:

* **`cvs`:** Yüklenen CV metinlerini, NFKC normalizasyonu yapılmış halini, çıkarılan yetenek ve tarihleri, deneyim sürelerini ve SBERT vektör gömmelerini (`BLOB` formatında) saklar.
* **`jobs`:** İlan açıklamalarını, başlıklarını, zorunlu/tercih edilen yetenek listelerini ve ilan vektör gömmelerini tutar.
* **`matches`:** Her aday ile ilan arasındaki Kosinüs Benzerliğini, görsel format puanını, eksik must-have yeteneklerin listesini ve dil eşleşme cezalarını kaydeder.
* **`user_profiles`:** Adayların temel profil verilerini ilişkilendirir.
* **`job_search_sessions`:** Adayın gerçekleştirdiği CV optimizasyon oturumlarını ve üretilen Word/PDF belgelerinin verilerini tutar.

---

## Kod Yorum Satırları (Hatırlatıcı Notlar)

Akademik sunumlar, kod savunmaları ve jüri değerlendirmeleri için kod içerisindeki karmaşık ve gereksiz yorum satırları temizlenmiştir. Bunların yerine, sunum anında size rehberlik etmesi amacıyla **`# NOT:`** ön ekiyle başlayan **kısa Türkçe notlar** eklenmiştir.

Bu notlar sunum esnasında kod düzeyinde şu konuları hızlıca açıklamanıza yardımcı olur:
* [app.py](file:///c:/Users/yigit/Desktop/bittirme%20hoca%20dedin/app.py) dosyasında SQLite bağlantısı kurulurken eşzamanlılığı artıran **WAL (Write-Ahead Logging)** modunun açılması.
* [file_parser.py](file:///c:/Users/yigit/Desktop/bittirme%20hoca%20dedin/file_parser.py) dosyasındaki **Dinamik Gutter ve Sütun Bölme Algoritması** koordinat hesaplamaları.
* [nlp_engine.py](file:///c:/Users/yigit/Desktop/bittirme%20hoca%20dedin/nlp_engine.py) dosyasında SBERT modeli yüklenmesi ve **Kosinüs Benzerliği** normları.
* [nlp_engine.py](file:///c:/Users/yigit/Desktop/bittirme%20hoca%20dedin/nlp_engine.py) dosyasındaki **Canva görsel düzeni 15p ceza puanı (visual tax)** kesintileri.
* [extractive_cv.py](file:///c:/Users/yigit/Desktop/bittirme%20hoca%20dedin/extractive_cv.py) dosyasında adayın kendi cümlelerini ağırlıklandırırken kullanılan **%50 semantik benzerlik, %30 yetenek, %20 unvan uyumu katsayıları**.

---

## Lisans

Bu proje MIT Lisansı altında dağıtılmaktadır. Detaylar için `LICENSE` dosyasına göz atabilirsiniz.
