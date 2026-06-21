// ===== MediAI Main App Script =====

console.log('[v0] MediAI App Initialized');

// ===== Theme Toggle =====
const themeToggle = document.getElementById('themeToggle');
if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
}

function toggleTheme() {
    const isDarkMode = document.body.classList.contains('light-mode');
    if (isDarkMode) {
        document.body.classList.remove('light-mode');
        localStorage.setItem('theme', 'dark');
        updateThemeIcon('dark');
    } else {
        document.body.classList.add('light-mode');
        localStorage.setItem('theme', 'light');
        updateThemeIcon('light');
    }
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('#themeToggle i');
    if (icon) {
        if (theme === 'light') {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        }
    }
}

// Load saved theme
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        updateThemeIcon('light');
    } else {
        updateThemeIcon('dark');
    }
}

initTheme();

// ===== AOS Animation Initialization =====
if (typeof AOS !== 'undefined') {
    AOS.init({
        duration: 800,
        easing: 'ease-in-out',
        once: false
    });
}

// ===== Sidebar Toggle for Mobile =====
const sidebarToggle = document.getElementById('sidebarToggle');
if (sidebarToggle && sidebarToggle.dataset.sidebarBound !== 'true') {
    sidebarToggle.dataset.sidebarBound = 'true';
    sidebarToggle.addEventListener('click', function() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.toggle('show');
        }
    });
}

// Close sidebar when clicking on a link (mobile)
document.querySelectorAll('.sidebar .nav-link').forEach(link => {
    link.addEventListener('click', function() {
        if (window.innerWidth < 768) {
            const sidebar = document.getElementById('sidebar');
            if (sidebar) {
                sidebar.classList.remove('show');
            }
        }
    });
});

// ===== API Request Wrapper =====
class MediAIApi {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = { ...(options.headers || {}) };
        const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
        const authToken = localStorage.getItem('token');

        if (!isFormData && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }
        if (authToken && !headers.Authorization) {
            headers.Authorization = `Bearer ${authToken}`;
        }

        const config = {
            credentials: 'same-origin',
            headers,
            ...options
        };

        try {
            const response = await fetch(url, config);
            const contentType = response.headers.get('content-type') || '';
            const responseBody = contentType.includes('application/json')
                ? await response.json()
                : await response.text();

            if (!response.ok) {
                const errorMessage = typeof responseBody === 'string'
                    ? responseBody
                    : responseBody?.detail || `API Error: ${response.status}`;
                const error = new Error(errorMessage);
                error.status = response.status;
                throw error;
            }
            return responseBody;
        } catch (error) {
            console.error('[v0] API Error:', error);
            throw error;
        }
    }

    async predict(data) {
        return this.request('/predict', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async analyzeXRay(formData) {
        return this.request('/api/xray/analyze', {
            method: 'POST',
            body: formData
        });
    }

    async chat(message) {
        return this.request('/chat', {
            method: 'POST',
            body: JSON.stringify({ message })
        });
    }
}

// Create global API instance
window.mediaiApi = new MediAIApi();

// ===== Auth Helpers =====
async function logout() {
    try {
        await fetch('/auth/logout', { method: 'POST' });
    } catch (error) {
        console.error('[auth] Logout failed:', error);
    } finally {
        localStorage.removeItem('token');
        localStorage.removeItem('user_id');
        window.location.href = '/login';
    }
}

document.querySelectorAll('a').forEach(link => {
    if (link.textContent.trim().toLowerCase() === 'logout') {
        link.addEventListener('click', event => {
            event.preventDefault();
            logout();
        });
    }
});

// ===== Form Validation Helper =====
function validateForm(formElement) {
    if (!formElement.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
        formElement.classList.add('was-validated');
        return false;
    }
    return true;
}

// ===== Notification Helper =====
function showNotification(message, type = 'info', duration = 3000) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    if (duration) {
        setTimeout(() => {
            alertDiv.remove();
        }, duration);
    }
}

// ===== Loading State Helper =====
function setLoading(element, isLoading) {
    if (isLoading) {
        element.disabled = true;
        element.dataset.originalText = element.innerHTML;
        element.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
    } else {
        element.disabled = false;
        element.innerHTML = element.dataset.originalText;
    }
}

// ===== Format Date Helper =====
function formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// ===== Local Storage Helpers =====
const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('[v0] Storage Error:', error);
        }
    },
    get(key) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (error) {
            console.error('[v0] Storage Error:', error);
            return null;
        }
    },
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('[v0] Storage Error:', error);
        }
    }
};

console.log('[v0] App modules loaded successfully');
