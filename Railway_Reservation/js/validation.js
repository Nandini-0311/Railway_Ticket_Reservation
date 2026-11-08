/**
 * Railway Ticket Reservation System
 * File: js/validation.js
 * Purpose: Client-side validation, session state management (localStorage),
 *          and standardized fetch API communications.
 */

// ==============================================================
// 1. SESSION MANAGEMENT
// ==============================================================
const Session = {
    getUser() {
        try {
            return JSON.parse(localStorage.getItem('railway_user') || 'null');
        } catch (e) {
            return null;
        }
    },
    getUserToken() {
        return localStorage.getItem('railway_user_token');
    },
    setUser(user, token) {
        localStorage.setItem('railway_user', JSON.stringify(user));
        localStorage.setItem('railway_user_token', token);
    },
    clearUser() {
        localStorage.removeItem('railway_user');
        localStorage.removeItem('railway_user_token');
    },
    getAdmin() {
        try {
            return JSON.parse(localStorage.getItem('railway_admin') || 'null');
        } catch (e) {
            return null;
        }
    },
    getAdminToken() {
        return localStorage.getItem('railway_admin_token');
    },
    setAdmin(admin, token) {
        localStorage.setItem('railway_admin', JSON.stringify(admin));
        localStorage.setItem('railway_admin_token', token);
    },
    clearAdmin() {
        localStorage.removeItem('railway_admin');
        localStorage.removeItem('railway_admin_token');
    }
};

// ==============================================================
// 2. HTTP FETCH API WRAPPER
// ==============================================================
const API = {
    async request(url, options = {}) {
        options.headers = options.headers || {};
        options.headers['Content-Type'] = 'application/json';

        // Check user or admin token
        const userToken = Session.getUserToken();
        const adminToken = Session.getAdminToken();
        const activeToken = adminToken || userToken;

        if (activeToken) {
            options.headers['X-Session-Token'] = activeToken;
        }

        try {
            const resp = await fetch(url, options);
            const data = await resp.json();
            return data;
        } catch (err) {
            console.error('[API Fetch Error]', err);
            return { success: false, error: 'Network error or server unreachable.' };
        }
    },

    get(url) {
        return this.request(url, { method: 'GET' });
    },

    post(url, body) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    }
};

// ==============================================================
// 3. INPUT VALIDATION FUNCTIONS
// ==============================================================
const Validator = {
    isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(String(email).toLowerCase());
    },

    isValidPhone(phone) {
        const clean = String(phone).replace(/\D/g, '');
        return clean.length === 10;
    },

    isValidPNR(pnr) {
        const clean = String(pnr).trim();
        return clean.length === 10 && /^\d+$/.test(clean);
    },

    isFutureDate(dateStr) {
        const target = new Date(dateStr);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return target >= today;
    }
};

// ==============================================================
// 4. UI HELPERS
// ==============================================================
function showAlert(message, type = 'danger', containerId = 'alert-box') {
    const el = document.getElementById(containerId);
    if (!el) return;

    const bgClass = type === 'success' ? '#ecfdf5' : '#fef2f2';
    const borderClass = type === 'success' ? '#10b981' : '#ef4444';
    const textClass = type === 'success' ? '#065f46' : '#991b1b';

    el.innerHTML = `
        <div style="background:${bgClass}; border: 1.5px solid ${borderClass}; color: ${textClass}; padding: 0.85rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-weight: 500;">
            ${message}
        </div>
    `;
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function clearAlert(containerId = 'alert-box') {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = '';
}

// Populate station dropdown selects
async function populateStationDropdowns(sourceSelectId = 'source_station', destSelectId = 'dest_station', selectedSrc = null, selectedDst = null) {
    const data = await API.get('/api/stations');
    if (!data.success) return;

    const srcEl = document.getElementById(sourceSelectId);
    const dstEl = document.getElementById(destSelectId);

    if (srcEl) {
        srcEl.innerHTML = '<option value="">-- Select Source Station --</option>';
        data.stations.forEach(s => {
            const isSelected = selectedSrc && (selectedSrc == s.station_id || selectedSrc == s.station_code) ? 'selected' : '';
            srcEl.innerHTML += `<option value="${s.station_id}" ${isSelected}>${s.station_name} (${s.station_code})</option>`;
        });
    }

    if (dstEl) {
        dstEl.innerHTML = '<option value="">-- Select Destination Station --</option>';
        data.stations.forEach(s => {
            const isSelected = selectedDst && (selectedDst == s.station_id || selectedDst == s.station_code) ? 'selected' : '';
            dstEl.innerHTML += `<option value="${s.station_id}" ${isSelected}>${s.station_name} (${s.station_code})</option>`;
        });
    }
}

// Update Top Navigation Bar according to auth state
function updateNavbar() {
    const navLinks = document.getElementById('navbar-auth-links');
    if (!navLinks) return;

    const user = Session.getUser();
    const admin = Session.getAdmin();

    if (admin) {
        navLinks.innerHTML = `
            <a href="/admin_dashboard.html" class="active">Admin Dashboard (${admin.username})</a>
            <a href="javascript:void(0)" onclick="logoutAdmin()" class="btn-nav-accent">Logout</a>
        `;
    } else if (user) {
        navLinks.innerHTML = `
            <a href="/search_train.html">Book Ticket</a>
            <a href="/pnr_status.html">PNR Status</a>
            <a href="/user_dashboard.html">Dashboard</a>
            <a href="/booking_history.html">My Trips</a>
            <a href="javascript:void(0)" onclick="logoutUser()" class="btn-nav-accent">Logout (${user.full_name.split(' ')[0]})</a>
        `;
    } else {
        navLinks.innerHTML = `
            <a href="/search_train.html">Search Trains</a>
            <a href="/pnr_status.html">PNR Enquiry</a>
            <a href="/login.html">Login</a>
            <a href="/register.html" class="btn-nav-accent">Register</a>
        `;
    }
}

async function logoutUser() {
    await API.post('/api/logout', {});
    Session.clearUser();
    window.location.href = '/login.html';
}

async function logoutAdmin() {
    await API.post('/api/logout', {});
    Session.clearAdmin();
    window.location.href = '/admin_login.html';
}

// Execute on DOM load
document.addEventListener('DOMContentLoaded', () => {
    updateNavbar();
});
