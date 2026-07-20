import os
import re
import numpy as np
import spacy
from datetime import datetime
from dateutil.relativedelta import relativedelta

os.environ['TRANSFORMERS_OFFLINE'] = '0'
os.environ['HF_HUB_OFFLINE'] = '0'

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

SKILL_DATABASE = [

    "python", "java", "javascript", "typescript", "c++", "c#", "c", "ruby", "go", "golang",
    "rust", "swift", "kotlin", "scala", "php", "perl", "r", "matlab", "dart", "lua",
    "objective-c", "shell", "bash", "powershell", "assembly", "fortran", "cobol",
    "visual basic", "haskell", "elixir", "clojure", "groovy",

    "react", "reactjs", "react.js", "angular", "angularjs", "vue", "vuejs", "vue.js",
    "next.js", "nextjs", "nuxt.js", "svelte", "django", "flask", "fastapi",
    "spring", "spring boot", "express", "express.js", "node.js", "nodejs",
    "asp.net", ".net", "dotnet", "rails", "ruby on rails", "laravel", "symfony",
    "jquery", "bootstrap", "tailwind", "tailwindcss", "material ui", "redux",

    "android", "ios", "react native", "flutter", "xamarin", "swiftui",
    "ionic", "cordova", "mobile development",

    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
    "oracle", "sqlite", "mariadb", "cassandra", "dynamodb", "firebase",
    "neo4j", "couchdb", "influxdb", "memcached", "database management",
    "database design", "database administration", "nosql", "graphql",

    "aws", "amazon web services", "azure", "microsoft azure", "gcp",
    "google cloud", "google cloud platform", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "jenkins", "gitlab ci", "github actions",
    "ci/cd", "devops", "cloud computing", "heroku", "digitalocean",
    "nginx", "apache", "linux", "unix", "windows server",
    "serverless", "lambda", "microservices", "service mesh",

    "machine learning", "deep learning", "artificial intelligence", "ai",
    "natural language processing", "nlp", "computer vision", "neural networks",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    "data analysis", "data science", "data engineering", "data mining",
    "data visualization", "big data", "hadoop", "spark", "apache spark",
    "pyspark", "airflow", "apache kafka", "kafka", "etl",
    "statistics", "regression", "classification", "clustering",
    "random forest", "xgboost", "gradient boosting", "svm",
    "support vector machine", "decision tree", "ensemble methods",
    "reinforcement learning", "transfer learning", "generative ai",
    "large language models", "llm", "transformers", "bert", "gpt",
    "hugging face", "langchain", "rag", "prompt engineering",
    "feature engineering", "model deployment", "mlops",
    "convolutional neural network", "cnn", "recurrent neural network", "rnn",
    "lstm", "gan", "autoencoder", "attention mechanism",
    "image recognition", "object detection", "speech recognition",
    "sentiment analysis", "text mining", "information retrieval",
    "recommendation system", "time series", "anomaly detection",
    "a/b testing", "hypothesis testing", "bayesian",
    "power bi", "tableau", "looker", "d3.js",
    "jupyter", "jupyter notebook", "google colab",

    "git", "github", "gitlab", "bitbucket", "svn",
    "agile", "scrum", "kanban", "jira", "confluence",
    "rest", "rest api", "restful", "api", "api design",
    "graphql", "grpc", "soap", "websocket",
    "unit testing", "integration testing", "test driven development", "tdd",
    "behavior driven development", "bdd", "selenium", "cypress",
    "jest", "pytest", "junit", "mocha",
    "design patterns", "solid principles", "clean code",
    "object oriented programming", "oop", "functional programming",
    "software architecture", "system design", "microservices architecture",

    "cybersecurity", "information security", "network security",
    "penetration testing", "ethical hacking", "vulnerability assessment",
    "owasp", "encryption", "ssl", "tls", "oauth", "jwt",
    "sso", "identity management", "firewall", "ids", "ips",
    "siem", "compliance", "gdpr", "iso 27001",

    "tcp/ip", "dns", "http", "https", "vpn", "routing",
    "switching", "load balancing", "cdn", "networking",

    "project management", "product management", "business analysis",
    "requirements gathering", "stakeholder management",
    "risk management", "change management", "strategic planning",
    "budgeting", "forecasting", "kpi", "okr",
    "lean", "six sigma", "prince2", "pmp",
    "crm", "erp", "sap", "salesforce",

    "communication", "leadership", "teamwork", "problem solving",
    "critical thinking", "analytical thinking", "creativity",
    "time management", "adaptability", "collaboration",
    "presentation", "negotiation", "mentoring", "coaching",

    "ui/ux", "user experience", "user interface", "ux design", "ui design",
    "figma", "sketch", "adobe xd", "photoshop", "illustrator",
    "wireframing", "prototyping", "responsive design", "accessibility",

    "excel", "microsoft office", "google workspace", "slack",
    "trello", "asana", "notion", "miro",
    "xml", "json", "yaml", "csv", "html", "css",
    "sass", "less", "webpack", "vite", "babel",
    "npm", "yarn", "pip", "maven", "gradle",
    "swagger", "postman", "insomnia",
    "rabbitmq", "celery", "webscraping", "web scraping",
    "beautifulsoup", "scrapy", "selenium",
    "blockchain", "smart contracts", "solidity", "web3",
    "iot", "embedded systems", "arduino", "raspberry pi",
    "robotics", "3d printing", "cad", "autocad",
    "unity", "unreal engine", "game development",
]

