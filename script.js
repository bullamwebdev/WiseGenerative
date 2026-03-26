/**
 * Wise Generative v3 - JavaScript
 * Following Research-Backed Design Framework
 * 
 * Skills Applied:
 * 7. Micro-Interactions (functional, <300ms)
 * 8. Performance (Core Web Vitals optimized)
 * 9. Accessibility (WCAG 2.2 AA, keyboard nav)
 */

(function() {
    'use strict';
    
    // =========================================
    // MOBILE MENU (Accessible)
    // =========================================
    
    const navToggle = document.querySelector('.nav__toggle');
    const navLinks = document.querySelector('.nav__links');
    
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            const isOpen = navToggle.getAttribute('aria-expanded') === 'true';
            navToggle.setAttribute('aria-expanded', !isOpen);
            navLinks.setAttribute('data-open', !isOpen);
        });
        
        // Close menu on link click
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navToggle.setAttribute('aria-expanded', 'false');
                navLinks.setAttribute('data-open', 'false');
            });
        });
        
        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && navLinks.getAttribute('data-open') === 'true') {
                navToggle.setAttribute('aria-expanded', 'false');
                navLinks.setAttribute('data-open', 'false');
                navToggle.focus();
            }
        });
    }
    
    // =========================================
    // SMOOTH SCROLL (with nav offset)
    // =========================================
    
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            
            if (target) {
                const navHeight = document.querySelector('.header')?.offsetHeight || 80;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
                
                // Update focus for accessibility
                target.setAttribute('tabindex', '-1');
                target.focus({ preventScroll: true });
            }
        });
    });
    
    // =========================================
    // HEADER SCROLL BEHAVIOR
    // =========================================
    
    const header = document.querySelector('.header');
    let lastScrollY = 0;
    let ticking = false;
    
    function updateHeader() {
        const scrollY = window.pageYOffset;
        
        if (scrollY > 100) {
            header.style.background = 'rgba(8, 8, 12, 0.95)';
        } else {
            header.style.background = 'rgba(8, 8, 12, 0.85)';
        }
        
        lastScrollY = scrollY;
        ticking = false;
    }
    
    window.addEventListener('scroll', () => {
        if (!ticking) {
            requestAnimationFrame(updateHeader);
            ticking = true;
        }
    }, { passive: true });
    
    // =========================================
    // INTERSECTION OBSERVER (Animations)
    // =========================================
    
    const animateOnScroll = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                // Staggered animation
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, index * 100);
                
                // Unobserve after animation
                animateOnScroll.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });
    
    // Elements to animate
    const animateElements = document.querySelectorAll(
        '.service-card, .step, .stat__value, .about__grid, .cta__content'
    );
    
    animateElements.forEach(el => el.classList.add('animate-in'));
    animateElements.forEach(el => animateOnScroll.observe(el));
    
    // =========================================
    // STATS COUNTER (Skill 7: Functional Animation)
    // =========================================
    
    const statsSection = document.querySelector('.stats');
    const counters = document.querySelectorAll('.stat__number');
    let statsAnimated = false;
    
    function animateCounters() {
        if (statsAnimated) return;
        statsAnimated = true;
        
        counters.forEach(counter => {
            const target = parseInt(counter.getAttribute('data-target'), 10);
            const duration = 2000; // 2 seconds
            const startTime = performance.now();
            
            function updateCounter(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Ease out cubic
                const easeOut = 1 - Math.pow(1 - progress, 3);
                const current = Math.floor(target * easeOut);
                
                counter.textContent = current;
                
                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = target;
                }
            }
            
            requestAnimationFrame(updateCounter);
        });
    }
    
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                statsObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    
    if (statsSection) {
        statsObserver.observe(statsSection);
    }
    
    // =========================================
    // NEURAL NETWORK PARALLAX (Reduced Motion)
    // =========================================
    
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const neuralElement = document.querySelector('.neural');
    
    if (neuralElement && !prefersReducedMotion.matches) {
        document.addEventListener('mousemove', (e) => {
            const x = (window.innerWidth / 2 - e.clientX) / 40;
            const y = (window.innerHeight / 2 - e.clientY) / 40;
            
            neuralElement.style.transform = `translate(${x}px, ${y}px)`;
        });
    }
    
    // =========================================
    // FOCUS MANAGEMENT (Accessibility)
    // =========================================
    
    // Add visible focus indicator for keyboard users
    document.body.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            document.body.classList.add('keyboard-nav');
        }
    });
    
    document.body.addEventListener('mousedown', () => {
        document.body.classList.remove('keyboard-nav');
    });
    
    // =========================================
    // PERFORMANCE: Lazy load images (if any)
    // =========================================
    
    if ('IntersectionObserver' in window) {
        const lazyImages = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        }, { rootMargin: '50px' });
        
        lazyImages.forEach(img => imageObserver.observe(img));
    }
    
    // =========================================
    // ANALYTICS HOOKS (Optional)
    // =========================================
    
    const whatsappLinks = document.querySelectorAll('a[href*="wa.me"]');
    
    whatsappLinks.forEach(link => {
        link.addEventListener('click', () => {
            // Track WhatsApp CTA clicks
            if (typeof gtag === 'function') {
                gtag('event', 'click', {
                    'event_category': 'CTA',
                    'event_label': 'WhatsApp'
                });
            }
            
            // Console log for debugging
            console.log('📊 WhatsApp CTA clicked:', link.href);
        });
    });
    
    // =========================================
    // CONSOLE EASTER EGG
    // =========================================
    
    console.log('%c✨ Wise Generative', 'font-size: 24px; font-weight: bold; color: #00d4aa;');
    console.log('%cSolutions IA Innovantes', 'font-size: 14px; color: #a0a0b0;');
    console.log('%c📱 Contact: wa.me/33754039519', 'font-size: 12px; color: #25d366;');
    console.log('%c🎨 Built with research-backed design principles', 'font-size: 11px; color: #7c3aed;');
    
})();