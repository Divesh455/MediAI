const profileState = {
    profile: null,
    loaded: false,
    editing: false,
};

const profileElements = {
    loadingState: document.getElementById('profileLoadingState'),
    errorState: document.getElementById('profileErrorState'),
    retryButton: document.getElementById('retryProfileButton'),
    content: document.getElementById('profileContent'),
    form: document.getElementById('profileForm'),
    firstName: document.getElementById('firstName'),
    lastName: document.getElementById('lastName'),
    email: document.getElementById('email'),
    phone: document.getElementById('phone'),
    dob: document.getElementById('dob'),
    gender: document.getElementById('gender'),
    address: document.getElementById('address'),
    profileImage: document.getElementById('profileImage'),
    profileDisplayName: document.getElementById('profileDisplayName'),
    profileDisplayEmail: document.getElementById('profileDisplayEmail'),
    editButton: document.getElementById('editProfileButton'),
    cancelButton: document.getElementById('cancelProfileButton'),
    saveButton: document.getElementById('saveProfileButton'),
    actionGroup: document.getElementById('profileActionGroup'),
    uploadButton: document.getElementById('uploadPhotoButton'),
    photoInput: document.getElementById('profilePhotoInput'),
};

function getStoredToken() {
    return localStorage.getItem('token');
}

function clearAuthAndRedirect() {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    window.location.href = '/login';
}

function splitFullName(name) {
    const parts = String(name || '')
        .trim()
        .split(/\s+/)
        .filter(Boolean);

    if (!parts.length) {
        return { firstName: '', lastName: '' };
    }

    return {
        firstName: parts[0],
        lastName: parts.slice(1).join(' '),
    };
}

function normalizeProfile(profile) {
    const nameParts = splitFullName(profile?.name);
    const firstName = (profile?.first_name || nameParts.firstName || '').trim();
    const lastName = (profile?.last_name || nameParts.lastName || '').trim();

    return {
        id: profile?.id ?? null,
        name: [firstName, lastName].filter(Boolean).join(' ').trim(),
        first_name: firstName,
        last_name: lastName,
        email: String(profile?.email || '').trim(),
        phone: String(profile?.phone || '').trim(),
        gender: String(profile?.gender || '').trim(),
        dob: String(profile?.dob || '').trim(),
        address: String(profile?.address || '').trim(),
        profile_image: String(profile?.profile_image || '').trim(),
    };
}

function getProfileImageSrc(profile) {
    return profile.profile_image || '/img/placeholder-user.jpg';
}

function renderProfile(profile) {
    profileElements.profileDisplayName.textContent = profile.name || 'Your Profile';
    profileElements.profileDisplayEmail.textContent = profile.email || 'No email available';

    profileElements.profileImage.src = getProfileImageSrc(profile);
    profileElements.profileImage.alt = `${profile.name || 'Profile'} photo`;
    profileElements.profileImage.onerror = () => {
        profileElements.profileImage.onerror = null;
        profileElements.profileImage.src = '/img/placeholder-user.jpg';
    };

    profileElements.firstName.value = profile.first_name || '';
    profileElements.lastName.value = profile.last_name || '';
    profileElements.email.value = profile.email || '';
    profileElements.phone.value = profile.phone || '';
    profileElements.dob.value = profile.dob || '';
    profileElements.gender.value = profile.gender || '';
    profileElements.address.value = profile.address || '';
}

function setEditing(editing) {
    profileState.editing = editing;
    const disabled = !editing;

    [
        profileElements.firstName,
        profileElements.lastName,
        profileElements.email,
        profileElements.phone,
        profileElements.dob,
        profileElements.gender,
        profileElements.address,
    ].forEach((input) => {
        input.disabled = disabled;
    });

    profileElements.actionGroup.classList.toggle('d-none', !editing);
    profileElements.editButton.classList.toggle('d-none', editing);
}

function showContent() {
    profileElements.loadingState.classList.add('d-none');
    profileElements.errorState.classList.add('d-none');
    profileElements.content.classList.remove('d-none');
}

function showLoading() {
    profileElements.errorState.classList.add('d-none');
    profileElements.content.classList.add('d-none');
    profileElements.loadingState.classList.remove('d-none');
}

