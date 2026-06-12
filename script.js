/* Nicholas Hu — personal site interactions
   - light/dark theme toggle (persisted)
   - typewriter hero ("I'm a ...")
   - staggered card reveals */

document.addEventListener('DOMContentLoaded', () => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ---------- Theme toggle ---------- */
    const toggle = document.getElementById('theme-toggle');

    const applyToggleLabel = () => {
        const dark = document.documentElement.dataset.theme !== 'light';
        toggle.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
    };

    toggle.addEventListener('click', () => {
        const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
        document.documentElement.dataset.theme = next;
        try { localStorage.setItem('theme', next); } catch (e) { /* private mode */ }
        applyToggleLabel();
    });
    applyToggleLabel();

    /* ---------- Typewriter ---------- */
    const typed = document.getElementById('typed');
    const phrases = [
        'a silicon validator.',
        'a verification engineer.',
        'a hardware builder.',
        'an ECE senior @ Rice.',
    ];

    if (reducedMotion) {
        typed.textContent = phrases[0];
    } else {
        const TYPE_MS = 72;
        const DELETE_MS = 38;
        const HOLD_MS = 2100;
        const GAP_MS = 420;
        let phrase = 0;
        let len = 0;
        let deleting = false;

        const tick = () => {
            const current = phrases[phrase];
            len += deleting ? -1 : 1;
            typed.textContent = current.slice(0, len);

            let delay = deleting ? DELETE_MS : TYPE_MS;
            if (!deleting && len === current.length) {
                deleting = true;
                delay = HOLD_MS;
            } else if (deleting && len === 0) {
                deleting = false;
                phrase = (phrase + 1) % phrases.length;
                delay = GAP_MS;
            }
            setTimeout(tick, delay);
        };
        setTimeout(tick, 500);
    }

    /* ---------- Staggered card reveals ---------- */
    const revealEls = document.querySelectorAll('.reveal');

    const batches = new Map();
    revealEls.forEach(el => {
        const key = el.parentElement;
        const i = batches.get(key) || 0;
        el.style.setProperty('--reveal-delay', `${Math.min(i * 0.08, 0.32)}s`);
        batches.set(key, i + 1);
    });

    const revealObserver = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                obs.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -28px 0px' });
    revealEls.forEach(el => revealObserver.observe(el));
});
