/* Nicholas Hu — personal site interactions
   - hero canvas: scrolling logic-analyzer traces
   - scroll progress, scrollspy, header state
   - staggered reveal animations + stat counters
   - generated shmoo plot for the featured project card */

document.addEventListener('DOMContentLoaded', () => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ---------- Mobile nav ---------- */
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('nav-menu');

    const closeMenu = () => {
        hamburger.classList.remove('active');
        navMenu.classList.remove('active');
        hamburger.setAttribute('aria-expanded', 'false');
    };

    hamburger.addEventListener('click', () => {
        const open = navMenu.classList.toggle('active');
        hamburger.classList.toggle('active', open);
        hamburger.setAttribute('aria-expanded', String(open));
    });

    navMenu.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });
    document.addEventListener('click', e => {
        if (navMenu.classList.contains('active') &&
            !navMenu.contains(e.target) && !hamburger.contains(e.target)) closeMenu();
    });

    /* ---------- Header state + scroll progress ---------- */
    const header = document.querySelector('.header');
    const progress = document.querySelector('.scroll-progress');

    const onScroll = () => {
        header.classList.toggle('scrolled', window.scrollY > 40);
        const max = document.documentElement.scrollHeight - window.innerHeight;
        progress.style.transform = `scaleX(${max > 0 ? window.scrollY / max : 0})`;
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    /* ---------- Scrollspy ---------- */
    const sections = document.querySelectorAll('main section[id]');
    const navLinks = document.querySelectorAll('.nav-link');

    const spy = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            navLinks.forEach(l =>
                l.classList.toggle('active', l.getAttribute('href') === `#${entry.target.id}`));
        });
    }, { rootMargin: '-45% 0px -50% 0px' });
    sections.forEach(s => spy.observe(s));

    /* ---------- Staggered reveal animations ---------- */
    const revealEls = document.querySelectorAll('.reveal');

    // Stagger within each parent container so grids cascade.
    const batches = new Map();
    revealEls.forEach(el => {
        const key = el.parentElement;
        const i = batches.get(key) || 0;
        el.style.setProperty('--reveal-delay', `${Math.min(i * 0.09, 0.45)}s`);
        batches.set(key, i + 1);
    });

    const revealObserver = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                obs.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -36px 0px' });
    revealEls.forEach(el => revealObserver.observe(el));

    /* ---------- Stat counters ---------- */
    const counters = document.querySelectorAll('.count');
    const fmt = n => n.toLocaleString('en-US');

    const runCounter = el => {
        const target = parseInt(el.dataset.target, 10);
        if (reducedMotion) { el.textContent = fmt(target); return; }
        const dur = 1300;
        const t0 = performance.now();
        const tick = now => {
            const p = Math.min((now - t0) / dur, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            el.textContent = fmt(Math.round(target * eased));
            if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    };

    const counterObserver = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                runCounter(entry.target);
                obs.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    counters.forEach(c => counterObserver.observe(c));

    /* ---------- Shmoo plot (featured card) ---------- */
    const shmooGroup = document.querySelector('.shmoo-grid');
    if (shmooGroup) {
        const COLS = 12, ROWS = 8, CW = 23, CH = 19, GAP = 2.5;
        // Deterministic jitter so the pass/fail boundary looks organic.
        const jitter = (c, r) => {
            const x = Math.sin(c * 12.9898 + r * 78.233) * 43758.5453;
            return (x - Math.floor(x)) * 0.1 - 0.05;
        };
        const svgNS = 'http://www.w3.org/2000/svg';
        for (let r = 0; r < ROWS; r++) {
            for (let c = 0; c < COLS; c++) {
                // Higher frequency (right) fails first at lower VDD (bottom rows).
                const stress = c / (COLS - 1) - (1 - r / (ROWS - 1)) * 0.55;
                const v = stress + jitter(c, r);
                const cls = v > 0.5 ? 'fail' : v > 0.38 ? 'marginal' : 'pass';
                const rect = document.createElementNS(svgNS, 'rect');
                rect.setAttribute('x', c * (CW + GAP));
                rect.setAttribute('y', r * (CH + GAP));
                rect.setAttribute('width', CW);
                rect.setAttribute('height', CH);
                rect.setAttribute('class', `shmoo-cell ${cls}`);
                shmooGroup.appendChild(rect);
            }
        }
    }

    /* ---------- Hero canvas: logic-analyzer traces ---------- */
    const canvas = document.getElementById('wave-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let W = 0, H = 0, dpr = 1;
    let channels = [];
    let rafId = null;
    let heroVisible = true;

    const CHANNEL_STYLES = [
        { color: 'rgba(45, 212, 191, 0.32)', width: 1.4 },   // ch1 teal
        { color: 'rgba(251, 191, 36, 0.22)', width: 1.3 },   // ch2 amber
        { color: 'rgba(148, 163, 184, 0.16)', width: 1.2 },  // ch3 slate
        { color: 'rgba(45, 212, 191, 0.14)', width: 1.2 },   // ch4 faint teal
    ];

    const makeBits = n => Array.from({ length: n }, () => Math.random() > 0.5);

    const setup = () => {
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        W = canvas.offsetWidth;
        H = canvas.offsetHeight;
        canvas.width = W * dpr;
        canvas.height = H * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        const count = CHANNEL_STYLES.length;
        channels = CHANNEL_STYLES.map((style, i) => {
            const period = 46 + i * 22;                       // px per bit
            return {
                ...style,
                y: H * (0.18 + (i / (count - 1)) * 0.64),
                amp: 14 + i * 3,
                period,
                speed: 0.22 + i * 0.1,                        // px per frame
                offset: Math.random() * period,
                bits: makeBits(Math.ceil(W / period) + 3),
            };
        });
    };

    const drawChannel = ch => {
        ctx.strokeStyle = ch.color;
        ctx.lineWidth = ch.width;
        ctx.beginPath();
        let x = -ch.offset;
        let prev = null;
        for (let i = 0; i < ch.bits.length && x < W + ch.period; i++) {
            const y = ch.y + (ch.bits[i] ? -ch.amp : ch.amp);
            if (prev === null) {
                ctx.moveTo(x, y);
            } else if (prev !== y) {
                ctx.lineTo(x, prev);
                ctx.lineTo(x, y);
            }
            ctx.lineTo(x + ch.period, y);
            prev = y;
            x += ch.period;
        }
        ctx.stroke();
    };

    const step = () => {
        ctx.clearRect(0, 0, W, H);
        channels.forEach(ch => {
            ch.offset += ch.speed;
            if (ch.offset >= ch.period) {
                ch.offset -= ch.period;
                ch.bits.shift();
                ch.bits.push(Math.random() > 0.5);
            }
            drawChannel(ch);
        });
        if (!reducedMotion && heroVisible) rafId = requestAnimationFrame(step);
    };

    const start = () => {
        if (rafId === null) rafId = requestAnimationFrame(step);
    };
    const stop = () => {
        if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
    };

    setup();
    if (reducedMotion) {
        // Static single frame.
        channels.forEach(drawChannel);
    } else {
        const heroObserver = new IntersectionObserver(entries => {
            heroVisible = entries[0].isIntersecting;
            if (heroVisible) start(); else stop();
        }, { threshold: 0.05 });
        heroObserver.observe(canvas.parentElement);
        start();
    }

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            stop();
            setup();
            if (reducedMotion) channels.forEach(drawChannel);
            else if (heroVisible) start();
        }, 150);
    });
});
