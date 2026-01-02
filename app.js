(function () {
  function getPrefix() {
    const depth = Math.max(
      window.location.pathname.replace(/\/$/, '').split('/').filter(Boolean)
        .length - 1,
      0
    );
    return '../'.repeat(depth);
  }

  function loadShell() {
    const containers = [
      { id: 'site-header', file: 'header.html' },
      { id: 'site-footer', file: 'footer.html' },
    ];

    const prefix = getPrefix();

    containers.forEach(({ id, file }) => {
      const slot = document.getElementById(id);
      if (!slot) return;
      fetch(prefix + file)
        .then((res) => res.text())
        .then((html) => {
          slot.innerHTML = html.replace(/{{PREFIX}}/g, prefix);
          const y = slot.querySelector('#y');
          if (y) y.textContent = new Date().getFullYear();
        })
        .catch((err) => console.error('Include failed:', file, err));
    });
  }

  function ensureFavicon() {
    const prefix = getPrefix();
    const existing = document.querySelector("link[rel~='icon']");
    if (existing) {
      existing.href = prefix + 'pounamu_twistfav.ico';
      return;
    }
    const link = document.createElement('link');
    link.rel = 'icon';
    link.href = prefix + 'pounamu_twistfav.ico';
    document.head.appendChild(link);
  }

  function initGallery() {
    const main = document.getElementById('mainProductImage');
    const thumbs = Array.from(document.querySelectorAll('.thumb'));
    if (!main || !thumbs.length) return;

    thumbs.forEach((btn) => {
      btn.addEventListener('click', () => {
        const src = btn.getAttribute('data-src');
        const alt = btn.getAttribute('data-alt');
        if (!src) return;
        if (main.src === src) {
          if (alt) main.alt = alt;
        } else {
          main.src = src;
          if (alt) main.alt = alt;
        }
        thumbs.forEach((t) => t.classList.remove('is-active'));
        btn.classList.add('is-active');
      });
    });
  }

  window.addEventListener('DOMContentLoaded', () => {
    loadShell();
    ensureFavicon();
    initGallery();
  });
})();