function showError() {
    profileElements.loadingState.classList.add('d-none');
    profileElements.content.classList.add('d-none');
    profileElements.errorState.classList.remove('d-none');
}

async function fetchProfile() {
    const token = getStoredToken();
    if (!token) {
        clearAuthAndRedirect();
        return;
    }

    showLoading();

    try {
        const profile = await window.mediaiApi.request('/auth/profile', {
            method: 'GET',
        });
        profileState.profile = normalizeProfile(profile);
        profileState.loaded = true;
        renderProfile(profileState.profile);
        setEditing(false);
        showContent();
    } catch (error) {
        if (error.status === 401) {
            clearAuthAndRedirect();
            return;
        }

        console.error('[profile] Failed to load profile:', error);
        showNotification('Failed to load profile', 'danger');
        showError();
    }
}

async function saveProfile(event) {
    event.preventDefault();
    if (!profileState.profile) {
        return;
    }

    const saveButton = profileElements.saveButton;
    setLoading(saveButton, true);

    const payload = {
        name: `${profileElements.firstName.value.trim()} ${profileElements.lastName.value.trim()}`.trim(),
        firstName: profileElements.firstName.value.trim(),
        lastName: profileElements.lastName.value.trim(),
        email: profileElements.email.value.trim(),
        phone: profileElements.phone.value.trim(),
        gender: profileElements.gender.value,
        dob: profileElements.dob.value || null,
        address: profileElements.address.value.trim(),
    };

    try {
        const result = await window.mediaiApi.request('/auth/profile', {
            method: 'PUT',
            body: JSON.stringify(payload),
        });

        profileState.profile = normalizeProfile(result.profile || profileState.profile);
        renderProfile(profileState.profile);
        setEditing(false);
        showNotification(result.message || 'Profile updated successfully', 'success');
    } catch (error) {
        if (error.status === 401) {
            clearAuthAndRedirect();
            return;
        }

        console.error('[profile] Update failed:', error);
        showNotification('Profile update failed', 'danger');
    } finally {
        setLoading(saveButton, false);
    }
}

async function uploadProfilePhoto(file) {
    if (!file) {
        return;
    }

    if (!['image/jpeg', 'image/png'].includes(file.type)) {
        showNotification('Only JPG, JPEG, and PNG images are allowed', 'danger');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const uploadButton = profileElements.uploadButton;
    setLoading(uploadButton, true);

    try {
        const result = await window.mediaiApi.request('/auth/profile/upload-photo', {
            method: 'POST',
            body: formData,
        });

        profileState.profile = normalizeProfile(result.profile || {
            ...profileState.profile,
            profile_image: result.profile_image || profileState.profile.profile_image,
        });
        renderProfile(profileState.profile);
        showNotification(result.message || 'Profile photo uploaded successfully', 'success');
    } catch (error) {
        if (error.status === 401) {
            clearAuthAndRedirect();
            return;
        }

        console.error('[profile] Photo upload failed:', error);
        showNotification(error.message || 'Profile photo upload failed', 'danger');
    } finally {
        setLoading(uploadButton, false);
        profileElements.photoInput.value = '';
    }
}

function bindProfileEvents() {
    profileElements.editButton.addEventListener('click', () => {
        if (!profileState.profile) {
            return;
        }
        setEditing(true);
    });

    profileElements.cancelButton.addEventListener('click', () => {
        if (!profileState.profile) {
            return;
        }
        renderProfile(profileState.profile);
        setEditing(false);
    });

    profileElements.form.addEventListener('submit', saveProfile);

    profileElements.uploadButton.addEventListener('click', () => {
        profileElements.photoInput.click();
    });

    profileElements.photoInput.addEventListener('change', () => {
        uploadProfilePhoto(profileElements.photoInput.files?.[0]);
    });

    profileElements.retryButton.addEventListener('click', fetchProfile);
}

document.addEventListener('DOMContentLoaded', () => {
    if (!getStoredToken()) {
        clearAuthAndRedirect();
        return;
    }

    bindProfileEvents();
    fetchProfile();
});
