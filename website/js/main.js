document.addEventListener('DOMContentLoaded', () => {

    // ── Copy button ───────────────────────────────
    const copyBtn = document.querySelector('.copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            const text = copyBtn.getAttribute('data-copy');
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.textContent = 'Copied!';
                copyBtn.classList.add('copied');
                setTimeout(() => {
                    copyBtn.textContent = 'Copy';
                    copyBtn.classList.remove('copied');
                }, 2000);
            });
        });
    }

    // ── Scroll-in animation for daimon cards ─────
    const cards = document.querySelectorAll('.daimon-card');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, i) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, 0);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    cards.forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = `opacity 0.4s ease ${i * 0.08}s, transform 0.4s ease ${i * 0.08}s, border-color 0.25s, box-shadow 0.25s`;
        observer.observe(card);
    });

    // ── Active nav link on scroll ─────────────────
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');

    const sectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.id;
                navLinks.forEach(link => {
                    link.style.color = link.getAttribute('href') === `#${id}`
                        ? 'var(--text)' : '';
                });
            }
        });
    }, { rootMargin: '-30% 0px -60% 0px' });

    sections.forEach(s => sectionObserver.observe(s));
});
