import re
from sklearn.metrics.pairwise import cosine_similarity
from nlp_engine import NLPEngine

class ExtractiveCVGenerator:

    def __init__(self, nlp_engine: NLPEngine):
        self.nlp = nlp_engine

    def parse_cv(self, raw_text: str) -> dict:

        text = raw_text.strip()
        lines = text.split('\n')
        non_empty_lines = [l.strip() for l in lines if l.strip()]

        profile = {
            'full_name': '',
            'email': '',
            'phone': '',
            'location': '',
            'linkedin': '',
            'website': '',
            'summary': '',
            'education': [],
            'experience': [],
            'skills': {'technical': [], 'soft': [], 'tools': []},
            'languages': [],
            'certifications': [],
            'projects': [],
            'job_title': '',
            'original_headers': {}
        }

        email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w{2,}', text)
        if email_match: profile['email'] = email_match.group(0)

        phone_patterns = [
            r'(?:\+90|0)[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}',
            r'\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}',
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                profile['phone'] = phone_match.group(0).strip()
                break

        linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?', text, re.IGNORECASE)
        if linkedin_match: profile['linkedin'] = linkedin_match.group(0)

        doc = self.nlp.nlp(text[:500])
        for ent in doc.ents:
            if ent.label_ == "PERSON" and 2 <= len(ent.text.split()) <= 4:

                if not any(kw in ent.text.lower() for kw in ['engineer', 'developer', 'manager', 'scientist', 'generation', 'artificial']):
                    profile['full_name'] = ent.text.strip()
                    break

        if not profile['full_name']:
            for line in non_empty_lines[:5]:
                if not re.search(r'[@\d()+]|http|www|linkedin|cv|resume|özgeçmiş', line, re.IGNORECASE):
                    if 4 < len(line) < 40 and len(line.split()) >= 2:
                        if not any(kw in line.lower() for kw in ['engineer', 'developer', 'manager', 'scientist']):
                            profile['full_name'] = line.strip()
                            break

        if profile['full_name']:
            try:

                name_idx = -1
                for i, line in enumerate(non_empty_lines[:10]):
                    if profile['full_name'] in line:
                        name_idx = i
                        break

                if name_idx != -1:

                    for offset in range(1, 4):
                        if name_idx + offset < len(non_empty_lines):
                            next_line = non_empty_lines[name_idx + offset]
                            if any(kw in next_line.lower() for kw in ['engineer', 'developer', 'manager', 'specialist', 'uzman', 'mühendis', 'scientist', 'architect']):
                                profile['job_title'] = next_line.strip()
                                break
            except:
                pass

        section_keywords = {
            'experience': ['experience', 'deneyim', 'employment', 'kariyer', 'iş deneyimi'],
            'education': ['education', 'eğitim', 'öğrenim', 'academic'],
            'skills': ['skills', 'yetenek', 'beceri', 'yetkinlik'],
            'languages': ['languages', 'dil', 'yabancı dil'],
            'certifications': ['certifications', 'sertifika', 'belge'],
            'projects': ['projects', 'proje', 'portfolio'],
            'summary': ['summary', 'özet', 'profil', 'about', 'career objective', 'objective', 'kariyer hedefi']
        }

        sections = {'header': []}
        current_section = 'header'

        for line in non_empty_lines:

            clean_line = line.strip().lower()

            simplified_line = re.sub(r'\b(?:professional|work|academic)\s+', '', clean_line).strip()

            detected = None

            if 1 <= len(simplified_line.split()) <= 3:
                # Ignore lines starting with list markers
                is_header = not re.match(r'^[\s•\-‣▪▸►*]+', line.strip())
                # Ignore lines that have a colon followed by content
                if is_header and ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) > 1 and re.search(r'\w', parts[1]):
                        is_header = False

                if is_header:
                    for sec, keywords in section_keywords.items():
                        if any(kw in simplified_line for kw in keywords):
                            detected = sec
                            break

            if detected:
                current_section = detected
                if current_section not in sections:
                    sections[current_section] = []

                profile['original_headers'][current_section] = line.strip()
            else:
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].append(line)

        if 'experience' in sections:
            date_pattern = re.compile(r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|[a-zA-Zçğıöşü]+)?\s*(?:19|20)\d{2}|\d{1,2}[/-]\d{4})\s*[-–—]\s*((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|[a-zA-Zçğıöşü]+)?\s*(?:19|20)\d{2}|\d{1,2}[/-]\d{4}|present|current|halen|günümüz|devam)', re.IGNORECASE)
            job_title_pattern = re.compile(r'\b(engineer|developer|scientist|manager|intern|specialist|analyst|consultant|mühendis|uzman|geliştirici)\b', re.IGNORECASE)

            current_job = {'title': '', 'company': '', 'start_date': '', 'end_date': '', 'responsibilities': []}

            for line in sections['experience']:
                date_match = date_pattern.search(line)
                is_job_title = job_title_pattern.search(line) and len(line) < 80

                if (date_match or is_job_title) and len(current_job['responsibilities']) > 0:
                    profile['experience'].append(current_job)
                    current_job = {'title': '', 'company': '', 'start_date': '', 'end_date': '', 'responsibilities': []}

                if date_match:
                    current_job['start_date'] = date_match.group(1).strip()
                    current_job['end_date'] = date_match.group(2).strip()

                    remaining = date_pattern.sub('', line).strip().rstrip('–—-|,').strip()
                    if remaining and len(remaining) > 2:
                        current_job['company'] = remaining

                elif is_job_title:
                    parts = line.split(',')
                    current_job['title'] = parts[0].strip()
                    if len(parts) > 1:
                        current_job['company'] = parts[1].strip()
                else:
                    clean_line = re.sub(r'^[\s•\-‣▪▸►*]+', '', line).strip()
                    if len(clean_line) > 20:
                        current_job['responsibilities'].append(clean_line)
                    elif len(clean_line) > 2 and not current_job['company']:
                        current_job['company'] = clean_line

            if current_job['title'] or len(current_job['responsibilities']) > 0:
                profile['experience'].append(current_job)

        if 'education' in sections:
            edu_keywords = ['bachelor', 'master', 'phd', 'lisans', 'yüksek lisans', 'university', 'üniversite', 'college', 'b.s', 'm.s']
            current_edu = {'degree': '', 'institution': '', 'start_year': '', 'end_year': ''}

            for line in sections['education']:
                date_match = re.search(r'((?:19|20)\d{2})\s*[-–—]\s*((?:19|20)\d{2}|present|current|halen)', line, re.IGNORECASE)
                single_year = re.search(r'\b(?:19|20)\d{2}\b', line)

                if (date_match or single_year or any(kw in line.lower() for kw in edu_keywords)) and (current_edu['degree'] or current_edu['institution']):
                    if any(kw in line.lower() for kw in ['university', 'üniversite']) and current_edu['institution']:
                        profile['education'].append(current_edu)
                        current_edu = {'degree': '', 'institution': '', 'start_year': '', 'end_year': ''}

                if date_match:
                    current_edu['start_year'] = date_match.group(1).strip()
                    current_edu['end_year'] = date_match.group(2).strip()
                elif single_year and not current_edu['end_year']:
                    current_edu['end_year'] = single_year.group(0).strip()

                if any(kw in line.lower() for kw in ['university', 'üniversite', 'college', 'institute']):
                    clean_inst = re.sub(r'((?:19|20)\d{2})|[-–—]|(lisans|bachelor|master)', '', line, flags=re.IGNORECASE).strip()
                    current_edu['institution'] = clean_inst if clean_inst else line.strip()
                elif any(kw in line.lower() for kw in ['bachelor', 'master', 'phd', 'lisans', 'yüksek lisans', 'b.s', 'm.s', 'engineering', 'mühendislik']):
                    clean_deg = re.sub(r'((?:19|20)\d{2})|[-–—]', '', line).strip()
                    current_edu['degree'] = clean_deg
                elif len(line) > 5 and not current_edu['degree']:
                    current_edu['degree'] = line.strip()

            if current_edu['degree'] or current_edu['institution']:
                profile['education'].append(current_edu)

        profile['summary'] = " ".join(sections.get('summary', [])).strip()

        skills_lines = sections.get('skills', [])
        profile['skills']['groups'] = []
        all_skills = []
        for line in skills_lines:
            line_skills = self.nlp.extract_skills(line)
            if line_skills:
                profile['skills']['groups'].append(line_skills)
                all_skills.extend(line_skills)

        profile['skills']['technical'] = sorted(list(set(all_skills)))

        # Fallback: if no skills were parsed from a dedicated skills section, extract from whole text
        if not profile['skills']['technical']:
            profile['skills']['technical'] = self.nlp.extract_skills(raw_text)

        cert_lines = sections.get('certifications', [])
        for line in cert_lines:

            clean_cert = re.sub(r'^[\s•\-‣▪▸►*]+', '', line).strip()
            if len(clean_cert) > 5:

                year_match = re.search(r'\b(20\d{2}|19\d{2})\b', clean_cert)
                year = year_match.group(0) if year_match else ''

                parts = re.split(r'[,|]|from', clean_cert, flags=re.IGNORECASE)
                name = parts[0].strip()
                issuer = parts[1].strip() if len(parts) > 1 else ''

                profile['certifications'].append({
                    'name': name,
                    'issuer': issuer,
                    'year': year
                })

        has_data = any([
            profile['full_name'], profile['email'], profile['phone'],
            profile['education'], profile['experience'],
            profile['skills']['technical']
        ])

        if not profile['summary']:

            header_text = " ".join(sections.get('header', []))
            if len(header_text) > 100:
                profile['summary'] = header_text[:500]
            elif not has_data:
                profile['summary'] = text[:500]

        return profile

    def generate_tailored_cv(self, parsed_profile: dict, job_data: dict) -> dict:

        job_description = job_data.get('description', '')
        job_title = job_data.get('title', 'Belirtilmemiş İş Unvanı')

        cv_lang = self.nlp.detect_language(parsed_profile.get('summary', '') + " " + job_description)

        headers = {
            'tr': {
                'summary': 'PROFESYONEL ÖZET',
                'experience': 'İŞ DENEYİMİ',
                'education': 'EĞİTİM',
                'skills': 'YETKİNLİKLER',
                'projects': 'PROJELER',
                'certifications': 'SERTİFİKALAR',
                'languages': 'DİLLER'
            },
            'en': {
                'summary': 'PROFESSIONAL SUMMARY',
                'experience': 'PROFESSIONAL EXPERIENCE',
                'education': 'EDUCATION',
                'skills': 'SKILLS',
                'projects': 'PROJECTS',
                'certifications': 'CERTIFICATIONS',
                'languages': 'LANGUAGES'
            }
        }

        lang_headers = headers.get(cv_lang, headers['tr'])
        for key in lang_headers.keys():
            if key in parsed_profile.get('original_headers', {}):
                lang_headers[key] = parsed_profile['original_headers'][key]

        job_embedding = self.nlp.encode_text(job_description)
        job_skills = self.nlp.extract_skills(job_description)
        job_skills_set = set([s.lower() for s in job_skills])
        job_title_lower = job_title.lower()

        # NOT: Özgeçmiş özetindeki cümleleri SBERT ile kodlayıp iş tanımına en benzer olanları en üste alacak şekilde sıralıyoruz.
        raw_summary = parsed_profile.get("summary", "")
        if raw_summary:
            summary_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', raw_summary) if len(s.strip()) > 5]
            if len(summary_sentences) > 1:
                summary_embeddings = self.nlp.encode_texts(summary_sentences)
                job_vec = job_embedding.reshape(1, -1)
                sim_scores = cosine_similarity(job_vec, summary_embeddings)[0]

                scored_summary = []
                for idx, sentence in enumerate(summary_sentences):
                    scored_summary.append((sentence, sim_scores[idx] * 100))

                scored_summary.sort(key=lambda x: x[1], reverse=True)
                parsed_profile['summary'] = " ".join([item[0] for item in scored_summary])

        optimized_experience = []

        for exp in parsed_profile.get('experience', []):
            raw_responsibilities = exp.get('responsibilities', [])

            formatted_exp = {
                'title': exp.get('title', ''),
                'company': exp.get('company', ''),
                'location': exp.get('location', ''),
                'period': f"{exp.get('start_date', '')} - {exp.get('end_date', '')}".strip(' - '),
                'achievements': []
            }

            if not raw_responsibilities:
                optimized_experience.append(formatted_exp)
                continue

            all_sentences = []
            for resp in raw_responsibilities:

                split_sentences = re.split(r'(?<=[.!?])\s+', resp)
                all_sentences.extend([s.strip() for s in split_sentences if len(s.strip()) > 10])

            if not all_sentences:
                formatted_exp['achievements'] = raw_responsibilities[:2]
                optimized_experience.append(formatted_exp)
                continue

            sent_embeddings = self.nlp.encode_texts(all_sentences)
            job_vec = job_embedding.reshape(1, -1)

            sim_scores = cosine_similarity(job_vec, sent_embeddings)[0]

            scored_sentences = []

            # NOT: Her bir başarı/deneyim cümlesini; anlamsal benzerlik (%50), yetenek uyuşması (%30) ve unvan uyuşmasına (%20) göre ağırlıklandırıp puanlıyoruz.
            for i, sentence in enumerate(all_sentences):
                sentence_lower = sentence.lower()
                sim_score = sim_scores[i]

                bullet_skills = self.nlp.extract_skills(sentence)
                bullet_skills_set = set([s.lower() for s in bullet_skills])
                match_count = len(job_skills_set.intersection(bullet_skills_set))
                skill_ratio = min(match_count / max(len(job_skills_set), 1), 1.0)

                keyword_ratio = 0.0
                if any(word in sentence_lower for word in job_title_lower.split() if len(word) > 3):
                    keyword_ratio = 1.0

                final_score = self.nlp.calculate_weighted_score(
                    sim_score * 100,
                    skill_ratio,
                    keyword_ratio,
                    weights={'sim': 0.5, 'skill': 0.3, 'keyword': 0.2}
                )

                scored_sentences.append((sentence, final_score))

            scored_sentences.sort(key=lambda x: x[1], reverse=True)

            best_sentences = [item[0] for item in scored_sentences]

            formatted_exp['achievements'] = best_sentences
            optimized_experience.append(formatted_exp)

        education = []
        for edu in parsed_profile.get('education', []):
            education.append({
                'degree': f"{edu.get('degree', '')} {edu.get('field', '')}".strip(),
                'institution': edu.get('institution', ''),
                'period': f"{edu.get('start_year', '')} - {edu.get('end_year', '')}".strip(' - '),
                'details': f"GPA: {edu.get('gpa', '')}" if edu.get('gpa') else ''
            })

        cv_skills_dict = parsed_profile.get('skills', {})
        if isinstance(cv_skills_dict, dict):
            cv_skills = cv_skills_dict.get('technical', []) + cv_skills_dict.get('soft', [])
        elif isinstance(cv_skills_dict, list):
            cv_skills = cv_skills_dict
        else:
            cv_skills = []

        gap = self.nlp.semantic_gap_analysis(job_skills, cv_skills)
        highlights = gap['exact_matches'] + [m['cv_skill'] for m in gap['semantic_matches']]

        primary_skills = []
        secondary_skills = []

        for skill in cv_skills:
            if skill in highlights:
                primary_skills.append(skill)
            else:
                secondary_skills.append(skill)

        contact_info = {
            "email": parsed_profile.get("email", ""),
            "phone": parsed_profile.get("phone", ""),
            "location": parsed_profile.get("location", ""),
            "linkedin": parsed_profile.get("linkedin", ""),
            "website": parsed_profile.get("website", "")
        }

        # Reconstruct a complete plain text of the optimized CV for accurate score estimation
        cv_preview_text = f"{parsed_profile.get('full_name', '')}\n"
        
        contact_parts = [contact_info[k] for k in contact_info if contact_info[k]]
        if contact_parts:
            cv_preview_text += " • ".join(contact_parts) + "\n\n"
            
        if parsed_profile.get('summary'):
            cv_preview_text += f"{lang_headers.get('summary', 'SUMMARY')}\n{parsed_profile.get('summary')}\n\n"
            
        if optimized_experience:
            cv_preview_text += f"{lang_headers.get('experience', 'EXPERIENCE')}\n"
            for exp in optimized_experience:
                cv_preview_text += f"{exp['title']} — {exp['company']}\n"
                cv_preview_text += f"{exp['period']}\n"
                for ach in exp['achievements']:
                    cv_preview_text += f"• {ach}\n"
            cv_preview_text += "\n"
            
        if education:
            cv_preview_text += f"{lang_headers.get('education', 'EDUCATION')}\n"
            for edu in education:
                cv_preview_text += f"{edu['degree']} | {edu['institution']} | {edu['period']}\n"
            cv_preview_text += "\n"
            
        cv_skills = primary_skills + secondary_skills
        if cv_skills:
            cv_preview_text += f"{lang_headers.get('skills', 'SKILLS')}\n"
            cv_preview_text += ", ".join(cv_skills) + "\n\n"
            
        certs = parsed_profile.get('certifications', [])
        if certs:
            cv_preview_text += f"{lang_headers.get('certifications', 'CERTIFICATIONS')}\n"
            for cert in certs:
                cert_text = cert.get('name', '')
                if cert.get('issuer'): cert_text += f" — {cert['issuer']}"
                if cert.get('year'): cert_text += f" ({cert['year']})"
                cv_preview_text += f"• {cert_text}\n"
            cv_preview_text += "\n"

        ats_result = self.nlp.calculate_ats_score(cv_preview_text, job_description, [])
        final_score = ats_result.get('final_score', int(gap.get('coverage_percent', 0)))

        return {
            "cv_language": cv_lang,
            "full_name": parsed_profile.get("full_name", ""),
            "job_title": parsed_profile.get("job_title", job_title),
            "contact": contact_info,
            "headers": lang_headers,
            "professional_summary": parsed_profile.get("summary", ""),
            "target_position": job_title,
            "match_highlights": highlights[:5],
            "experience": optimized_experience,
            "education": education,
            "skills": {
                "primary": primary_skills[:10],
                "secondary": secondary_skills[:15],
                "tools": parsed_profile.get('skills', {}).get('tools', []) if isinstance(parsed_profile.get('skills', {}), dict) else [],
                "groups": parsed_profile.get('skills', {}).get('groups', [])
            },
            "languages": parsed_profile.get("languages", []),
            "certifications": parsed_profile.get("certifications", []),
            "projects": parsed_profile.get("projects", []),
            "ats_keywords": list(job_skills_set)[:10],
            "match_score_estimate": round(final_score, 2),
            "optimization_notes": f"{cv_lang.upper()} dilinde extractive model ile optimize edildi."
        }
