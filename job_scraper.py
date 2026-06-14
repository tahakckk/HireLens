"""
İş İlanı Scraper — LinkedIn ve diğer platformlardan iş ilanı bilgisi çekme modülü.

LinkedIn public job sayfalarından otomatik parse etmeyi dener.
Başarısız olursa kullanıcıdan manual metin girişi istenir (fallback).
"""

import re
import requests
from bs4 import BeautifulSoup


# ─────────────────────────────────────────────
# LinkedIn Job Parser
# ─────────────────────────────────────────────

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}


def validate_linkedin_url(url: str) -> bool:
    """LinkedIn iş ilanı URL'sini doğrular."""
    patterns = [
        r'https?://(www\.)?linkedin\.com/jobs/view/\d+',
        r'https?://(www\.)?linkedin\.com/jobs/.*',
        r'https?://([\w]+\.)?linkedin\.com/.*job.*',
    ]
    return any(re.match(p, url, re.IGNORECASE) for p in patterns)


def extract_linkedin_job_id(url: str) -> str | None:
    """LinkedIn URL'sinden job ID çıkarır."""
    match = re.search(r'/view/(\d+)', url)
    if match:
        return match.group(1)
    match = re.search(r'currentJobId=(\d+)', url)
    if match:
        return match.group(1)
    return None


def scrape_linkedin_job(url: str) -> dict:
    try:
        # NOT: LinkedIn linklerini normalize edip protokole uygun hale getiriyoruz.
        if not url.startswith('http'):
            url = 'https://' + url

        # NOT: Oturum kısıtlamalarını aşmak için LinkedIn Guest API (jobs-guest/jobs/api/jobPosting) endpoint'ini kullanıyoruz.
        job_id = extract_linkedin_job_id(url)
        if job_id:
            embed_url = f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}'
            response = requests.get(embed_url, headers=HEADERS, timeout=15)
        else:
            response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code != 200:
            return {
                'success': False,
                'error': f'HTTP {response.status_code} — LinkedIn sayfası erişilemedi. '
                         f'Lütfen ilan metnini manuel olarak yapıştırın.'
            }

        soup = BeautifulSoup(response.text, 'html.parser')

        # ── Title ──
        title = ''
        title_el = soup.find('h2', class_='top-card-layout__title')
        if not title_el:
            title_el = soup.find('h1')
        if not title_el:
            title_el = soup.find('h2')
        if title_el:
            title = title_el.get_text(strip=True)

        # ── Company ──
        company = ''
        company_el = soup.find('a', class_='topcard__org-name-link')
        if not company_el:
            company_el = soup.find('span', class_='topcard__flavor')
        if company_el:
            company = company_el.get_text(strip=True)

        # ── Location ──
        location = ''
        location_el = soup.find('span', class_='topcard__flavor--bullet')
        if location_el:
            location = location_el.get_text(strip=True)

        # ── Description ──
        description = ''
        desc_el = soup.find('div', class_='description__text')
        if not desc_el:
            desc_el = soup.find('div', class_='show-more-less-html__markup')
        if not desc_el:
            # Fallback: section ile dene
            desc_el = soup.find('section', class_='description')
        if desc_el:
            description = desc_el.get_text(separator='\n', strip=True)

        # ── Employment Type & Seniority ──
        employment_type = ''
        seniority = ''
        criteria_items = soup.find_all('li', class_='description__job-criteria-item')
        for item in criteria_items:
            header = item.find('h3')
            value = item.find('span')
            if header and value:
                header_text = header.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)
                if 'employment' in header_text or 'type' in header_text:
                    employment_type = value_text
                elif 'seniority' in header_text or 'level' in header_text:
                    seniority = value_text

        # Yeterli bilgi çekilebildi mi kontrol et
        if not description or len(description) < 50:
            return {
                'success': False,
                'error': 'İlan detayları yeterince çekilemedi. '
                         'LinkedIn login gerektirebilir. '
                         'Lütfen ilan metnini manuel olarak yapıştırın.'
            }

        return {
            'success': True,
            'title': title or 'Başlık bulunamadı',
            'company': company,
            'location': location,
            'description': description,
            'employment_type': employment_type,
            'seniority_level': seniority,
        }

    except requests.Timeout:
        return {
            'success': False,
            'error': 'LinkedIn sayfasına bağlanırken zaman aşımı oluştu. '
                     'Lütfen ilan metnini manuel olarak yapıştırın.'
        }
    except requests.RequestException as e:
        return {
            'success': False,
            'error': f'Bağlantı hatası: {str(e)}. '
                     f'Lütfen ilan metnini manuel olarak yapıştırın.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Parse hatası: {str(e)}. '
                     f'Lütfen ilan metnini manuel olarak yapıştırın.'
        }


def parse_job_text(text: str, title: str = '', company: str = '') -> dict:
    """
    Manuel olarak girilen ilan metnini yapısal hale getirir.
    Scraping başarısız olduğunda fallback olarak kullanılır.
    """
    if not text or len(text.strip()) < 20:
        return {
            'success': False,
            'error': 'İlan metni çok kısa. En az birkaç cümle gerekiyor.'
        }

    return {
        'success': True,
        'title': title.strip() if title else 'İş İlanı',
        'company': company.strip() if company else '',
        'location': '',
        'description': text.strip(),
        'employment_type': '',
        'seniority_level': '',
    }
