document.addEventListener('DOMContentLoaded', () => {

    // Mobile navigation toggle (Hamburger menu)
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');

    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navMenu.classList.toggle('active');
    });

    // Close mobile menu when a link is clicked
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
        });
    });

    // Sticky header on scroll
    const header = document.querySelector('.header');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });

    // On-scroll fade-in animations for sections
    const sectionsToAnimate = document.querySelectorAll('.work-section, .about-section, .contact-section');

    const observerOptions = {
        root: null, // observes intersections relative to the viewport
        rootMargin: '0px',
        threshold: 0.1 // trigger when 10% of the element is visible
    };

    const sectionObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            // If the element is intersecting (visible), add the 'visible' class
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // Stop observing the element after it has become visible
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Add the 'fade-in' class to each section and start observing it
    sectionsToAnimate.forEach(section => {
        section.classList.add('fade-in');
        sectionObserver.observe(section);
    });

});

