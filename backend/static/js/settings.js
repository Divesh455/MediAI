// ===== settings.js =====
console.log('[settings] Settings script loaded');

function initSettings() {
    console.log('[settings] Initializing settings logic');
    // 1. Theme Elements & Syncing
    const darkModeRadio = document.getElementById('darkMode');
    const lightModeRadio = document.getElementById('lightMode');

    function syncThemeRadios() {
        const currentTheme = localStorage.getItem('theme') || 'dark';
        if (currentTheme === 'light') {
            if (lightModeRadio) lightModeRadio.checked = true;
        } else {
            if (darkModeRadio) darkModeRadio.checked = true;
        }
    }

    if (darkModeRadio && lightModeRadio) {
        darkModeRadio.addEventListener('change', () => {
            document.body.classList.remove('light-mode');
            localStorage.setItem('theme', 'dark');
            if (typeof updateThemeIcon === 'function') updateThemeIcon('dark');
            console.log('[settings] Dark theme set via settings');
        });

        lightModeRadio.addEventListener('change', () => {
            document.body.classList.add('light-mode');
            localStorage.setItem('theme', 'light');
            if (typeof updateThemeIcon === 'function') updateThemeIcon('light');
            console.log('[settings] Light theme set via settings');
        });
    }

    // 2. Element References
    const languageSelect = document.getElementById('languageSelect');
    const timezoneSelect = document.getElementById('timezoneSelect');
    const saveGeneralBtn = document.getElementById('saveGeneralBtn');

    const emailNotifications = document.getElementById('emailNotifications');
    const pushNotifications = document.getElementById('pushNotifications');
    const reportReminders = document.getElementById('reportReminders');
    const marketingEmails = document.getElementById('marketingEmails');
    const saveNotificationsBtn = document.getElementById('saveNotificationsBtn');

    const profileVisibility = document.getElementById('profileVisibility');
    const shareData = document.getElementById('shareData');
    const savePrivacyBtn = document.getElementById('savePrivacyBtn');

    const currentPasswordInput = document.getElementById('currentPassword');
    const newPasswordInput = document.getElementById('newPassword');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const updatePasswordBtn = document.getElementById('updatePasswordBtn');

    const exportDataBtn = document.getElementById('exportDataBtn');
    const deleteAccountBtn = document.getElementById('deleteAccountBtn');

    // 3. Load preferences from LocalStorage
    function loadPreferences() {
        syncThemeRadios();

        if (languageSelect) languageSelect.value = localStorage.getItem('pref_language') || 'en';
        if (timezoneSelect) timezoneSelect.value = localStorage.getItem('pref_timezone') || 'UTC-5';

        if (emailNotifications) emailNotifications.checked = localStorage.getItem('pref_email_notif') !== 'false';
        if (pushNotifications) pushNotifications.checked = localStorage.getItem('pref_push_notif') !== 'false';
        if (reportReminders) reportReminders.checked = localStorage.getItem('pref_reminders_notif') === 'true';
        if (marketingEmails) marketingEmails.checked = localStorage.getItem('pref_marketing_notif') === 'true';

        if (profileVisibility) profileVisibility.value = localStorage.getItem('pref_privacy_visibility') || 'private';
        if (shareData) shareData.checked = localStorage.getItem('pref_privacy_share') !== 'false';
    }

    // Initialize UI values
    loadPreferences();

    // 4. Save General Changes
    if (saveGeneralBtn) {
        saveGeneralBtn.addEventListener('click', () => {
            if (languageSelect) localStorage.setItem('pref_language', languageSelect.value);
            if (timezoneSelect) localStorage.setItem('pref_timezone', timezoneSelect.value);
            if (typeof showNotification === 'function') {
                showNotification('General settings saved successfully!', 'success');
            } else {
                alert('General settings saved successfully!');
            }
        });
    }

    // 5. Save Notifications Settings
    if (saveNotificationsBtn) {
        saveNotificationsBtn.addEventListener('click', () => {
            if (emailNotifications) localStorage.setItem('pref_email_notif', emailNotifications.checked);
            if (pushNotifications) localStorage.setItem('pref_push_notif', pushNotifications.checked);
            if (reportReminders) localStorage.setItem('pref_reminders_notif', reportReminders.checked);
            if (marketingEmails) localStorage.setItem('pref_marketing_notif', marketingEmails.checked);
            if (typeof showNotification === 'function') {
                showNotification('Notification preferences saved!', 'success');
            } else {
                alert('Notification preferences saved!');
            }
        });
    }

    // 6. Save Privacy Settings
    if (savePrivacyBtn) {
        savePrivacyBtn.addEventListener('click', () => {
            if (profileVisibility) localStorage.setItem('pref_privacy_visibility', profileVisibility.value);
            if (shareData) localStorage.setItem('pref_privacy_share', shareData.checked);
            if (typeof showNotification === 'function') {
                showNotification('Privacy settings saved!', 'success');
            } else {
                alert('Privacy settings saved!');
            }
        });
    }

    // 7. Security Tab: Update Password
    if (updatePasswordBtn) {
        updatePasswordBtn.addEventListener('click', async () => {
            const currentPassword = currentPasswordInput.value;
            const newPassword = newPasswordInput.value;
            const confirmPassword = confirmPasswordInput.value;

            if (!currentPassword || !newPassword || !confirmPassword) {
                showNotification('All password fields are required.', 'danger');
                return;
            }

            if (newPassword !== confirmPassword) {
                showNotification('New password and confirm password do not match.', 'danger');
                return;
            }

            if (newPassword.length < 8) {
                showNotification('New password must be at least 8 characters long.', 'danger');
                return;
            }

            // Password strength check (uppercase, lowercase, number)
            if (!/[A-Z]/.test(newPassword) || !/[a-z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
                showNotification('Password must include an uppercase letter, lowercase letter, and a number.', 'danger');
                return;
            }

            if (typeof setLoading === 'function') setLoading(updatePasswordBtn, true);

            try {
                await window.mediaiApi.request('/auth/change-password', {
                    method: 'POST',
                    body: JSON.stringify({
                        currentPassword: currentPassword,
                        newPassword: newPassword
                    })
                });

                showNotification('Password updated successfully!', 'success');
                // Clear fields
                currentPasswordInput.value = '';
                newPasswordInput.value = '';
                confirmPasswordInput.value = '';
            } catch (error) {
                showNotification(error.message || 'Failed to update password.', 'danger');
            } finally {
                if (typeof setLoading === 'function') setLoading(updatePasswordBtn, false);
            }
        });
    }

    // 8. Account Tab: Export Health Data
    if (exportDataBtn) {
        exportDataBtn.addEventListener('click', async () => {
            if (typeof setLoading === 'function') setLoading(exportDataBtn, true);

            try {
                const profile = await window.mediaiApi.request('/auth/profile');
                let history = [];
                try {
                    // Fetch history if available
                    history = await window.mediaiApi.request('/dashboard/stats');
                } catch (e) {
                    console.log('Stats endpoint failed or empty history', e);
                }

                const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({
                    exportedAt: new Date().toISOString(),
                    profile: profile,
                    dashboardStats: history,
                    localPreferences: {
                        theme: localStorage.getItem('theme'),
                        language: localStorage.getItem('pref_language'),
                        timezone: localStorage.getItem('pref_timezone'),
                        emailNotifications: localStorage.getItem('pref_email_notif'),
                        pushNotifications: localStorage.getItem('pref_push_notif')
                    }
                }, null, 2));

                const downloadAnchor = document.createElement('a');
                downloadAnchor.setAttribute("href", dataStr);
                const safeName = (profile.name || 'user').toLowerCase().replace(/[^a-z0-9]/g, '_');
                downloadAnchor.setAttribute("download", `${safeName}_mediai_health_data.json`);
                document.body.appendChild(downloadAnchor);
                downloadAnchor.click();
                downloadAnchor.remove();

                showNotification('Health data exported successfully!', 'success');
            } catch (error) {
                showNotification('Failed to export data: ' + error.message, 'danger');
            } finally {
                if (typeof setLoading === 'function') setLoading(exportDataBtn, false);
            }
        });
    }

    // 9. Account Tab: Delete Account
    if (deleteAccountBtn) {
        deleteAccountBtn.addEventListener('click', async () => {
            const confirmed = confirm('WARNING: Are you absolutely sure you want to delete your account? This action cannot be undone and all your history, reports, and sessions will be deleted permanently.');
            if (!confirmed) return;

            if (typeof setLoading === 'function') setLoading(deleteAccountBtn, true);

            try {
                await window.mediaiApi.request('/auth/delete-account', {
                    method: 'DELETE'
                });

                alert('Your account has been deleted permanently. Thank you for using MediAI.');
                localStorage.clear();
                window.location.href = '/login';
            } catch (error) {
                showNotification('Failed to delete account: ' + error.message, 'danger');
                if (typeof setLoading === 'function') setLoading(deleteAccountBtn, false);
            }
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSettings);
} else {
    initSettings();
}
