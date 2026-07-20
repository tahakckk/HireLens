import fitz
import os
import unicodedata
from docx import Document

def extract_text_from_docx(file_path: str):

    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return "\n".join(full_text), []
    except Exception as e:
        raise ValueError(f"Word dosyası okunamadı: {str(e)}")

def extract_text_from_pdf(file_path: str):
    try:
        doc = fitz.open(file_path)
        total_text = ""
        warnings = []

        is_multi_column = False
        total_chars = 0

        for page in doc:

            blocks = page.get_text("blocks", sort=True)
            page_width = page.rect.width
            
            # NOT: Sayfa genişliğinin %20 ile %80'i arasındaki dikey çizgileri (gutter) tarayıp en uygun sütun ayracını buluyoruz.
            min_x = int(page_width * 0.2)
            max_x = int(page_width * 0.8)
            best_split_x = None
            min_crossings = 99999
            
            non_empty_blocks = [b for b in blocks if b[4].strip()]
            total_blocks = len(non_empty_blocks)
            
            for x in range(min_x, max_x, 5):
                crossings = 0
                left_count = 0
                right_count = 0
                for b in non_empty_blocks:
                    x0, y0, x1, y1, text, block_no, block_type = b
                    if x0 < x and x1 > x:
                        crossings += 1
                    elif x1 <= x:
                        left_count += 1
                    elif x0 >= x:
                        right_count += 1
                
                if left_count >= 3 and right_count >= 3:
                    if crossings < min_crossings:
                        min_crossings = crossings
                        best_split_x = x
            
            # NOT: Eğer sütunları kesen eleman sayısı çok azsa, sayfayı çift sütunlu olarak kabul edip sütun bazlı okuma yapıyoruz.
            if best_split_x is not None and (min_crossings <= 2 or min_crossings < total_blocks * 0.15):
                is_multi_column = True
                
                # NOT: Sütun ayracına (split_x) göre blokları sol ve sağ sütun olarak ayırıyoruz.
                final_page_blocks = []
                current_left = []
                current_right = []
                
                # NOT: İlk sıralamayı yukarıdan aşağıya (y0 koordinatına) göre yapıyoruz.
                sorted_by_y = sorted(non_empty_blocks, key=lambda b: b[1])
                
                for b in sorted_by_y:
                    x0, y0, x1, y1, text, block_no, block_type = b
                    # NOT: Her iki sütuna da taşan geniş başlık vb. blokları spanning olarak algılıyoruz.
                    is_spanning = (x0 < best_split_x - 10) and (x1 > best_split_x + 10)
                    
                    if is_spanning:
                        # NOT: Spanning blok öncesindeki sol ve sağ blok gruplarını kendi içinde sıralayıp ekliyoruz.
                        if current_left or current_right:
                            current_left.sort(key=lambda x: x[1])
                            current_right.sort(key=lambda x: x[1])
                            final_page_blocks.extend(current_left)
                            final_page_blocks.extend(current_right)
                            current_left = []
                            current_right = []
                        final_page_blocks.append(b)
                    else:
                        center_x = (x0 + x1) / 2
                        if center_x < best_split_x:
                            current_left.append(b)
                        else:
                            current_right.append(b)
                
                # NOT: Sayfa sonundaki kalan blokları birleştiriyoruz.
                if current_left or current_right:
                    current_left.sort(key=lambda x: x[1])
                    current_right.sort(key=lambda x: x[1])
                    final_page_blocks.extend(current_left)
                    final_page_blocks.extend(current_right)
                
                page_blocks = [b[4] for b in final_page_blocks]
            else:
                page_blocks = [b[4] for b in blocks if b[4].strip()]

            page_text = "\n".join(page_blocks)
            total_text += page_text + "\n"
            total_chars += len(page_text.strip())

        num_pages = len(doc)
        doc.close()

        if num_pages > 0 and (total_chars / num_pages) < 100:
            warnings.append("Bu PDF resim tabanlı görünüyor (Metin katmanı yok). Lütfen .docx formatını deneyin.")

        if is_multi_column:
            warnings.append("Çoklu sütunlu (multi-column) sayfa yapısı algılandı. Metin okuma sırası kaymış olabilir.")

        # NOT: Türkçe karakterlerdeki (ü, ç, ğ, ş, ı) Unicode ayrışmalarını NFKC ile normalize ediyoruz.
        total_text = unicodedata.normalize('NFKC', total_text)

        return total_text.strip(), warnings
    except Exception as e:
        raise ValueError(f"PDF okunamadı: {str(e)}")

def parse_file(file_path: str) -> dict:

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        text, warnings = extract_text_from_pdf(file_path)
    elif ext == '.docx':
        text, warnings = extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Desteklenmeyen dosya formatı: {ext}. PDF veya DOCX kullanın.")

    return {
        "text": text,
        "warnings": warnings,
        "extension": ext
    }
