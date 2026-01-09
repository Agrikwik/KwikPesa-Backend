function toggleAuth(mode) {
    const forms = ['login-form', 'register-form', 'otp-section', 'forgot-form', 'reset-section'];
    forms.forEach(id => document.getElementById(id).classList.add('hidden'));
    
    const subtitle = document.getElementById('auth-subtitle');
    
    if(mode === 'login') {
        document.getElementById('login-form').classList.remove('hidden');
        subtitle.innerText = "Welcome back, Merchant";
    } else if(mode === 'register') {
        document.getElementById('register-form').classList.remove('hidden');
        subtitle.innerText = "Join the KwachaPoint Network";
    } else if(mode === 'forgot') {
        document.getElementById('forgot-form').classList.remove('hidden');
        subtitle.innerText = "Recover Account";
    } else if(mode === 'reset') {
        document.getElementById('reset-section').classList.remove('hidden');
        subtitle.innerText = "Security Reset";
    } else if(mode === 'otp') {
        document.getElementById('otp-section').classList.remove('hidden');
        subtitle.innerText = "Verify Your Email";
    }
}

document.getElementById('login-form').onsubmit = async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    btn.innerText = "Checking...";
            
    const res = await fetch('/auth/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            email: document.getElementById('login-email').value,
            password: document.getElementById('login-password').value
        })
    });
            
    const data = await res.json();
    if(res.ok) {
        localStorage.setItem('kp_token', data.access_token);
        // Try to get redirect URL from server, else default to dashboard
        try {
            redirectRes = await fetch('/redirect');
            const redirectData = await redirectRes.json();
            window.location.href = redirectData.redirect_url || '/dashboard';
        } catch {
            window.location.href = '/dashboard';
        }
    } else {
        alert(data.detail);
        btn.innerText = "Sign In";
    }
};

        document.getElementById('register-form').onsubmit = async (e) => {
            e.preventDefault();
            const res = await fetch('/auth/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: document.getElementById('reg-email').value,
                    password: document.getElementById('reg-pass').value,
                    full_name: document.getElementById('reg-name').value,
                    personal_phone: document.getElementById('reg-phone').value,
                    business_name: document.getElementById('reg-biz').value
                })
            });
            if(res.ok) toggleAuth('otp');
            else alert("Error: " + (await res.json()).detail);
        };

        // --- FORGOT PASSWORD LOGIC ---
        document.getElementById('forgot-form').onsubmit = async (e) => {
            e.preventDefault();
            const email = document.getElementById('forgot-email-input').value;
            const res = await fetch('/auth/forgot-password', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email: email })
            });
            if(res.ok) {
                alert("Reset code sent!");
                toggleAuth('reset');
            } else alert("Error sending code.");
        };

        // --- RESET PASSWORD SUBMISSION ---
        async function submitNewPassword() {
            const email = document.getElementById('forgot-email-input').value; // Retreive from the forgot input
            const res = await fetch('/auth/reset-password', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: email,
                    otp_code: document.getElementById('reset-otp').value,
                    new_password: document.getElementById('reset-new-pass').value
                })
            });
            if(res.ok) {
                alert("Success! Password updated.");
                toggleAuth('login');
            } else alert("Verification failed.");
        }

        // --- VERIFY ACCOUNT LOGIC ---
async function verifyAccount() {
    const email = document.getElementById('reg-email').value;
    const code = document.getElementById('otp-code').value;
    const res = await fetch(`/auth/verify-otp?email=${email}&code=${code}`, { method: 'POST' });
    if(res.ok) {
        alert("Verified! You can now sign in.");
        toggleAuth('login');
    } else alert("Invalid code.");
};