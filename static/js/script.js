document.addEventListener('DOMContentLoaded', function() {
    // Handle image errors
    document.querySelectorAll('img').forEach(img => {
        img.onerror = function() {
            this.style.display = 'none';
        };
    });
});