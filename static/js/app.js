/**
 * AI Jobs Match — Frontend JavaScript
 * Drag & drop, AJAX, animasyonlar ve interaktivite
 */

document.addEventListener('DOMContentLoaded', () => {
    initDropZone();
    initMobileMenu();
    initFlashAutoClose();
    initLoadingOverlay();
});

/* ── Drag & Drop File Upload ── */
function initDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const fileList = document.getElementById('fileList');
    const uploadBtn = document.getElementById('uploadBtn');

    if (!dropZone || !fileInput) return;

    // Drag events
    ['dragenter', 'dragover'].forEach(event => {
        dropZone.addEventListener(event, (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(event => {
        dropZone.addEventListener(event, (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
        });
    });

    // Drop
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        fileInput.files = dt.files;
        updateFilePreview();
    });

    // File input change
    fileInput.addEventListener('change', updateFilePreview);

    function updateFilePreview() {
        const files = fileInput.files;
        if (!files || files.length === 0) {
            filePreview.style.display = 'none';
            uploadBtn.style.display = 'none';
            return;
        }

        fileList.innerHTML = '';
        let hasValidFile = false;

        for (const file of files) {
            const isPDF = file.name.toLowerCase().endsWith('.pdf');
            const sizeKB = (file.size / 1024).toFixed(1);
            const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            const sizeStr = file.size > 1024 * 1024 ? `${sizeMB} MB` : `${sizeKB} KB`;

            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <span class="file-item-name">${isPDF ? '📄' : '⚠️'} ${file.name}</span>
                <span class="file-item-size">${sizeStr}</span>
            `;

            if (!isPDF) {
                item.style.borderColor = 'rgba(239, 68, 68, 0.3)';
                item.style.background = 'rgba(239, 68, 68, 0.05)';
            } else {
                hasValidFile = true;
            }

            fileList.appendChild(item);
        }

        filePreview.style.display = 'block';
        uploadBtn.style.display = hasValidFile ? 'inline-flex' : 'none';
    }
}

/* ── Mobile Menu Toggle ── */
function initMobileMenu() {
    const toggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');

    if (!toggle || !sidebar) return;

    toggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });
}

/* ── Flash Auto Close ── */
function initFlashAutoClose() {
    const flashes = document.querySelectorAll('.flash-message');
    flashes.forEach((flash, i) => {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-10px)';
            setTimeout(() => flash.remove(), 300);
        }, 5000 + (i * 500));
    });
}

/* ── Loading Overlay ── */
function initLoadingOverlay() {
    // Create overlay element
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.id = 'loadingOverlay';
    overlay.innerHTML = `
        <div class="loading-spinner"></div>
        <div class="loading-text" id="loadingText">İşleniyor...</div>
    `;
    document.body.appendChild(overlay);

    // Show loading on form submissions
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            const fileInput = document.getElementById('fileInput');
            if (!fileInput.files || fileInput.files.length === 0) {
                e.preventDefault();
                return;
            }
            showLoading('CV\'ler analiz ediliyor... Bu biraz sürebilir.');
        });
    }

    const jobForm = document.getElementById('jobForm');
    if (jobForm) {
        jobForm.addEventListener('submit', () => {
            showLoading('İş ilanı analiz ediliyor...');
        });
    }

    // Match buttons
    document.querySelectorAll('form[action*="/match/"]').forEach(form => {
        form.addEventListener('submit', () => {
            showLoading('Eşleştirme yapılıyor... Tüm CV\'ler analiz ediliyor.');
        });
    });
}

function showLoading(text) {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    if (overlay) {
        loadingText.textContent = text || 'İşleniyor...';
        overlay.classList.add('active');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

/* ── Delete CV ── */
function deleteCV(cvId) {
    if (!confirm('Bu CV\'yi silmek istediğinizden emin misiniz?')) return;

    fetch(`/api/delete-cv/${cvId}`, { method: 'DELETE' })
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        })
        .then(data => {
            if (data.success) {
                const card = document.getElementById(`cv-${cvId}`);
                if (card) {
                    card.style.opacity = '0';
                    card.style.transform = 'translateX(20px)';
                    card.style.transition = 'all 0.3s ease';
                    setTimeout(() => {
                        window.location.reload();
                    }, 300);
                } else {
                    window.location.reload();
                }
            } else {
                alert('Silme işlemi başarısız: ' + (data.message || 'Bilinmeyen hata'));
            }
        })
        .catch(err => {
            console.error('Silme hatası:', err);
            alert('CV silinirken bir hata oluştu: ' + err.message);
        });
}

/* ── Delete Job ── */
function deleteJob(jobId) {
    if (!confirm('Bu iş ilanını silmek istediğinizden emin misiniz?')) return;

    fetch(`/api/delete-job/${jobId}`, { method: 'DELETE' })
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        })
        .then(data => {
            if (data.success) {
                const card = document.getElementById(`job-${jobId}`);
                if (card) {
                    card.style.opacity = '0';
                    card.style.transform = 'translateX(20px)';
                    card.style.transition = 'all 0.3s ease';
                    setTimeout(() => {
                        window.location.reload();
                    }, 300);
                } else {
                    window.location.reload();
                }
            } else {
                alert('Silme işlemi başarısız: ' + (data.message || 'Bilinmeyen hata'));
            }
        })
        .catch(err => {
            console.error('Silme hatası:', err);
            alert('İş ilanı silinirken bir hata oluştu: ' + err.message);
        });
}

/* ── Toggle Skills (Expand/Collapse) ── */
function toggleSkills(btn) {
    const container = btn.parentElement;
    const hiddenTags = container.querySelectorAll('.skill-hidden');
    const isExpanded = btn.dataset.expanded === 'true';
    const hiddenCount = btn.dataset.hiddenCount;

    hiddenTags.forEach((tag, i) => {
        if (isExpanded) {
            // Collapse: hide with animation
            tag.style.opacity = '0';
            tag.style.transform = 'scale(0.8)';
            setTimeout(() => {
                tag.style.display = 'none';
            }, 200);
        } else {
            // Expand: show with staggered animation
            tag.style.display = 'inline-flex';
            tag.style.opacity = '0';
            tag.style.transform = 'scale(0.8)';
            setTimeout(() => {
                tag.style.opacity = '1';
                tag.style.transform = 'scale(1)';
            }, 30 * i);
        }
    });

    if (isExpanded) {
        btn.textContent = `+${hiddenCount} daha`;
        btn.dataset.expanded = 'false';
    } else {
        btn.textContent = '▲ Gizle';
        btn.dataset.expanded = 'true';
    }
}
