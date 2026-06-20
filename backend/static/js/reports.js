(() => {
    const state = {
        report: null,
    };

    const elements = {
        startDate: document.getElementById('startDate'),
        endDate: document.getElementById('endDate'),
        generateReportBtn: document.getElementById('generateReportBtn'),
        downloadPdfBtn: document.getElementById('downloadPdfBtn'),
        downloadDocxBtn: document.getElementById('downloadDocxBtn'),
        printReportBtn: document.getElementById('printReportBtn'),
        reportLoading: document.getElementById('reportLoading'),
        reportEmptyState: document.getElementById('reportEmptyState'),
        generatedReport: document.getElementById('generatedReport'),
        reportId: document.getElementById('reportId'),
        reportGeneratedAt: document.getElementById('reportGeneratedAt'),
        reportDateRange: document.getElementById('reportDateRange'),
        reportPatient: document.getElementById('reportPatient'),
        executiveSummary: document.getElementById('executiveSummary'),
        keyConcernChips: document.getElementById('keyConcernChips'),
        totalPredictions: document.getElementById('totalPredictions'),
        totalXrays: document.getElementById('totalXrays'),
        totalChats: document.getElementById('totalChats'),
        mostCommonConcern: document.getElementById('mostCommonConcern'),
        diseasePredictionsList: document.getElementById('diseasePredictionsList'),
        xrayAnalysesList: document.getElementById('xrayAnalysesList'),
        chatHistoryList: document.getElementById('chatHistoryList'),
        recommendationsList: document.getElementById('recommendationsList'),
    };

    function init() {
        if (!elements.generateReportBtn) {
            return;
        }

        document.getElementById('sidebarToggle')?.addEventListener('click', () => {
            document.getElementById('sidebar')?.classList.toggle('show');
        });

        elements.generateReportBtn.addEventListener('click', handleGenerateReport);
        elements.downloadPdfBtn.addEventListener('click', () => downloadReportFile('pdf'));
        elements.downloadDocxBtn.addEventListener('click', () => downloadReportFile('docx'));
        elements.printReportBtn.addEventListener('click', handlePrintReport);

        setDefaultDateRange();
        setReportState('empty');
    }

    function setDefaultDateRange() {
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 30);

        elements.startDate.value = toDateInputValue(start);
        elements.endDate.value = toDateInputValue(end);
    }

    function toDateInputValue(date) {
        return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
            .toISOString()
            .slice(0, 10);
    }

    function setReportState(stateName) {
        elements.reportLoading.classList.toggle('d-none', stateName !== 'loading');
        elements.reportEmptyState.classList.toggle('d-none', stateName !== 'empty');
        elements.generatedReport.classList.toggle('d-none', stateName !== 'report');
    }

    async function handleGenerateReport() {
        const startDate = elements.startDate.value;
        const endDate = elements.endDate.value;

        if (!startDate || !endDate) {
            showNotification('Please choose both a start date and an end date.', 'warning', 4000);
            return;
        }

        if (startDate > endDate) {
            showNotification('Start date must be earlier than or equal to the end date.', 'warning', 4000);
            return;
        }

        setReportState('loading');
        setButtonsLoading(true);

        try {
            const response = await fetch('/reports/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    user_id: null,
                    start_date: startDate,
                    end_date: endDate,
                }),
            });

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            const payload = await parseJsonResponse(response);
            if (!response.ok) {
                throw new Error(payload?.detail || 'Could not generate the report.');
            }

            state.report = payload;
            renderReport(payload);
            setReportState('report');
            setButtonsLoading(false, true);
            showNotification('Report generated successfully.', 'success', 3000);
        } catch (error) {
            console.error('[reports] Generate failed:', error);
            state.report = null;
            setReportState('empty');
            setButtonsLoading(false, false);
            showNotification(error.message || 'Failed to generate the report.', 'danger', 5000);
        } finally {
            setReportState(state.report ? 'report' : 'empty');
            setButtonsLoading(false, !!state.report);
        }
    }

    function setButtonsLoading(isLoading, hasReport = false) {
        elements.generateReportBtn.disabled = isLoading;
        elements.generateReportBtn.innerHTML = isLoading
            ? '<i class="fas fa-spinner fa-spin me-2"></i>Generating...'
            : '<i class="fas fa-wand-magic-sparkles me-2"></i>Generate Report';
        elements.downloadPdfBtn.disabled = isLoading || !hasReport;
        elements.downloadDocxBtn.disabled = isLoading || !hasReport;
        elements.printReportBtn.disabled = isLoading || !hasReport;
    }

    async function parseJsonResponse(response) {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            return response.json();
        }
        const text = await response.text();
        try {
            return JSON.parse(text);
        } catch {
            return { detail: text };
        }
    }

    function renderReport(report) {
        elements.reportId.textContent = report.report_id || '-';
        elements.reportGeneratedAt.textContent = formatDisplayDate(report.generated_at);
        elements.reportDateRange.textContent = `${formatDate(report.start_date)} - ${formatDate(report.end_date)}`;
        elements.reportPatient.textContent = report.user
            ? `${report.user.first_name || ''} ${report.user.last_name || ''}`.trim()
            : '-';
        elements.executiveSummary.textContent = report.summary?.executive_summary || '';
        renderChipList(elements.keyConcernChips, report.summary?.key_concerns || ['General Health']);
        elements.totalPredictions.textContent = String(report.statistics?.total_predictions ?? 0);
        elements.totalXrays.textContent = String(report.statistics?.total_xrays ?? 0);
        elements.totalChats.textContent = String(report.statistics?.total_chats ?? 0);
        elements.mostCommonConcern.textContent = report.statistics?.most_common_health_concern || '-';

        renderPredictionList(report.disease_predictions || []);
        renderXrayList(report.xray_analyses || []);
        renderChatList(report.chat_history || []);
        renderRecommendationList(report.recommendations || []);
    }

    function renderChipList(container, items) {
        if (!items.length) {
            container.innerHTML = '<span class="report-chip">No key concerns found</span>';
            return;
        }

        container.innerHTML = items.map(item => `<span class="report-chip">${escapeHtml(item)}</span>`).join('');
    }

    function renderPredictionList(items) {
        if (!items.length) {
            elements.diseasePredictionsList.innerHTML = `
                <div class="report-item">
                    <p class="report-item-title mb-1">No disease predictions in this date range</p>
                    <p class="report-item-muted mb-0">Run a prediction to include it in the next report.</p>
                </div>
            `;
            return;
        }

        elements.diseasePredictionsList.innerHTML = items.map((item, index) => `
            <div class="report-item">
                <div class="report-item-header">
                    <div>
                        <p class="report-item-title">Prediction #${index + 1}</p>
                        <p class="report-item-subtitle">${escapeHtml(item.prediction_date)}</p>
                    </div>
                    <span class="severity-badge severity-${normalizeSeverity(item.risk_level).toLowerCase()}">
                        ${escapeHtml(item.risk_level || 'Unknown')}
                    </span>
                </div>
                <p class="report-item-text"><strong>Symptoms:</strong> ${escapeHtml((item.input_symptoms || []).join(', ') || 'Not provided')}</p>
                <p class="report-item-text"><strong>Predicted disease:</strong> ${escapeHtml(item.predicted_disease || 'Unknown')}</p>
                <p class="report-item-text"><strong>Confidence:</strong> ${escapeHtml(item.confidence_score || 'Unavailable')}</p>
                <p class="report-item-text mb-0"><strong>Recommendations:</strong> ${escapeHtml((item.recommendations || []).join(', ') || 'Review with a clinician.')}</p>
            </div>
        `).join('');
    }

    function renderXrayList(items) {
        if (!items.length) {
            elements.xrayAnalysesList.innerHTML = `
                <div class="report-item">
                    <p class="report-item-title mb-1">No X-ray analyses in this date range</p>
                    <p class="report-item-muted mb-0">Upload an X-ray to include it in the report.</p>
                </div>
            `;
            return;
        }

        elements.xrayAnalysesList.innerHTML = items.map((item, index) => `
            <div class="report-item">
                <div class="report-item-header">
                    <div>
                        <p class="report-item-title">Analysis #${index + 1}</p>
                        <p class="report-item-subtitle">${escapeHtml(item.upload_date)}</p>
                    </div>
                    <span class="severity-badge severity-${normalizeSeverity(item.severity).toLowerCase()}">
                        ${escapeHtml(item.severity || 'Medium')}
                    </span>
                </div>
                <p class="report-item-text"><strong>Body part:</strong> ${escapeHtml(item.body_part || 'Unknown')}</p>
                <p class="report-item-text"><strong>Findings:</strong> ${escapeHtml((item.findings || []).join(', ') || 'None reported')}</p>
                <p class="report-item-text"><strong>AI explanation:</strong> ${escapeHtml(item.ai_explanation || '')}</p>
                <p class="report-item-text mb-0"><strong>Suggested action:</strong> ${escapeHtml((item.suggested_action || []).join(', ') || 'Review with a clinician.')}</p>
            </div>
        `).join('');
    }

    function renderChatList(items) {
        if (!items.length) {
            elements.chatHistoryList.innerHTML = `
                <div class="report-item">
                    <p class="report-item-title mb-1">No chat consultations in this date range</p>
                    <p class="report-item-muted mb-0">Conversation history will appear here after you chat with MediAI.</p>
                </div>
            `;
            return;
        }

        elements.chatHistoryList.innerHTML = items.map((item, index) => `
            <div class="report-item">
                <div class="report-item-header">
                    <div>
                        <p class="report-item-title">Consultation #${index + 1}</p>
                        <p class="report-item-subtitle">${escapeHtml(item.created_at)}</p>
                    </div>
                </div>
                <p class="report-item-text"><strong>Question:</strong> ${escapeHtml(item.question || '')}</p>
                <p class="report-item-text"><strong>Answer:</strong> ${escapeHtml(item.answer || '')}</p>
                <p class="report-item-text"><strong>Topics discussed:</strong> ${escapeHtml((item.topics_discussed || []).join(', ') || 'General Health')}</p>
                <p class="report-item-text mb-0"><strong>Follow-up:</strong> ${escapeHtml((item.follow_up_recommendations || []).join(', ') || 'Monitor symptoms and follow up if needed.')}</p>
            </div>
        `).join('');
    }

    function renderRecommendationList(items) {
        if (!items.length) {
            elements.recommendationsList.innerHTML = `
                <div class="report-item">
                    <p class="report-item-title mb-1">No recommendations available</p>
                    <p class="report-item-muted mb-0">Generate a report after more activity is available.</p>
                </div>
            `;
            return;
        }

        elements.recommendationsList.innerHTML = items.map(item => `
            <div class="report-item">
                <p class="report-item-text mb-0">${escapeHtml(item)}</p>
            </div>
        `).join('');
    }

    async function downloadReportFile(format) {
        if (!state.report?.report_id) {
            showNotification('Generate a report first before downloading files.', 'warning', 3500);
            return;
        }

        const endpoint = format === 'pdf'
            ? `/reports/${encodeURIComponent(state.report.report_id)}/pdf`
            : `/reports/${encodeURIComponent(state.report.report_id)}/docx`;

        try {
            const response = await fetch(endpoint, {
                credentials: 'same-origin',
            });

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            if (!response.ok) {
                const payload = await parseJsonResponse(response);
                throw new Error(payload?.detail || `Unable to download ${format.toUpperCase()} file.`);
            }

            const blob = await response.blob();
            const fileName = `${state.report.report_id}.${format}`;
            triggerBlobDownload(blob, fileName);
        } catch (error) {
            console.error('[reports] Download failed:', error);
            showNotification(error.message || `Failed to download ${format.toUpperCase()} report.`, 'danger', 5000);
        }
    }

    function triggerBlobDownload(blob, fileName) {
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = fileName;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.URL.revokeObjectURL(url);
    }

    function handlePrintReport() {
        if (!state.report?.report_id) {
            showNotification('Generate a report first before printing.', 'warning', 3500);
            return;
        }
        window.print();
    }

    function formatDate(value) {
        if (!value) {
            return '-';
        }
        const date = new Date(value);
        return date.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
        });
    }

    function formatDisplayDate(value) {
        if (!value) {
            return '-';
        }
        const date = new Date(value);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        });
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

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;',
        }[char]));
    }

    init();
})();
