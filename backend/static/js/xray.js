(() => {
    const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
    const REQUEST_TIMEOUT_MS = 65000;
    const REPORT_STORAGE_KEY = 'mediai_xray_reports';
    const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png'];
    const ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png'];
    const LOADING_STEPS = [
        'Uploading X-ray securely',
        'Running Gemini Vision assessment',
        'Formatting structured report'
    ];
    const storageHelper = {
        set(key, value) {
            try {
                window.localStorage.setItem(key, JSON.stringify(value));
            } catch (error) {
                console.error('[xray] Could not save report to local storage:', error);
            }
        },
        get(key) {
            try {
                const rawValue = window.localStorage.getItem(key);
                if (!rawValue) {
                    return null;
                }
                return JSON.parse(rawValue);
            } catch (error) {
                console.error('[xray] Could not read reports from local storage:', error);
                return null;
            }
        }
    };

    const elements = {
        dropZone: document.getElementById('dropZone'),
        imageInput: document.getElementById('imageInput'),
        uploadError: document.getElementById('uploadError'),
        imagePreview: document.getElementById('imagePreview'),
        previewImg: document.getElementById('previewImg'),
        previewName: document.getElementById('previewName'),
        previewMeta: document.getElementById('previewMeta'),
        analyzeBtn: document.getElementById('analyzeBtn'),
        clearImageBtn: document.getElementById('clearImage'),
        emptyState: document.getElementById('emptyState'),
        loadingState: document.getElementById('loadingState'),
        loadingStep: document.getElementById('loadingStep'),
        resultsContainer: document.getElementById('resultsContainer'),
        resultsError: document.getElementById('resultsError'),
        resultImage: document.getElementById('resultImage'),
        resultFileName: document.getElementById('resultFileName'),
        resultImageType: document.getElementById('resultImageType'),
        resultSeverity: document.getElementById('resultSeverity'),
        resultConfidence: document.getElementById('resultConfidence'),
        resultConfidenceBar: document.getElementById('resultConfidenceBar'),
        resultDate: document.getElementById('resultDate'),
        findingsList: document.getElementById('findingsList'),
        abnormalitiesList: document.getElementById('abnormalitiesList'),
        recommendationsList: document.getElementById('recommendationsList'),
        summaryText: document.getElementById('summaryText'),
        downloadBtn: document.getElementById('downloadReportBtn'),
        recentAnalysesList: document.getElementById('recentAnalysesList')
    };

    let selectedFile = null;
    let selectedPreviewUrl = '';
    let currentReport = null;
    let loadingIntervalId = null;

    function init() {
        if (!elements.dropZone) {
            return;
        }

        elements.dropZone.addEventListener('click', () => elements.imageInput.click());
        elements.dropZone.addEventListener('dragover', onDragOver);
        elements.dropZone.addEventListener('dragleave', onDragLeave);
        elements.dropZone.addEventListener('drop', onDrop);
        elements.imageInput.addEventListener('change', onInputChange);
        elements.clearImageBtn.addEventListener('click', clearSelectedImage);
        elements.analyzeBtn.addEventListener('click', analyzeSelectedImage);
        elements.downloadBtn.addEventListener('click', () => downloadPdfReport(currentReport));
        elements.recentAnalysesList.addEventListener('click', onRecentAnalysisAction);

        renderRecentAnalyses();
    }

    function onDragOver(event) {
        event.preventDefault();
        elements.dropZone.classList.add('dragover');
    }

    function onDragLeave() {
        elements.dropZone.classList.remove('dragover');
    }

    function onDrop(event) {
        event.preventDefault();
        elements.dropZone.classList.remove('dragover');
        if (event.dataTransfer.files.length > 0) {
            handleSelectedFile(event.dataTransfer.files[0]);
        }
    }

    function onInputChange(event) {
        if (event.target.files.length > 0) {
            handleSelectedFile(event.target.files[0]);
        }
    }

    function getFileExtension(fileName) {
        const parts = String(fileName || '').split('.');
        return parts.length > 1 ? parts.pop().toLowerCase() : '';
    }

    function validateFile(file) {
        if (!file) {
            return 'Please choose an X-ray image to analyze.';
        }

        const extension = getFileExtension(file.name);
        const hasValidExtension = ALLOWED_EXTENSIONS.includes(extension);
        const hasValidMimeType = ALLOWED_MIME_TYPES.includes(file.type);

        if (!hasValidExtension && !hasValidMimeType) {
            return 'Invalid file format. Please upload a JPG, JPEG, or PNG image.';
        }

        if (file.size === 0) {
            return 'The selected image is empty. Please choose a different file.';
        }

        if (file.size > MAX_FILE_SIZE_BYTES) {
            return 'File size must be 10MB or smaller.';
        }

        return '';
    }

    function handleSelectedFile(file) {
        const validationMessage = validateFile(file);
        if (validationMessage) {
            showUploadError(validationMessage);
            clearSelectedImage({ keepResults: true, keepNotification: true });
            return;
        }

        hideUploadError();
        selectedFile = file;

        const reader = new FileReader();
        reader.onload = event => {
            selectedPreviewUrl = event.target.result;
            elements.previewImg.src = selectedPreviewUrl;
            elements.previewName.textContent = file.name;
            elements.previewMeta.textContent = `${formatFileSize(file.size)} | ${file.type || extensionToLabel(file.name)}`;
            elements.imagePreview.style.display = 'block';
            elements.analyzeBtn.style.display = 'inline-flex';
            elements.dropZone.classList.add('has-file');
        };
        reader.readAsDataURL(file);
    }

    function clearSelectedImage(options = {}) {
        selectedFile = null;
        selectedPreviewUrl = '';
        elements.imageInput.value = '';
        elements.previewImg.removeAttribute('src');
        elements.previewName.textContent = '';
        elements.previewMeta.textContent = '';
        elements.imagePreview.style.display = 'none';
        elements.analyzeBtn.style.display = 'none';
        elements.dropZone.classList.remove('has-file', 'dragover');

        if (!options.keepNotification) {
            hideUploadError();
        }
    }

    function showUploadError(message) {
        elements.uploadError.textContent = message;
        elements.uploadError.classList.remove('d-none');
    }

    function hideUploadError() {
        elements.uploadError.textContent = '';
        elements.uploadError.classList.add('d-none');
    }

    function showResultsError(message) {
        elements.resultsError.textContent = message;
        elements.resultsError.classList.remove('d-none');
    }

    function hideResultsError() {
        elements.resultsError.textContent = '';
        elements.resultsError.classList.add('d-none');
    }

    function setActionButtonLoading(isLoading) {
        if (isLoading) {
            elements.analyzeBtn.disabled = true;
            elements.analyzeBtn.dataset.originalText = elements.analyzeBtn.innerHTML;
            elements.analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Analyzing X-Ray...';
            return;
        }

        elements.analyzeBtn.disabled = false;
        elements.analyzeBtn.innerHTML = elements.analyzeBtn.dataset.originalText || '<i class="fas fa-wave-square me-2"></i>Analyze X-Ray';
    }

    function setPanelState(state) {
        elements.emptyState.classList.toggle('d-none', state !== 'empty');
        elements.loadingState.classList.toggle('d-none', state !== 'loading');
        elements.resultsContainer.classList.toggle('d-none', state !== 'results');
    }

    function startLoadingAnimation() {
        let stepIndex = 0;
        elements.loadingStep.textContent = LOADING_STEPS[stepIndex];
        stopLoadingAnimation();
        loadingIntervalId = window.setInterval(() => {
            stepIndex = (stepIndex + 1) % LOADING_STEPS.length;
            elements.loadingStep.textContent = LOADING_STEPS[stepIndex];
        }, 1600);
    }

    function stopLoadingAnimation() {
        if (loadingIntervalId) {
            window.clearInterval(loadingIntervalId);
            loadingIntervalId = null;
        }
    }

    async function analyzeSelectedImage() {
        if (!selectedFile || !selectedPreviewUrl) {
            showUploadError('Please upload a valid X-ray image before starting the analysis.');
            return;
        }

        hideUploadError();
        hideResultsError();
        setActionButtonLoading(true);
        setPanelState('loading');
        startLoadingAnimation();

        const formData = new FormData();
        formData.append('file', selectedFile);

        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

        try {
            const response = await fetch('/api/xray/analyze', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                signal: controller.signal
            });

            const payload = await parseResponse(response);
            if (!response.ok) {
                throw new Error(payload?.detail || 'X-ray analysis failed. Please try again.');
            }

            const report = buildReportRecord(payload);
            currentReport = report;
            saveReport(report);
            renderResult(report);
            renderRecentAnalyses();
            showNotification('X-ray analysis completed successfully.', 'success', 3500);
        } catch (error) {
            const message = error.name === 'AbortError'
                ? 'The X-ray analysis timed out. Please try again with a clearer image.'
                : error.message || 'An unexpected error interrupted the X-ray analysis.';
            setPanelState('empty');
            showResultsError(message);
            showNotification(message, 'danger', 5000);
        } finally {
            window.clearTimeout(timeoutId);
            stopLoadingAnimation();
            setActionButtonLoading(false);
        }
    }

    async function parseResponse(response) {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            return response.json();
        }

        const text = await response.text();
        if (!text) {
            return {};
        }

        try {
            return JSON.parse(text);
        } catch (error) {
            return { detail: text };
        }
    }

    function buildReportRecord(apiResult) {
        const now = new Date();
        return {
            id: `${now.getTime()}-${Math.random().toString(36).slice(2, 9)}`,
            fileName: selectedFile.name,
            mimeType: selectedFile.type || inferMimeTypeFromPreview(selectedPreviewUrl),
            previewUrl: selectedPreviewUrl,
            analysisDate: now.toISOString(),
            analysis: {
                image_type: cleanText(apiResult.image_type, 'Unknown'),
                findings: normalizeList(apiResult.findings, ['No findings returned by the AI service.']),
                abnormalities: normalizeList(apiResult.abnormalities),
                severity: normalizeSeverity(apiResult.severity),
                confidence: cleanText(apiResult.confidence, 'Unavailable'),
                summary: cleanText(
                    apiResult.summary,
                    'AI-generated X-ray analysis report is unavailable. This is not a medical diagnosis.'
                ),
                recommendations: normalizeList(apiResult.recommendations, [
                    'Consult a qualified healthcare professional or radiologist for formal review.'
                ])
            }
        };
    }

    function cleanText(value, fallback = '') {
        const cleaned = String(value || '').trim();
        return cleaned || fallback;
    }

    function normalizeList(value, fallback = []) {
        if (Array.isArray(value)) {
            const cleaned = value.map(item => String(item || '').trim()).filter(Boolean);
            if (cleaned.length) {
                return cleaned;
            }
        } else if (typeof value === 'string' && value.trim()) {
            return [value.trim()];
        }

        return [...fallback];
    }

    function normalizeSeverity(value) {
        const normalized = String(value || '').trim().toLowerCase();
        if (normalized === 'low') {
            return 'Low';
        }
        if (normalized === 'high') {
            return 'High';
        }
        return 'Medium';
    }

    function renderResult(report) {
        hideResultsError();
        setPanelState('results');

        const { analysis } = report;
        elements.resultImage.src = report.previewUrl;
        elements.resultImage.alt = `${analysis.image_type} X-ray preview`;
        elements.resultFileName.textContent = report.fileName;
        elements.resultImageType.textContent = analysis.image_type;
        elements.resultDate.textContent = formatDisplayDate(report.analysisDate);
        elements.resultConfidence.textContent = analysis.confidence;
        renderSeverityBadge(analysis.severity);
        renderConfidenceMeter(analysis.confidence);
        renderList(elements.findingsList, analysis.findings, 'No findings returned.');
        renderList(elements.abnormalitiesList, analysis.abnormalities, 'No specific abnormalities highlighted.');
        renderList(elements.recommendationsList, analysis.recommendations, 'No recommendations returned.');
        elements.summaryText.innerHTML = escapeHtml(analysis.summary).replace(/\n/g, '<br>');
    }

    function renderSeverityBadge(severity) {
        const normalized = normalizeSeverity(severity);
        elements.resultSeverity.textContent = normalized;
        elements.resultSeverity.className = `severity-badge severity-${normalized.toLowerCase()}`;
    }

    function renderConfidenceMeter(confidenceLabel) {
        const score = extractConfidenceScore(confidenceLabel);
        elements.resultConfidenceBar.style.width = `${score}%`;
        elements.resultConfidenceBar.setAttribute('aria-valuenow', String(score));
        elements.resultConfidenceBar.className = `progress-bar ${score >= 75 ? 'bg-success' : score >= 45 ? 'bg-warning' : 'bg-danger'}`;
    }

    function extractConfidenceScore(confidenceLabel) {
        const match = String(confidenceLabel || '').match(/(\d{1,3})(?:\.\d+)?\s*%?/);
        if (match) {
            return Math.max(0, Math.min(100, Number(match[1])));
        }

        const normalized = String(confidenceLabel || '').toLowerCase();
        if (normalized.includes('high')) {
            return 85;
        }
        if (normalized.includes('medium')) {
            return 60;
        }
        if (normalized.includes('low')) {
            return 35;
        }
        return 50;
    }

    function renderList(container, items, fallbackText) {
        if (!items.length) {
            container.innerHTML = `<li class="xray-list-empty">${escapeHtml(fallbackText)}</li>`;
            return;
        }

        container.innerHTML = items
            .map(item => `<li>${escapeHtml(item)}</li>`)
            .join('');
    }

    function saveReport(report) {
        const reports = loadSavedReports();
        const updatedReports = [report, ...reports.filter(item => item.id !== report.id)].slice(0, 8);
        storageHelper.set(REPORT_STORAGE_KEY, updatedReports);
    }

    function loadSavedReports() {
        const savedValue = storageHelper.get(REPORT_STORAGE_KEY);
        return Array.isArray(savedValue) ? savedValue : [];
    }

    function renderRecentAnalyses() {
        const reports = loadSavedReports();
        if (!reports.length) {
            elements.recentAnalysesList.innerHTML = `
                <div class="dashboard-card recent-xray-empty">
                    <p class="fw-bold mb-2">No X-ray analyses yet</p>
                    <p class="text-light-secondary small mb-0">Your recent AI-generated X-ray analyses will appear here after the first upload.</p>
                </div>
            `;
            return;
        }

        elements.recentAnalysesList.innerHTML = reports.map(report => {
            const severity = normalizeSeverity(report.analysis?.severity);
            return `
                <div class="dashboard-card recent-xray-card">
                    <div class="image-preview-container recent-xray-media">
                        <img src="${report.previewUrl}" alt="${escapeHtml(report.fileName)} preview" class="recent-xray-thumb">
                    </div>
                    <div class="recent-xray-body">
                        <div class="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-2">
                            <div>
                                <p class="fw-bold mb-1">${escapeHtml(report.analysis?.image_type || 'Unknown X-ray')}</p>
                                <p class="text-light-secondary small mb-0">${escapeHtml(report.fileName)}</p>
                            </div>
                            <span class="severity-badge severity-${severity.toLowerCase()}">${severity}</span>
                        </div>
                        <p class="text-light-secondary small mb-3">${escapeHtml(formatDisplayDate(report.analysisDate))}</p>
                        <p class="recent-xray-summary mb-3">${escapeHtml(truncateText(report.analysis?.summary || '', 120))}</p>
                        <div class="d-flex flex-wrap gap-2">
                            <button class="btn btn-outline-primary btn-sm" data-action="view" data-report-id="${report.id}">
                                <i class="fas fa-eye me-1"></i>View Result
                            </button>
                            <button class="btn btn-primary btn-sm" data-action="download" data-report-id="${report.id}">
                                <i class="fas fa-file-arrow-down me-1"></i>Download PDF
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function onRecentAnalysisAction(event) {
        const button = event.target.closest('[data-report-id]');
        if (!button) {
            return;
        }

        const reportId = button.getAttribute('data-report-id');
        const report = loadSavedReports().find(item => item.id === reportId);
        if (!report) {
            showNotification('That saved report could not be found in local storage.', 'warning', 4000);
            return;
        }

        if (button.dataset.action === 'download') {
            downloadPdfReport(report);
            return;
        }

        currentReport = report;
        renderResult(report);
        showNotification('Loaded a saved X-ray analysis report.', 'info', 2500);
    }

    async function downloadPdfReport(report) {
        if (!report) {
            showNotification('Run an X-ray analysis first to download a report.', 'warning', 3500);
            return;
        }

        if (!window.jspdf || !window.jspdf.jsPDF) {
            showNotification('PDF generation is unavailable because jsPDF did not load.', 'danger', 5000);
            return;
        }

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({ unit: 'pt', format: 'a4' });
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const margin = 44;
        const maxTextWidth = pageWidth - (margin * 2);
        const lineHeight = 18;
        let cursorY = 52;

        const ensureSpace = requiredHeight => {
            if (cursorY + requiredHeight <= pageHeight - margin) {
                return;
            }
            doc.addPage();
            cursorY = 52;
        };

        const addWrappedText = (text, options = {}) => {
            const fontSize = options.fontSize || 11;
            const fontStyle = options.fontStyle || 'normal';
            const color = options.color || [31, 41, 55];
            doc.setFont('helvetica', fontStyle);
            doc.setFontSize(fontSize);
            doc.setTextColor(...color);

            const lines = doc.splitTextToSize(String(text || ''), maxTextWidth);
            ensureSpace(lines.length * lineHeight + 10);
            doc.text(lines, margin, cursorY);
            cursorY += (lines.length * lineHeight) + 8;
        };

        const addSectionTitle = title => {
            ensureSpace(28);
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(14);
            doc.setTextColor(0, 112, 149);
            doc.text(title, margin, cursorY);
            cursorY += 22;
        };

        doc.setFont('helvetica', 'bold');
        doc.setFontSize(22);
        doc.setTextColor(5, 10, 26);
        doc.text('MediAI X-Ray Analysis Report', margin, cursorY);
        cursorY += 28;

        addWrappedText(`Analysis Date: ${formatDisplayDate(report.analysisDate)}`, { fontSize: 11, fontStyle: 'bold' });
        addWrappedText(`Image File: ${report.fileName}`, { fontSize: 11 });
        addWrappedText(`Detected Image Type: ${report.analysis.image_type}`, { fontSize: 11 });
        addWrappedText(`Severity: ${report.analysis.severity}`, { fontSize: 11 });
        addWrappedText(`Confidence: ${report.analysis.confidence}`, { fontSize: 11 });

        ensureSpace(88);
        doc.setFillColor(255, 248, 230);
        doc.roundedRect(margin, cursorY, maxTextWidth, 54, 8, 8, 'F');
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(10);
        doc.setTextColor(140, 90, 0);
        doc.text('Medical Disclaimer', margin + 14, cursorY + 18);
        doc.setFont('helvetica', 'normal');
        doc.text(
            doc.splitTextToSize(
                'This analysis is generated by AI and should not be considered a medical diagnosis. Please consult a qualified healthcare professional.',
                maxTextWidth - 28
            ),
            margin + 14,
            cursorY + 36
        );
        cursorY += 72;

        if (report.previewUrl) {
            try {
                const imageDimensions = await getImageDimensions(report.previewUrl);
                const maxImageWidth = maxTextWidth;
                const maxImageHeight = 220;
                const scale = Math.min(
                    maxImageWidth / imageDimensions.width,
                    maxImageHeight / imageDimensions.height,
                    1
                );
                const renderWidth = imageDimensions.width * scale;
                const renderHeight = imageDimensions.height * scale;
                ensureSpace(renderHeight + 18);
                const imageFormat = inferPdfImageFormat(report.previewUrl);
                doc.addImage(report.previewUrl, imageFormat, margin, cursorY, renderWidth, renderHeight);
                cursorY += renderHeight + 18;
            } catch (error) {
                console.warn('[xray] Could not embed preview image in PDF:', error);
            }
        }

        addSectionTitle('Visible Findings');
        report.analysis.findings.forEach(item => addWrappedText(`- ${item}`));

        addSectionTitle('Potential Abnormalities');
        if (report.analysis.abnormalities.length) {
            report.analysis.abnormalities.forEach(item => addWrappedText(`- ${item}`));
        } else {
            addWrappedText('- No specific abnormalities were highlighted by the AI response.');
        }

        addSectionTitle('Recommendations');
        report.analysis.recommendations.forEach(item => addWrappedText(`- ${item}`));

        addSectionTitle('AI-Generated Medical Report');
        addWrappedText(report.analysis.summary, { fontSize: 11 });

        const dateFragment = report.analysisDate.slice(0, 10);
        doc.save(`mediai-xray-report-${dateFragment}.pdf`);
    }

    function getImageDimensions(dataUrl) {
        return new Promise((resolve, reject) => {
            const image = new Image();
            image.onload = () => resolve({ width: image.width, height: image.height });
            image.onerror = reject;
            image.src = dataUrl;
        });
    }

    function inferPdfImageFormat(dataUrl) {
        return dataUrl.startsWith('data:image/png') ? 'PNG' : 'JPEG';
    }

    function inferMimeTypeFromPreview(previewUrl) {
        if (String(previewUrl || '').startsWith('data:image/png')) {
            return 'image/png';
        }
        return 'image/jpeg';
    }

    function extensionToLabel(fileName) {
        const extension = getFileExtension(fileName);
        return extension ? extension.toUpperCase() : 'Image';
    }

    function formatFileSize(size) {
        if (size >= 1024 * 1024) {
            return `${(size / (1024 * 1024)).toFixed(2)} MB`;
        }
        return `${Math.max(1, Math.round(size / 1024))} KB`;
    }

    function formatDisplayDate(value) {
        return new Date(value).toLocaleString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    }

    function truncateText(value, maxLength) {
        if (value.length <= maxLength) {
            return value;
        }
        return `${value.slice(0, maxLength - 1)}...`;
    }

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[char]));
    }

    init();
})();
