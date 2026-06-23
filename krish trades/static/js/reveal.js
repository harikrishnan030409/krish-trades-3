/* ============================================================
   KRISH TRADES — Pro Animation Engine v3
   - IntersectionObserver scroll reveals with stagger
   - Custom cursor
   - Page progress bar
   - Hero particles
   - Back to top
   - Magnetic buttons
   - Number counter
   - Cart shake animation
   ============================================================ */
(function () {
    'use strict';

    var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ── Page progress bar ──────────────────────────────── */
    var bar = document.createElement('div');
    bar.id = 'page-progress';
    document.body.prepend(bar);
    window.addEventListener('scroll', function () {
        var scrolled = window.scrollY;
        var total    = document.documentElement.scrollHeight - window.innerHeight;
        bar.style.width = (total > 0 ? (scrolled / total) * 100 : 0) + '%';
    }, { passive: true });

    /* ── Custom cursor ──────────────────────────────────── */
    if (!reduced && window.matchMedia('(pointer:fine)').matches) {
        var dot  = document.createElement('div'); dot.className  = 'cursor-dot';
        var ring = document.createElement('div'); ring.className = 'cursor-ring';
        document.body.appendChild(dot);
        document.body.appendChild(ring);

        var mx = 0, my = 0, rx = 0, ry = 0;
        document.addEventListener('mousemove', function (e) {
            mx = e.clientX; my = e.clientY;
            dot.style.left = mx + 'px'; dot.style.top = my + 'px';
        });
        // ring follows with slight lag
        (function animRing() {
            rx += (mx - rx) * 0.14;
            ry += (my - ry) * 0.14;
            ring.style.left = rx + 'px'; ring.style.top = ry + 'px';
            requestAnimationFrame(animRing);
        })();

        document.querySelectorAll('a, button, .btn, .card, .category-chip, .payment-method-card').forEach(function (el) {
            el.addEventListener('mouseenter', function () { document.body.classList.add('hovering'); });
            el.addEventListener('mouseleave', function () { document.body.classList.remove('hovering'); });
        });
    }

    /* ── Hero particles ─────────────────────────────────── */
    var heroSection = document.querySelector('.hero-section');
    if (heroSection && !reduced) {
        var pContainer = document.createElement('div');
        pContainer.className = 'hero-particles';
        heroSection.appendChild(pContainer);
        for (var i = 0; i < 18; i++) {
            var p = document.createElement('div');
            p.className = 'hero-particle';
            var size = Math.random() * 5 + 3;
            var startX = Math.random() * 100;
            var duration = Math.random() * 12 + 8;
            var delay = Math.random() * 8;
            p.style.cssText =
                'width:' + size + 'px;' +
                'height:' + size + 'px;' +
                'left:' + startX + '%;' +
                'bottom:-10px;' +
                'opacity:' + (Math.random() * 0.4 + 0.1) + ';' +
                'animation-name:particle-float;' +
                'animation-duration:' + duration + 's;' +
                'animation-delay:' + delay + 's;';
            pContainer.appendChild(p);
        }
        // inject keyframe
        var style = document.createElement('style');
        style.textContent = '@keyframes particle-float {' +
            '0%   { transform: translateY(0) translateX(0) scale(1); opacity:0.3; }' +
            '25%  { transform: translateY(-30vh) translateX(20px); opacity:0.7; }' +
            '50%  { transform: translateY(-60vh) translateX(-15px) scale(1.2); opacity:0.5; }' +
            '75%  { transform: translateY(-80vh) translateX(10px); opacity:0.2; }' +
            '100% { transform: translateY(-110vh) translateX(0) scale(0.5); opacity:0; }' +
        '}';
        document.head.appendChild(style);
    }

    /* ── IntersectionObserver scroll reveals ─────────────── */
    var targets = document.querySelectorAll('.reveal-on-scroll');
    if (!targets.length) return;

    if (reduced || !('IntersectionObserver' in window)) {
        targets.forEach(function (el) { el.classList.add('is-visible'); });
    } else {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -30px 0px' });
        targets.forEach(function (el) { io.observe(el); });
    }

    /* ── Back to top button ─────────────────────────────── */
    var btt = document.createElement('button');
    btt.id = 'back-to-top';
    btt.innerHTML = '<i class="bi bi-chevron-up"></i>';
    btt.title = 'Back to top';
    document.body.appendChild(btt);
    window.addEventListener('scroll', function () {
        btt.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });
    btt.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    /* ── Magnetic button effect ─────────────────────────── */
    if (!reduced && window.matchMedia('(pointer:fine)').matches) {
        document.querySelectorAll('.btn-lg, .btn-add-cart').forEach(function (btn) {
            btn.addEventListener('mousemove', function (e) {
                var rect = btn.getBoundingClientRect();
                var dx = e.clientX - (rect.left + rect.width  / 2);
                var dy = e.clientY - (rect.top  + rect.height / 2);
                btn.style.transform = 'translateX(' + (dx * 0.12) + 'px) translateY(' + (dy * 0.12 - 2) + 'px)';
            });
            btn.addEventListener('mouseleave', function () {
                btn.style.transform = '';
            });
        });
    }

    /* ── Counter animation ──────────────────────────────── */
    document.querySelectorAll('[data-count-to]').forEach(function (el) {
        var target = parseInt(el.dataset.countTo, 10);
        if (isNaN(target)) return;
        var started = false;
        var ciob = new IntersectionObserver(function (entries) {
            if (entries[0].isIntersecting && !started) {
                started = true;
                var start = 0, duration = 1400, startTime = null;
                function step(ts) {
                    if (!startTime) startTime = ts;
                    var pct = Math.min((ts - startTime) / duration, 1);
                    // ease-out
                    var ease = 1 - Math.pow(1 - pct, 3);
                    el.textContent = Math.round(start + (target - start) * ease).toLocaleString();
                    if (pct < 1) requestAnimationFrame(step);
                }
                requestAnimationFrame(step);
                ciob.unobserve(el);
            }
        }, { threshold: 0.5 });
        ciob.observe(el);
    });

    /* ── Cart icon shake on add ─────────────────────────── */
    document.querySelectorAll('form[action*="cart/add"]').forEach(function (form) {
        form.addEventListener('submit', function () {
            var icon = document.querySelector('.cart-nav-link');
            if (!icon) return;
            icon.style.animation = 'none';
            requestAnimationFrame(function () {
                icon.style.animation = 'cart-shake 0.5s ease';
            });
        });
    });
    var shakeStyle = document.createElement('style');
    shakeStyle.textContent = '@keyframes cart-shake {' +
        '0%,100%{ transform:scale(1) rotate(0); }' +
        '20%    { transform:scale(1.3) rotate(-10deg); }' +
        '40%    { transform:scale(1.2) rotate(8deg); }' +
        '60%    { transform:scale(1.15) rotate(-6deg); }' +
        '80%    { transform:scale(1.05) rotate(4deg); }' +
    '}';
    document.head.appendChild(shakeStyle);

    /* ── Image lazy-load entrance ───────────────────────── */
    if ('IntersectionObserver' in window) {
        var imgObs = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    e.target.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                    e.target.style.opacity = '1';
                    e.target.style.transform = 'scale(1)';
                    imgObs.unobserve(e.target);
                }
            });
        }, { threshold: 0.1 });
        document.querySelectorAll('.card img, .product-detail-img').forEach(function (img) {
            img.style.opacity = '0';
            img.style.transform = 'scale(0.96)';
            imgObs.observe(img);
        });
    }

})();
