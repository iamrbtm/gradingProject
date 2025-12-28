// Theme toggle and mobile menu functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const mobileThemeToggle = document.getElementById('mobile-theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const mobileThemeIcon = document.getElementById('mobile-theme-icon');
    const html = document.documentElement;
    
    // Mobile menu elements
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    const mobileMenuClose = document.getElementById('mobile-menu-close');
    const mobileOverlay = document.getElementById('mobile-overlay');
    
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    const systemTheme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    const currentTheme = savedTheme || systemTheme;
    
    // Apply current theme
    function applyTheme(theme) {
        if (theme === 'dark') {
            html.classList.add('dark');
            if (themeIcon) themeIcon.className = 'fas fa-sun';
            if (mobileThemeIcon) mobileThemeIcon.className = 'fas fa-sun mr-3';
        } else {
            html.classList.remove('dark');
            if (themeIcon) themeIcon.className = 'fas fa-moon';
            if (mobileThemeIcon) mobileThemeIcon.className = 'fas fa-moon mr-3';
        }
    }
    
    // Initialize theme
    applyTheme(currentTheme);
    
    // Toggle theme function
    function toggleTheme() {
        const isDark = html.classList.contains('dark');
        const newTheme = isDark ? 'light' : 'dark';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    }
    
    // Theme toggle event listeners
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    if (mobileThemeToggle) {
        mobileThemeToggle.addEventListener('click', toggleTheme);
    }
    
    // Mobile menu functionality
    function openMobileMenu() {
        if (mobileMenu && mobileOverlay) {
            mobileMenu.classList.add('open');
            mobileOverlay.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
        }
    }
    
    function closeMobileMenu() {
        if (mobileMenu && mobileOverlay) {
            mobileMenu.classList.remove('open');
            mobileOverlay.classList.add('hidden');
            document.body.style.overflow = ''; // Restore scrolling
        }
    }
    
    // Mobile menu event listeners
    if (mobileMenuButton) {
        mobileMenuButton.addEventListener('click', openMobileMenu);
    }
    
    if (mobileMenuClose) {
        mobileMenuClose.addEventListener('click', closeMobileMenu);
    }
    
    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', closeMobileMenu);
    }
    
    // Close mobile menu on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeMobileMenu();
        }
    });
    
    // Close mobile menu when clicking navigation links
    const mobileNavLinks = document.querySelectorAll('#mobile-menu a');
    mobileNavLinks.forEach(link => {
        link.addEventListener('click', closeMobileMenu);
    });
    
    // Handle window resize - close mobile menu if screen becomes large
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 768) { // md breakpoint
            closeMobileMenu();
        }
    });
});