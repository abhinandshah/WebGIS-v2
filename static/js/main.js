// Main JavaScript for Palika GIS

// Sidebar toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('toggleSidebar');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            
            // Adjust main content margin when sidebar is collapsed
            if (sidebar.classList.contains('collapsed')) {
                mainContent.style.marginLeft = '0';
            } else {
                mainContent.style.marginLeft = '260px';
            }
        });
    }
    
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(flash => {
        setTimeout(() => {
            flash.style.transition = 'opacity 0.3s';
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 300);
        }, 5000);
    });
    
    // Language toggle (placeholder functionality)
    const langButtons = document.querySelectorAll('.lang-btn');
    langButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            langButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // In a real implementation, this would change the language
            console.log('Language changed to:', this.textContent);
        });
    });
    
    // Highlight active navigation item
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.style.background = 'var(--bg-light)';
            item.style.borderLeftColor = 'var(--primary)';
        }
    });
    
    // Mobile responsive menu
    const mediaQuery = window.matchMedia('(max-width: 768px)');
    
    function handleMobileMenu(e) {
        if (e.matches) {
            // Mobile view
            if (sidebar) {
                sidebar.classList.add('collapsed');
            }
            if (mainContent) {
                mainContent.style.marginLeft = '0';
            }
        } else {
            // Desktop view
            if (sidebar) {
                sidebar.classList.remove('collapsed');
            }
            if (mainContent) {
                mainContent.style.marginLeft = '260px';
            }
        }
    }
    
    // Initial check
    handleMobileMenu(mediaQuery);
    
    // Listen for viewport changes
    mediaQuery.addListener(handleMobileMenu);
});

// Utility function to format dates
function formatDate(date) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(date).toLocaleDateString('en-US', options);
}

// Utility function to format numbers
function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}

// Export functions for use in templates
window.PalikaGIS = {
    formatDate,
    formatNumber
};