(function () {
  function getPrefix() {
    const depth = Math.max(
      window.location.pathname.replace(/\/$/, '').split('/').filter(Boolean)
        .length,
      0
    );
    return '../'.repeat(depth);
  }

  function loadHeader() {
    const slot = document.getElementById('site-header');
    if (!slot) return;

    const prefix = getPrefix();

    fetch(prefix + 'header.html')
      .then((res) => res.text())
      .then((html) => {
        slot.innerHTML = html.replace(/{{PREFIX}}/g, prefix);
      })
      .catch((err) => console.error('Include failed:', 'header.html', err));
  }

  function loadFooter() {
    const slot = document.getElementById('site-footer');
    if (!slot) return;
    const prefix = getPrefix();

    fetch(prefix + 'footer.html')
      .then((res) => res.text())
      .then((html) => {
        slot.innerHTML = html;
        const y = slot.querySelector('#y');
        if (y) y.textContent = new Date().getFullYear();
      })
      .catch(() => {});
  }

  function loadShell() {
    loadHeader();
    loadFooter();
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
