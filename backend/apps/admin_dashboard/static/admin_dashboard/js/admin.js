document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh health indicators every 30s
    const healthEls = document.querySelectorAll('[data-health-url]');
    if (healthEls.length) {
        setInterval(() => {
            healthEls.forEach(el => {
                fetch(el.dataset.healthUrl).then(r => r.json()).then(d => {
                    el.innerHTML = '<span class="health-dot green"></span> Healthy';
                }).catch(() => {
                    el.innerHTML = '<span class="health-dot red"></span> Error';
                });
            });
        }, 30000);
    }

    // Modal toggle
    document.querySelectorAll('[data-modal-open]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById(btn.dataset.modalOpen).classList.add('open');
        });
    });
    document.querySelectorAll('[data-modal-close]').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.remove('open');
        });
    });
});