SOFT_SKILLS = [
    "communication", "leadership", "teamwork", "problem solving",
    "critical thinking", "analytical thinking", "creativity",
    "time management", "adaptability", "collaboration",
    "presentation", "negotiation", "mentoring", "coaching",
    "strategic thinking", "emotional intelligence", "conflict resolution",
    "interpersonal skills", "public speaking", "active listening",
    "decision making", "organizational skills", "customer service"
]

STANDARD_SECTIONS = {
    "summary": ["özet", "summary", "kariyer özeti", "professional summary", "career summary", "about", "hakkımda"],
    "experience": ["deneyim", "is deneyimi", "iş tecrübesi", "experience", "work experience", "employment", "iş geçmişi"],
    "education": ["eğitim", "eğitim bilgileri", "education", "academic background", "tahsil"],
    "skills": ["yetenekler", "beceriler", "skills", "technical skills", "teknik yetenekler", "yetkinlikler"],
    "certifications": ["sertifikalar", "nitelikler", "certifications", "certificates", "eğitimler ve sertifikalar"]
}

from text_utils import clean_text

class NLPEngine:

    def __init__(self, sbert_model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
                 spacy_model_name: str = 'en_core_web_sm'):
        self._sbert_model = None
        self._nlp = None
        self._sbert_model_name = sbert_model_name
        self._spacy_model_name = spacy_model_name
        self._skills_loaded = False

    @property
    def sbert_model(self) -> SentenceTransformer:
        # NOT: Yerel (Offline) Sentence-BERT modelini belleğe yüklüyoruz. İnternet yoksa yerelden yükleme dener.
        if self._sbert_model is None:
            print(f"[NLP Engine] SBERT modeli yükleniyor (Local-Only): {self._sbert_model_name}...")
            try:
                self._sbert_model = SentenceTransformer(self._sbert_model_name, local_files_only=True)
            except Exception as e:
                print(f"[NLP Engine] Yerel model bulunamadı veya yüklenemedi: {e}. Çevrimiçi deneniyor...")
                try:
                    os.environ['TRANSFORMERS_OFFLINE'] = '0'
                    os.environ['HF_HUB_OFFLINE'] = '0'
                    self._sbert_model = SentenceTransformer(self._sbert_model_name)
                    os.environ['TRANSFORMERS_OFFLINE'] = '1'
                    os.environ['HF_HUB_OFFLINE'] = '1'
                except Exception as e2:
                    print(f"[NLP Engine] KRİTİK HATA: Model hiçbir şekilde yüklenemedi: {e2}")
                    raise e2

            self._sbert_model.max_seq_length = 512
            self._sbert_model = self._sbert_model.to('cpu')
            print(f"[NLP Engine] SBERT modeli hazır. (max_seq_length={self._sbert_model.max_seq_length})")
        return self._sbert_model

    @property
    def nlp(self):
        # The language model is installed with the application dependencies.
        # Never download or silently downgrade the NLP pipeline during a request.
        if self._nlp is None:
            print(f"[NLP Engine] spaCy modeli yükleniyor: {self._spacy_model_name}...")
            try:
                self._nlp = spacy.load(self._spacy_model_name)
            except OSError as exc:
                raise RuntimeError(
                    f"Required spaCy model '{self._spacy_model_name}' is not installed. "
                    "Install the application requirements before starting HireLens."
                ) from exc

            if "entity_ruler" in self._nlp.pipe_names:
                self._nlp.remove_pipe("entity_ruler")

            # NOT: Yetenek veri tabanını (SKILL_DATABASE) spaCy NER (Named Entity Recognition) boru hattına ekliyoruz.
            ruler = self._nlp.add_pipe("entity_ruler", before="ner")
            patterns = []
            for skill in SKILL_DATABASE:
                if len(skill) > 1:
                    patterns.append({"label": "SKILL", "pattern": skill.lower()})
            ruler.add_patterns(patterns)
            self._skills_loaded = True
            print(f"[NLP Engine] spaCy hazır. {len(patterns)} yetenek pattern'ı yüklendi.")

        return self._nlp

    def extract_skills(self, text: str) -> list:

        cleaned = clean_text(text)
        doc = self.nlp(cleaned)
        skills = set()
        for ent in doc.ents:
            if ent.label_ == "SKILL":
                skills.add(ent.text.strip())
        return sorted(list(skills))

    def _parse_date(self, date_str: str) -> datetime:

        if not date_str:
            return None

        now = datetime.now()
        date_str = date_str.lower().strip()

        if any(x in date_str for x in ['present', 'günümüz', 'mevcut', 'hala', 'current']):
            return now

        match = re.search(r'(\d{1,2})?[/-]?(\d{4})', date_str)
        if match:
            month = int(match.group(1)) if match.group(1) else 1
            year = int(match.group(2))
            try:
                return datetime(year, month, 1)
            except:
                return datetime(year, 1, 1)

        return None

    def extract_cv_info(self, text: str) -> dict:

        timeline = self.extract_experience_timeline(text)
        metrics = self.calculate_experience_metrics(timeline)

        skill_recency = {}
        all_detected_skills = set()

        for item in timeline:
            for skill in item.get('skills', []):
                all_detected_skills.add(skill)
                if skill not in skill_recency:
                    skill_recency[skill] = item['end_date']

        general_skills = self.extract_skills(text)
        for s in general_skills:
            if s not in skill_recency:
                skill_recency[s] = "unknown"
                all_detected_skills.add(s)

        clean_timeline = []
        for item in timeline:
            clean_item = item.copy()
            clean_item.pop('start_dt', None)
            clean_item.pop('end_dt', None)

            clean_timeline.append(clean_item)

        return {
            'skills': sorted(list(all_detected_skills)),
            'timeline': clean_timeline,
            'skill_recency': skill_recency,
            'total_experience_months': metrics['total_months'],
            'gaps_detected': metrics['gaps'],
            'is_recent': metrics['is_recent'],
            'last_job_end': metrics['last_job_end']
        }

    def extract_experience_timeline(self, text: str) -> list:

        date_range_pattern = re.compile(
            r'(\d{1,2}/)?\d{4}\s?[-–—]\s?((\d{1,2}/)?\d{4}|present|günümüz|current|hala)',
            re.IGNORECASE
        )

        timeline = []
        matches = list(date_range_pattern.finditer(text))

        for i, match in enumerate(matches):
            full_range = match.group(0)
            parts = re.split(r'[-–—]', full_range)

            start_date = self._parse_date(parts[0])
            end_date = self._parse_date(parts[1]) if len(parts) > 1 else datetime.now()

            if start_date and end_date:

                now = datetime.now()
                if start_date > now:
                    continue
                if end_date > now:
                    end_date = now

                duration = relativedelta(end_date, start_date)
                months = duration.years * 12 + duration.months

                start_pos = match.start()
                pre_context = text[max(0, start_pos - 100):start_pos]

                post_start = match.end()
                end_pos = matches[i+1].start() if i + 1 < len(matches) else len(text)
                post_context = text[post_start:min(post_start + 500, end_pos)]

                block_text = (pre_context + " " + post_context).lower()

                block_skills = self.extract_skills(block_text)

                timeline.append({
                    'start_date': start_date.strftime('%Y-%m'),
                    'end_date': end_date.strftime('%Y-%m'),
                    'start_dt': start_date,
                    'end_dt': end_date,
                    'duration_months': max(1, months),
                    'raw_range': full_range,
                    'context': block_text.lower(),
                    'skills': block_skills
                })

        timeline.sort(key=lambda x: x['start_date'], reverse=True)
        return timeline

    def _merge_intervals(self, intervals: list) -> int:

        if not intervals:
            return 0

        sorted_intervals = sorted(intervals, key=lambda x: x[0])
        merged = []

        for curr_start, curr_end in sorted_intervals:
            if not merged or curr_start > merged[-1][1]:
                merged.append([curr_start, curr_end])
            else:
                merged[-1][1] = max(merged[-1][1], curr_end)

        total_months = 0
        for start, end in merged:
            diff = relativedelta(end, start)
            total_months += diff.years * 12 + diff.months

        return max(1, total_months)

    def calculate_experience_metrics(self, timeline: list) -> dict:

        if not timeline:
            return {'total_months': 0, 'gaps': [], 'is_recent': False, 'last_job_end': None}

        edu_keywords = ['university', 'universitesi', 'lisans', 'bachelor', 'master', 'high school', 'lise', 'education', 'egitim', 'student', 'ogrenci', 'graduation', 'mezuniyet', 'expected']

        work_intervals = []
        prof_timeline = []

        for item in timeline:
            is_edu = any(kw in item['context'] for kw in edu_keywords)

            if not is_edu:
                work_intervals.append((item['start_dt'], item['end_dt']))
                prof_timeline.append(item)

        total_months = self._merge_intervals(work_intervals)

        gaps = []
        if prof_timeline:
            for i in range(len(prof_timeline) - 1):
                try:
                    current_start = datetime.strptime(prof_timeline[i]['start_date'], '%Y-%m')
                    prev_end = datetime.strptime(prof_timeline[i+1]['end_date'], '%Y-%m')

                    if current_start > prev_end:
                        gap_duration = relativedelta(current_start, prev_end)
                        gap_months = gap_duration.years * 12 + gap_duration.months
                        if gap_months > 6:
                            gaps.append({
                                'after': prof_timeline[i+1]['raw_range'],
                                'before': prof_timeline[i]['raw_range'],
                                'duration': gap_months
                            })
                except:
                    continue

        last_job_end_str = prof_timeline[0]['end_date'] if prof_timeline else timeline[0]['end_date']
        try:
            last_job_end = datetime.strptime(last_job_end_str, '%Y-%m')
            is_recent = (datetime.now() - last_job_end).days < 730
        except:
            is_recent = False

        return {
            'total_months': total_months,
            'gaps': gaps,
            'is_recent': is_recent,
            'last_job_end': last_job_end_str
        }

    def add_custom_skills(self, skills_list: list):

        nlp = self.nlp
        ruler = nlp.get_pipe("entity_ruler")
        patterns = []
        for skill in skills_list:
            skill_clean = skill.lower().strip()
            if len(skill_clean) > 1:
                patterns.append({"label": "SKILL", "pattern": skill_clean})
        if patterns:
            ruler.add_patterns(patterns)

    def encode_text(self, text: str) -> np.ndarray:

        cleaned = clean_text(text)
        embedding = self.sbert_model.encode([cleaned])
        return embedding[0]

    def encode_texts(self, texts: list) -> np.ndarray:

        cleaned_texts = [clean_text(t) for t in texts]
        embeddings = self.sbert_model.encode(cleaned_texts, show_progress_bar=True)
        return embeddings

    def compute_match_score(self, job_embedding: np.ndarray, cv_embedding: np.ndarray) -> float:
        # NOT: SBERT vektörleri arasındaki kosinüs benzerliğini hesaplayıp sonucu 100 üzerinden bir yüzde değerine dönüştürüyoruz.
        job_vec = job_embedding.reshape(1, -1)
        cv_vec = cv_embedding.reshape(1, -1)
        score = cosine_similarity(job_vec, cv_vec)[0][0]
        return round(float(score * 100), 2)

    def compute_batch_matches(self, job_embedding: np.ndarray,
                              cv_embeddings: np.ndarray) -> np.ndarray:

        job_vec = job_embedding.reshape(1, -1)
        scores = cosine_similarity(job_vec, cv_embeddings)[0]
        return np.round(scores * 100, 2)

    def select_best_sentences(self, job_description: str, sentences: list, top_n: int = 3, threshold: float = 0.3) -> list:

        if not sentences:
            return []

        job_emb = self.encode_text(job_description)
        sent_embs = self.encode_texts(sentences)

        job_vec = job_emb.reshape(1, -1)
        scores = cosine_similarity(job_vec, sent_embs)[0]

        scored_sentences = list(zip(sentences, scores))
        scored_sentences.sort(key=lambda x: x[1], reverse=True)

        best = [s[0] for s in scored_sentences if s[1] >= threshold]
        if not best:
            return [s[0] for s in scored_sentences[:2]]

        return best[:top_n]

    def calculate_weighted_score(self, sim_score: float, skill_match_ratio: float, keyword_match_ratio: float,
                                 weights: dict = None) -> float:

        if weights is None:
            weights = {'sim': 0.4, 'skill': 0.4, 'keyword': 0.2}

        final_score = (weights['sim'] * sim_score +
                       weights['skill'] * (skill_match_ratio * 100) +
                       weights['keyword'] * (keyword_match_ratio * 100))

        return round(float(final_score), 2)

    def detect_language(self, text: str) -> str:

        if not text:
            return "en"

        tr_chars = len(re.findall(r'[çğışöüİĞÜŞÖÇ]', text))

        en_keywords = len(re.findall(r'\b(the|and|with|from|which|that|this|for|was|were|been|have|has|experience|education|skills|summary)\b', text, re.IGNORECASE))

        tr_keywords = len(re.findall(r'\b(ve|ile|için|olan|bir|bu|da|de|deneyim|eğitim|yetenekler|özet)\b', text, re.IGNORECASE))

        if tr_keywords > en_keywords or (tr_chars > 5 and tr_keywords > 0):
            return "tr"
        elif en_keywords > 0:
            return "en"

        if tr_chars > 3:
            return "tr"
        return "en"

    def semantic_header_matching(self, text: str) -> dict:

        standard_sections = {
            "summary": ["özet", "summary", "hakkımda", "bana dair", "professional profile", "about me", "kariyer özeti"],
            "experience": ["deneyim", "experience", "iş geçmişi", "kariyer yolculuğum", "work history", "profesyonel geçmiş"],
            "education": ["eğitim", "education", "akademi", "öğrenim", "academic background", "okul"],
            "skills": ["yetenekler", "skills", "beceriler", "teknik yetkinlikler", "competencies", "araçlar"],
            "projects": ["projeler", "projects", "portfolyo", "portfolio", "çalışmalarım"],
            "certifications": ["sertifikalar", "certifications", "eğitimler", "başarılar", "licenses", "awards"]
        }

        lines = text.split('\n')
        candidates = [line.strip() for line in lines if 2 < len(line.strip()) < 50]

        found_sections = {}
        if not candidates:
            return found_sections

        candidate_embeddings = self.sbert_model.encode(candidates)

        for category, synonyms in standard_sections.items():
            cat_embeddings = self.sbert_model.encode(synonyms)

            sims = cosine_similarity(cat_embeddings, candidate_embeddings)
            max_sim = np.max(sims)

            if max_sim > 0.70:
                found_sections[category] = True

        return found_sections

    def gap_analysis(self, job_skills: list, candidate_skills: list) -> dict:

        job_set = set(s.lower().strip() for s in job_skills)
        candidate_set = set(s.lower().strip() for s in candidate_skills)

        matching = job_set.intersection(candidate_set)
        missing = job_set - candidate_set
        extra = candidate_set - job_set

        coverage = (len(matching) / len(job_set) * 100) if len(job_set) > 0 else 0

        return {
            'matching_skills': sorted(list(matching)),
            'missing_skills': sorted(list(missing)),
            'extra_skills': sorted(list(extra)),
            'coverage_percent': round(coverage, 1),
            'total_required': len(job_set),
            'total_matched': len(matching),
        }

    def semantic_gap_analysis(self, job_skills: list, candidate_skills: list,
                              threshold: float = 0.75,
                              candidate_skill_recency: dict = None) -> dict:

        job_set = set(s.lower().strip() for s in job_skills if s.strip())
        candidate_set = set(s.lower().strip() for s in candidate_skills if s.strip())

        exact_matches = job_set.intersection(candidate_set)

        initially_missing = job_set - candidate_set
        initially_extra = candidate_set - job_set

        semantic_matches = []
        matched_extras = set()
        remaining_missing = set()

        # NOT: Birebir eşleşmeyen yetenekleri SBERT ile vektörleştirip, anlamca uyuşanları (örneğin 'go' ve 'golang') tespit ediyoruz.
        if initially_missing and initially_extra:
            missing_list = sorted(list(initially_missing))
            extra_list = sorted(list(initially_extra))

            missing_embeddings = self.sbert_model.encode(missing_list)
            extra_embeddings = self.sbert_model.encode(extra_list)

            sim_matrix = cosine_similarity(missing_embeddings, extra_embeddings)

            used_missing = set()
            used_extra = set()

            pairs = []
            for i in range(len(missing_list)):
                for j in range(len(extra_list)):
                    pairs.append((sim_matrix[i][j], i, j))
            pairs.sort(key=lambda x: x[0], reverse=True)

            for score, i, j in pairs:
                if score < threshold:
                    break
                if i in used_missing or j in used_extra:
                    continue

                job_s, cv_s = missing_list[i].lower(), extra_list[j].lower()
                if (job_s == "go" and cv_s == "git") or (job_s == "git" and cv_s == "go"):
                    continue

                semantic_matches.append({
                    'job_skill': missing_list[i],
                    'cv_skill': extra_list[j],
                    'similarity': round(float(score), 3)
                })
                used_missing.add(i)
                used_extra.add(j)
                matched_extras.add(extra_list[j])

            for i, skill in enumerate(missing_list):
                if i not in used_missing:
                    remaining_missing.add(skill)
        else:
            remaining_missing = initially_missing

        remaining_extra = initially_extra - matched_extras

        total_required = len(job_set)
        total_score = 0.0

        now = datetime.now()

        for skill in exact_matches:
            penalty = 1.0
            if candidate_skill_recency and skill in candidate_skill_recency:
                last_used_str = candidate_skill_recency[skill]
                if last_used_str == "unknown":
                    penalty = 0.9
                else:
                    try:
                        last_used = datetime.strptime(last_used_str, '%Y-%m')
                        months_ago = (now.year - last_used.year) * 12 + (now.month - last_used.month)
                        if months_ago > 24:
                            penalty = 0.8
                    except:
                        pass
            total_score += 1.0 * penalty

        for match in semantic_matches:
            penalty = 1.0
            cv_skill = match['cv_skill']
            if candidate_skill_recency and cv_skill in candidate_skill_recency:
                last_used_str = candidate_skill_recency[cv_skill]
                if last_used_str == "unknown":
                    penalty = 0.9
                else:
                    try:
                        last_used = datetime.strptime(last_used_str, '%Y-%m')
                        months_ago = (now.year - last_used.year) * 12 + (now.month - last_used.month)
                        if months_ago > 24:
                            penalty = 0.8
                    except:
                        pass
            total_score += (match['similarity']) * penalty

        coverage = (total_score / total_required * 100) if total_required > 0 else 0

        return {
            'exact_matches': sorted(list(exact_matches)),
            'semantic_matches': semantic_matches,
            'missing_skills': sorted(list(remaining_missing)),
            'extra_skills': sorted(list(remaining_extra)),
            'coverage_percent': round(min(coverage, 100.0), 1),
            'total_required': total_required,
            'total_exact': len(exact_matches),
            'total_semantic': len(semantic_matches),
            'total_matched': len(exact_matches) + len(semantic_matches),
        }

    def calculate_ats_score(self, cv_text: str, job_description: str, pdf_warnings: list) -> dict:

        # NOT: Scorecard 4.0: Görsel tasarım puanını (Max: 40) hesaplıyoruz. Çok sütunlu Canva şablonlarına 15 puan "Pretty Resume" cezası kesiyoruz.
        format_score = 40.0
        format_breakdown = {"structure": 20, "design": 10, "readability": 10}

        pretty_keywords = ["column", "tablo", "table", "layout", "graphic", "sidebar"]
        design_warnings = [w for w in pdf_warnings if any(pk in w.lower() for pk in pretty_keywords)]
        is_pretty_resume = len(design_warnings) > 0 or len(pdf_warnings) > 2

        if is_pretty_resume:
            format_score -= 15.0
            format_breakdown["design"] = 0

        other_warnings = [w for w in pdf_warnings if w not in design_warnings]
        warning_deduction = len(other_warnings) * 4.0
        format_score = max(5.0, format_score - warning_deduction)
        format_breakdown["readability"] = max(0, 10 - len(other_warnings) * 2)

        cv_info = self.extract_cv_info(cv_text)
        job_info = self.extract_job_requirements(job_description)

        job_title = ""
        for line in job_description.split('\n'):
            if line.strip():
                job_title = line.strip()[:100]
                break

        last_job = cv_info['timeline'][0].get('context', "") if cv_info['timeline'] else ""
        title_score = 0.0
        if last_job and job_title:
            title_sim = cosine_similarity(
                self.sbert_model.encode([job_title]),
                self.sbert_model.encode([last_job])
            )[0][0]

            if title_sim >= 0.57:
                title_score = 15.0
            else:
                title_score = title_sim * 10.0

        gap = self.semantic_gap_analysis(
            job_info['must_have_skills'] + job_info['nice_to_have_skills'],
            cv_info['skills'],
            candidate_skill_recency=cv_info['skill_recency']
        )

        matched_skills = gap['exact_matches'] + [m['job_skill'] for m in gap['semantic_matches']]

        hard_matched = [s for s in matched_skills if s.lower() not in SOFT_SKILLS]
        soft_matched = [s for s in matched_skills if s.lower() in SOFT_SKILLS]

        hard_total = len([s for s in (job_info['must_have_skills'] + job_info['nice_to_have_skills']) if s.lower() not in SOFT_SKILLS])
        soft_total = len([s for s in (job_info['must_have_skills'] + job_info['nice_to_have_skills']) if s.lower() in SOFT_SKILLS])

        hard_ratio = len(hard_matched) / hard_total if hard_total > 0 else 1.0
        soft_ratio = len(soft_matched) / soft_total if soft_total > 0 else 1.0

        skills_score = (hard_ratio * 0.7 + soft_ratio * 0.3) * 25.0

        final_keyword_score = title_score + skills_score

        found_sections = self.semantic_header_matching(cv_text)

        section_score = 0
        standard_found = 0

        for cat in STANDARD_SECTIONS.keys():
            if found_sections.get(cat):
                standard_found += 1
                section_score += 4.0

        cv_lang = self.detect_language(cv_text)
        job_lang = self.detect_language(job_description)
        lang_match = (cv_lang == job_lang)

        missing_must_haves = []
        for must_skill in job_info['must_have_skills']:
            if must_skill.lower() not in [s.lower() for s in cv_info['skills']]:
                is_semantic = any(sm['job_skill'].lower() == must_skill.lower() for sm in gap['semantic_matches'])
                if not is_semantic:
                    missing_must_haves.append(must_skill)

        # NOT: Eğer aday ilanda belirtilen zorunlu (Must-Have) yetenekleri taşımıyorsa, her eksik yetenek için toplam puanını %25 düşürüyoruz (en fazla %80 kırpma).
        is_disqualified = (len(missing_must_haves) > 0)

        must_have_multiplier = max(0.2, 1.0 - len(missing_must_haves) * 0.25)

        raw_score = format_score + final_keyword_score + section_score

        total_score = raw_score * must_have_multiplier
        if not lang_match and cv_lang != "unknown" and job_lang != "unknown":
            total_score *= 0.9

        return {
            'final_score': float(round(max(0.0, total_score), 2)),
            'format_score': float(round(format_score, 1)),
            'keyword_score': float(round(final_keyword_score, 1)),
            'section_score': float(round(section_score, 1)),
            'missing_must_haves': missing_must_haves,
            'is_disqualified': 1 if is_disqualified else 0,
            'is_pretty_resume': 1 if is_pretty_resume else 0,
            'penalty_applied': float(round(max(0.0, raw_score - total_score), 2)),
            'language_match': lang_match,
            'cv_lang': cv_lang,
            'job_lang': job_lang,
            'sections_found': list(found_sections.keys()),
            'title_match_bonus': float(round(title_score, 1)),
            'detail_metrics': {
                'format': format_breakdown,
                'skills': {
                    'hard': float(round(hard_ratio*100, 0)),
                    'soft': float(round(soft_ratio*100, 0)),
                    'title': float(round(title_score, 1))
                }
            }
        }

    def extract_job_requirements(self, description: str) -> dict:

        MUST_KEYWORDS = [
            'required', 'must', 'must have', 'must-have', 'mandatory',
            'essential', 'critical', 'necessary', 'obligatory',
            'prerequisite', 'minimum', 'at least', 'minimum of',
            'proven experience', 'strong experience', 'solid experience',
            'certificate', 'certification', 'certified',
            'license', 'licence', 'licensed',
            'fluent', 'fluency', 'native',
            'degree', 'bachelor', 'master', 'phd', 'diploma',
            'zorunlu', 'gerekli', 'şart', 'olmazsa olmaz',
            'sertifika', 'ehliyet', 'lisans', 'diploma',
        ]

        CERT_PATTERNS = re.compile(
            r'\b('
            r'src[\s\-]*\d+|iso[\s\-]*\d+|osha[\s\-]*\d+|pmp|prince2|itil(?:\s+v?\d+)?|six[\s\-]*sigma|ccna|ccnp|ccie'
            r'|aws[\s\-]+(?:certified|solutions|cloud)|azure[\s\-]+(?:certified|administrator|developer)|comptia[\s\-]+(?:a\+|security\+|network\+)'
            r'|cissp|cism|cisa|cpa|cfa|frm|first[\s\-]*aid(?:\s+certif\w*)?|driving[\s\-]*licen[sc]e|ehliyet|src[\s\-]*belgesi'
            r'|isg[\s\-]*(?:belgesi|sertifika\w*)|ilk[\s\-]*yardım(?:\s+sertifika\w*)'
            r')\b',
            re.IGNORECASE
        )

        if not description:
            return {'must_have_skills': [], 'nice_to_have_skills': []}

        doc = self.nlp(description.lower())
        must_have = set()
        nice_to_have = set()

        for sent in doc.sents:
            sent_text = sent.text.lower()
            is_must_sentence = any(kw in sent_text for kw in MUST_KEYWORDS)

            for ent in sent.ents:
                if ent.label_ == "SKILL":
                    skill = ent.text.strip()
                    if is_must_sentence: must_have.add(skill)
                    else: nice_to_have.add(skill)

            cert_found = CERT_PATTERNS.findall(sent_text)
            for cert in cert_found:
                if len(cert.strip()) > 2:
                    if is_must_sentence: must_have.add(cert.strip())
                    else: nice_to_have.add(cert.strip())

        nice_to_have -= must_have

        return {
            'must_have_skills': sorted(list(must_have)),
            'nice_to_have_skills': sorted(list(nice_to_have)),
        }
