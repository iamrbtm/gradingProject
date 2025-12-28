// Theme management functionality
class ThemeManager {
    constructor() {
        this.themeToggle = document.getElementById('theme-toggle');
        this.mobileThemeToggle = document.getElementById('mobile-theme-toggle');
        this.themeIcon = document.getElementById('theme-icon');
        this.mobileThemeIcon = document.getElementById('mobile-theme-icon');
        this.init();
    }

    init() {
        // Check current theme that was already applied by inline script
        const currentTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
        
        // Update icons to match current theme without changing the theme itself
        this.updateIcons(currentTheme);

        // Listen for system theme changes
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                // Only auto-switch if user hasn't manually set a preference
                if (!localStorage.getItem('theme')) {
                    const systemTheme = e.matches ? 'dark' : 'light';
                    this.setTheme(systemTheme, false); // Don't save to localStorage
                }
            });
        }

        // Add event listeners to theme toggle buttons
        if (this.themeToggle) {
            this.themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
        
        if (this.mobileThemeToggle) {
            this.mobileThemeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
    }

    getSystemPreference() {
        // Check if the browser supports prefers-color-scheme
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    updateIcons(theme) {
        if (theme === 'dark') {
            // Update both desktop and mobile icons for dark mode
            if (this.themeIcon) {
                this.themeIcon.classList.remove('fa-moon');
                this.themeIcon.classList.add('fa-sun');
            }
            if (this.mobileThemeIcon) {
                this.mobileThemeIcon.classList.remove('fa-moon');
                this.mobileThemeIcon.classList.add('fa-sun');
            }
        } else {
            // Update both desktop and mobile icons for light mode
            if (this.themeIcon) {
                this.themeIcon.classList.remove('fa-sun');
                this.themeIcon.classList.add('fa-moon');
            }
            if (this.mobileThemeIcon) {
                this.mobileThemeIcon.classList.remove('fa-sun');
                this.mobileThemeIcon.classList.add('fa-moon');
            }
        }
    }

    setTheme(theme, saveToStorage = true) {
        const html = document.documentElement;
        
        if (theme === 'dark') {
            html.classList.add('dark');
        } else {
            html.classList.remove('dark');
        }
        
        // Update icons
        this.updateIcons(theme);
        
        // Save theme preference only if requested
        if (saveToStorage) {
            localStorage.setItem('theme', theme);
        }
    }

    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.classList.contains('dark') ? 'dark' : 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }

    getCurrentTheme() {
        return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    }
}

// Mobile menu management
class MobileMenuManager {
    constructor() {
        this.menuButton = document.getElementById('mobile-menu-button');
        this.closeButton = document.getElementById('mobile-menu-close');
        this.menu = document.getElementById('mobile-menu');
        this.overlay = document.getElementById('mobile-overlay');
        this.init();
    }

    init() {
        if (this.menuButton) {
            this.menuButton.addEventListener('click', () => {
                this.openMenu();
            });
        }

        if (this.closeButton) {
            this.closeButton.addEventListener('click', () => {
                this.closeMenu();
            });
        }

        if (this.overlay) {
            this.overlay.addEventListener('click', () => {
                this.closeMenu();
            });
        }

        // Close menu when clicking on menu items
        if (this.menu) {
            const menuLinks = this.menu.querySelectorAll('a');
            menuLinks.forEach(link => {
                link.addEventListener('click', () => {
                    this.closeMenu();
                });
            });
        }

        // Close menu on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeMenu();
            }
        });
    }

    openMenu() {
        if (this.menu && this.overlay) {
            this.menu.classList.add('open');
            this.overlay.classList.add('open');
            document.body.style.overflow = 'hidden';
        }
    }

    closeMenu() {
        if (this.menu && this.overlay) {
            this.menu.classList.remove('open');
            this.overlay.classList.remove('open');
            document.body.style.overflow = '';
        }
    }
}

