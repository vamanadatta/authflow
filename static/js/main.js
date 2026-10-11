// ==========================================================================
// AuthFlow Client-Side Script
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initPasswordToggles();
    initPasswordStrength();
    initPasswordMatch();
    initAlertAutoDismiss();
});

/* --------------------------------------------------------------------------
   1. Theme Management (Dark / Light Mode)
   -------------------------------------------------------------------------- */
function initTheme() {
    const themeToggleBtn = document.getElementById('themeToggle');
    const savedTheme = localStorage.getItem('authflow-theme') || 'dark';

    document.documentElement.setAttribute('data-theme', savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('authflow-theme', newTheme);
        });
    }
}

/* --------------------------------------------------------------------------
   2. Show / Hide Password Toggles
   -------------------------------------------------------------------------- */
function initPasswordToggles() {
    const toggleButtons = document.querySelectorAll('.password-toggle-btn');

    toggleButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const wrapper = btn.closest('.input-wrapper');
            const input = wrapper ? wrapper.querySelector('.password-field') : null;
            if (!input) return;

            const icon = btn.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                icon.className = 'fa-regular fa-eye-slash';
            } else {
                input.type = 'password';
                icon.className = 'fa-regular fa-eye';
            }
        });
    });
}

/* --------------------------------------------------------------------------
   3. Real-time Password Strength Meter
   -------------------------------------------------------------------------- */
function initPasswordStrength() {
    const passwordInput = document.getElementById('password');
    const meterContainer = document.getElementById('passwordMeter');
    if (!passwordInput || !meterContainer) return;

    const bars = [
        document.getElementById('bar1'),
        document.getElementById('bar2'),
        document.getElementById('bar3'),
        document.getElementById('bar4')
    ];
    const meterText = document.getElementById('meterText');

    passwordInput.addEventListener('input', () => {
        const val = passwordInput.value;
        if (!val) {
            bars.forEach(bar => {
                bar.style.backgroundColor = '';
            });
            meterText.textContent = 'Password strength';
            meterText.style.color = '';
            return;
        }

        let score = 0;
        if (val.length >= 6) score++;
        if (val.length >= 10) score++;
        if (/[A-Z]/.test(val) && /[a-z]/.test(val)) score++;
        if (/[0-9]/.test(val) || /[^A-Za-z0-9]/.test(val)) score++;

        const levels = [
            { label: 'Too Weak', color: '#f43f5e' },
            { label: 'Weak', color: '#f97316' },
            { label: 'Medium', color: '#eab308' },
            { label: 'Strong', color: '#10b981' }
        ];

        const currentLevel = levels[score - 1] || levels[0];

        bars.forEach((bar, index) => {
            if (index < score) {
                bar.style.backgroundColor = currentLevel.color;
            } else {
                bar.style.backgroundColor = '';
            }
        });

        meterText.textContent = `Strength: ${currentLevel.label}`;
        meterText.style.color = currentLevel.color;
    });
}

/* --------------------------------------------------------------------------
   4. Password Confirmation Matcher
   -------------------------------------------------------------------------- */
function initPasswordMatch() {
    const passwordInput = document.getElementById('password');
    const confirmInput = document.getElementById('confirm_password');
    const indicator = document.getElementById('matchIndicator');

    if (!passwordInput || !confirmInput || !indicator) return;

    function checkMatch() {
        const pass = passwordInput.value;
        const confirm = confirmInput.value;

        if (!confirm) {
            indicator.textContent = '';
            indicator.className = 'match-indicator';
            return;
        }

        if (pass === confirm) {
            indicator.textContent = '✓ Passwords match';
            indicator.className = 'match-indicator match';
        } else {
            indicator.textContent = '✕ Passwords do not match';
            indicator.className = 'match-indicator mismatch';
        }
    }

    confirmInput.addEventListener('input', checkMatch);
    passwordInput.addEventListener('input', () => {
        if (confirmInput.value) checkMatch();
    });
}

/* --------------------------------------------------------------------------
   5. Auto-Dismiss Flash Alerts
   -------------------------------------------------------------------------- */
function initAlertAutoDismiss() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });
}

/* --------------------------------------------------------------------------
   6. Social Login Simulation
   -------------------------------------------------------------------------- */
function simulateSocialLogin(provider) {
    alert(`Connecting with ${provider}... This demo authenticates using the built-in SQLite user database.`);
}