// Form validation utility
class FormValidator {
    constructor() {
        this.init();
    }

    init() {
        // Add validation to all forms with the 'validate' class
        const forms = document.querySelectorAll('form.validate');
        forms.forEach(form => {
            this.addFormValidation(form);
        });

        // Add real-time validation to inputs
        const inputs = document.querySelectorAll('input[required], input[data-validate]');
        inputs.forEach(input => {
            this.addInputValidation(input);
        });
    }

    addFormValidation(form) {
        form.addEventListener('submit', (e) => {
            if (!this.validateForm(form)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }

    addInputValidation(input) {
        input.addEventListener('blur', () => {
            this.validateInput(input);
        });

        input.addEventListener('input', () => {
            // Clear validation state on input
            this.clearValidationState(input);
        });
    }

    validateForm(form) {
        let isValid = true;
        const inputs = form.querySelectorAll('input[required], input[data-validate]');
        
        inputs.forEach(input => {
            if (!this.validateInput(input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateInput(input) {
        const value = input.value.trim();
        const type = input.type;
        const rules = input.dataset.validate;
        let isValid = true;
        let errorMessage = '';

        // Clear previous validation state
        this.clearValidationState(input);

        // Required field validation
        if (input.hasAttribute('required') && !value) {
            isValid = false;
            errorMessage = 'This field is required.';
        }

        // Email validation
        if (type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = 'Please enter a valid email address.';
            }
        }

        // Password validation
        if (type === 'password' && value) {
            if (value.length < 6) {
                isValid = false;
                errorMessage = 'Password must be at least 6 characters long.';
            }
        }

        // Custom validation rules
        if (rules && value) {
            switch (rules) {
                case 'username':
                    if (value.length < 3) {
                        isValid = false;
                        errorMessage = 'Username must be at least 3 characters long.';
                    }
                    break;
                case 'grade':
                    const grade = parseFloat(value);
                    if (isNaN(grade) || grade < 0 || grade > 100) {
                        isValid = false;
                        errorMessage = 'Grade must be a number between 0 and 100.';
                    }
                    break;
                case 'credits':
                    const credits = parseFloat(value);
                    if (isNaN(credits) || credits <= 0) {
                        isValid = false;
                        errorMessage = 'Credits must be a positive number.';
                    }
                    break;
            }
        }

        // Apply validation state
        if (isValid) {
            input.classList.add('valid');
            input.classList.remove('invalid');
        } else {
            input.classList.add('invalid');
            input.classList.remove('valid');
            this.showErrorMessage(input, errorMessage);
        }

        return isValid;
    }

    clearValidationState(input) {
        input.classList.remove('valid', 'invalid');
        this.removeErrorMessage(input);
    }

    showErrorMessage(input, message) {
        this.removeErrorMessage(input);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        input.parentNode.insertBefore(errorDiv, input.nextSibling);
    }

    removeErrorMessage(input) {
        const errorMessage = input.parentNode.querySelector('.error-message');
        if (errorMessage) {
            errorMessage.remove();
        }
    }
}

// Loading utility
class LoadingManager {
    static show(button) {
        if (button) {
            const originalText = button.innerHTML;
            button.dataset.originalText = originalText;
            button.innerHTML = '<div class="spinner"></div> Loading...';
            button.disabled = true;
        }
    }

    static hide(button) {
        if (button && button.dataset.originalText) {
            button.innerHTML = button.dataset.originalText;
            button.disabled = false;
            delete button.dataset.originalText;
        }
    }

    static showFormLoading(form) {
        const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitButton) {
            this.show(submitButton);
        }
    }

    static hideFormLoading(form) {
        const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitButton) {
            this.hide(submitButton);
        }
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new ThemeManager();
    new MobileMenuManager();
    new FormValidator();

    // Add loading states to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            LoadingManager.showFormLoading(this);
        });
    });

    // Add smooth scrolling to anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});