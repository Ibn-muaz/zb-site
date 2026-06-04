/* ═══════════════════════════════════════════════════════
   ZB LANDS AND HOME — Main JavaScript
   ═══════════════════════════════════════════════════════ */

'use strict';

// ── Utility: Get CSRF Token ──
function getCookie(name) {
  const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? v[2] : null;
}
const CSRF = getCookie('csrftoken');

// ── Utility: Fetch Wrapper ──
async function apiFetch(url, method = 'GET', data = null) {
  const opts = {
    method,
    headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
    credentials: 'same-origin',
  };
  if (data) opts.body = JSON.stringify(data);
  const r = await fetch(url, opts);
  return r.json();
}

// ── Toast Notification ──
function showToast(msg, type = 'success') {
  const icons = { success: 'check-circle-fill', error: 'exclamation-triangle-fill', info: 'info-circle-fill', warning: 'exclamation-circle-fill' };
  const colors = { success: '#2ECC71', error: '#E74C3C', info: '#3498DB', warning: '#F39C12' };
  const t = document.createElement('div');
  t.className = 'zb-toast';
  t.style.cssText = `
    position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);
    background:rgba(15,32,64,0.95);backdrop-filter:blur(20px);
    border:1px solid ${colors[type]}44;border-radius:12px;padding:14px 20px;
    display:flex;align-items:center;gap:12px;color:#E8E4DA;font-size:.875rem;
    z-index:99999;box-shadow:0 8px 32px rgba(0,0,0,.4);
    transition:all .4s cubic-bezier(.4,0,.2,1);min-width:280px;max-width:400px;
  `;
  t.innerHTML = `<i class="bi bi-${icons[type]}" style="color:${colors[type]};font-size:1.1rem;flex-shrink:0"></i><span>${msg}</span>`;
  document.body.appendChild(t);
  setTimeout(() => { t.style.transform = 'translateX(-50%) translateY(0)'; t.style.opacity = '1'; }, 10);
  setTimeout(() => { t.style.transform = 'translateX(-50%) translateY(80px)'; t.style.opacity = '0'; setTimeout(() => t.remove(), 400); }, 4000);
}

// ═══════════════════════════════════════════════════════
// 1. DARK / LIGHT THEME TOGGLE
// ═══════════════════════════════════════════════════════
(function initTheme() {
  const btn = document.getElementById('themeToggle');
  const icon = document.getElementById('themeIcon');
  const saved = localStorage.getItem('zb-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  if (icon) icon.className = saved === 'dark' ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
  if (btn) {
    btn.addEventListener('click', () => {
      const cur = document.documentElement.getAttribute('data-theme');
      const next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('zb-theme', next);
      if (icon) icon.className = next === 'dark' ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
    });
  }
})();

// ═══════════════════════════════════════════════════════
// 2. NAVBAR SCROLL EFFECT
// ═══════════════════════════════════════════════════════
(function initNavScroll() {
  const nav = document.getElementById('mainNav');
  if (!nav) return;
  const update = () => nav.classList.toggle('scrolled', window.scrollY > 60);
  window.addEventListener('scroll', update, { passive: true });
  update();
})();

// ═══════════════════════════════════════════════════════
// 3. BACK TO TOP
// ═══════════════════════════════════════════════════════
(function initBackToTop() {
  const btn = document.getElementById('backToTop');
  if (!btn) return;
  window.addEventListener('scroll', () => btn.classList.toggle('show', window.scrollY > 400), { passive: true });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();

// ═══════════════════════════════════════════════════════
// 4. AUTO-DISMISS ALERTS
// ═══════════════════════════════════════════════════════
document.querySelectorAll('.zb-alert').forEach(el => {
  setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 300);
  }, 5000);
});

// ═══════════════════════════════════════════════════════
// 5. SAVE / UNSAVE PROPERTY
// ═══════════════════════════════════════════════════════
document.querySelectorAll('.save-btn').forEach(btn => {
  btn.addEventListener('click', async (e) => {
    e.preventDefault();
    const slug = btn.dataset.slug;
    if (!slug) return;
    btn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i>';
    try {
      const res = await apiFetch(`/properties/${slug}/save/`, 'POST');
      const saved = res.saved;
      btn.innerHTML = `<i class="bi bi-${saved ? 'heart-fill' : 'heart'}"></i>`;
      btn.classList.toggle('saved', saved);
      showToast(res.message || (saved ? 'Property saved!' : 'Removed from saved'), saved ? 'success' : 'info');
    } catch {
      btn.innerHTML = '<i class="bi bi-heart"></i>';
      showToast('Please log in to save properties.', 'warning');
    }
  });
});

// ═══════════════════════════════════════════════════════
// 6. PROPERTY GALLERY THUMBNAILS
// ═══════════════════════════════════════════════════════
(function initGallery() {
  const mainImg = document.getElementById('galleryMain');
  if (!mainImg) return;
  document.querySelectorAll('.gallery-thumb').forEach((thumb, i) => {
    thumb.addEventListener('click', () => {
      const src = thumb.dataset.src;
      mainImg.style.opacity = '0';
      setTimeout(() => { mainImg.src = src; mainImg.style.opacity = '1'; }, 200);
      document.querySelectorAll('.gallery-thumb').forEach(t => t.classList.remove('active'));
      thumb.classList.add('active');
    });
    if (i === 0) thumb.classList.add('active');
  });
})();

// ═══════════════════════════════════════════════════════
// 7. PROPERTY FILTER — PRICE RANGE
// ═══════════════════════════════════════════════════════
(function initPriceRange() {
  const minSlider = document.getElementById('priceMin');
  const maxSlider = document.getElementById('priceMax');
  const minDisplay = document.getElementById('priceMinDisplay');
  const maxDisplay = document.getElementById('priceMaxDisplay');
  if (!minSlider || !maxSlider) return;

  const fmt = v => '₦' + (parseInt(v) / 1000000).toFixed(1) + 'M';

  const update = () => {
    if (minDisplay) minDisplay.textContent = fmt(minSlider.value);
    if (maxDisplay) maxDisplay.textContent = fmt(maxSlider.value);
    const minPct = (minSlider.value - minSlider.min) / (minSlider.max - minSlider.min) * 100;
    const maxPct = (maxSlider.value - maxSlider.min) / (maxSlider.max - maxSlider.min) * 100;
    minSlider.style.setProperty('--val', minPct + '%');
    maxSlider.style.setProperty('--val', maxPct + '%');
  };

  minSlider.addEventListener('input', update);
  maxSlider.addEventListener('input', update);
  update();
})();

// ═══════════════════════════════════════════════════════
// 8. MARK ALL NOTIFICATIONS READ
// ═══════════════════════════════════════════════════════
const markAll = document.getElementById('markAllRead');
if (markAll) {
  markAll.addEventListener('click', async (e) => {
    e.preventDefault();
    try {
      await apiFetch('/api/v1/notifications/read/', 'POST');
      document.querySelectorAll('.notif-item.unread').forEach(el => el.classList.remove('unread'));
      const badge = document.querySelector('.notif-badge');
      if (badge) badge.remove();
    } catch {}
  });
}

// ═══════════════════════════════════════════════════════
// 9. PROPERTY MAP (LEAFLET)
// ═══════════════════════════════════════════════════════
function initMap(lat, lng, title) {
  const mapEl = document.getElementById('propertyMap');
  if (!mapEl || typeof L === 'undefined') return;
  const map = L.map('propertyMap', { zoomControl: true }).setView([lat, lng], 14);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);
  const icon = L.divIcon({
    html: `<div style="background:linear-gradient(135deg,#C9A84C,#A07835);border-radius:50% 50% 50% 0;width:36px;height:36px;transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;box-shadow:0 4px 12px rgba(0,0,0,.4)"><i class="bi bi-buildings-fill" style="transform:rotate(45deg);color:#0A1628;font-size:16px"></i></div>`,
    className: '',
    iconSize: [36, 36],
    iconAnchor: [18, 36],
  });
  L.marker([lat, lng], { icon }).addTo(map).bindPopup(`<strong>${title}</strong>`).openPopup();
}

// ═══════════════════════════════════════════════════════
// 10. PROPERTY COMPARISON (store in sessionStorage)
// ═══════════════════════════════════════════════════════
(function initCompare() {
  document.querySelectorAll('.compare-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const slug = btn.dataset.slug;
      let list = JSON.parse(sessionStorage.getItem('compare') || '[]');
      if (list.includes(slug)) {
        list = list.filter(s => s !== slug);
        btn.classList.remove('active');
        showToast('Removed from comparison', 'info');
      } else if (list.length >= 3) {
        showToast('You can compare up to 3 properties.', 'warning');
        return;
      } else {
        list.push(slug);
        btn.classList.add('active');
        showToast('Added to comparison!', 'success');
      }
      sessionStorage.setItem('compare', JSON.stringify(list));
      updateCompareBar(list);
    });
  });

  function updateCompareBar(list) {
    let bar = document.getElementById('compareBar');
    if (!list.length) { if (bar) bar.remove(); return; }
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'compareBar';
      bar.style.cssText = 'position:fixed;bottom:0;left:0;right:0;background:rgba(10,22,40,.97);border-top:1px solid rgba(201,168,76,.25);padding:14px 24px;display:flex;align-items:center;justify-content:center;gap:16px;z-index:9998;backdrop-filter:blur(20px)';
      document.body.appendChild(bar);
    }
    bar.innerHTML = `<span style="color:#C9A84C;font-weight:600">${list.length} properties selected</span>
      <a href="/properties/compare/?${list.map(s=>'ids='+s).join('&')}" class="btn btn-gold btn-sm">Compare Now</a>
      <button onclick="sessionStorage.removeItem('compare');document.getElementById('compareBar').remove()" class="btn btn-outline-light btn-sm">Clear</button>`;
  }

  const existing = JSON.parse(sessionStorage.getItem('compare') || '[]');
  if (existing.length) updateCompareBar(existing);
})();

// ═══════════════════════════════════════════════════════
// 11. ANIMATED COUNTERS (for stats section)
// ═══════════════════════════════════════════════════════
(function initCounters() {
  const els = document.querySelectorAll('[data-count]');
  if (!els.length) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const target = parseInt(el.dataset.count);
      const duration = 1800;
      const start = performance.now();
      const tick = (now) => {
        const p = Math.min((now - start) / duration, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.floor(ease * target).toLocaleString();
        if (p < 1) requestAnimationFrame(tick);
        else el.textContent = target.toLocaleString() + (el.dataset.suffix || '');
      };
      requestAnimationFrame(tick);
      observer.unobserve(el);
    });
  }, { threshold: 0.5 });
  els.forEach(el => observer.observe(el));
})();

// ═══════════════════════════════════════════════════════
// 12. INTERSECTION OBSERVER — FADE IN ANIMATIONS
// ═══════════════════════════════════════════════════════
(function initAnimations() {
  const els = document.querySelectorAll('.animate-on-scroll');
  if (!els.length) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('animate__animated', e.target.dataset.animation || 'animate__fadeInUp');
        e.target.style.opacity = '1';
        observer.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });
  els.forEach(el => { el.style.opacity = '0'; observer.observe(el); });
})();

// ═══════════════════════════════════════════════════════
// 13. NEWSLETTER FORM
// ═══════════════════════════════════════════════════════
const newsletterForm = document.getElementById('newsletterForm');
if (newsletterForm) {
  newsletterForm.addEventListener('submit', (e) => {
    e.preventDefault();
    showToast('Thank you for subscribing! 🎉', 'success');
    newsletterForm.reset();
  });
}

// ═══════════════════════════════════════════════════════
// 14. IMAGE LAZY LOAD
// ═══════════════════════════════════════════════════════
if ('IntersectionObserver' in window) {
  const imgs = document.querySelectorAll('img[data-src]');
  const imgObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.src = e.target.dataset.src;
        imgObserver.unobserve(e.target);
      }
    });
  });
  imgs.forEach(img => imgObserver.observe(img));
}

// ═══════════════════════════════════════════════════════
// 15. ADMIN — DELETE CONFIRM
// ═══════════════════════════════════════════════════════
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', (e) => {
    if (!confirm(el.dataset.confirm || 'Are you sure?')) e.preventDefault();
  });
});

// ═══════════════════════════════════════════════════════
// 16. ADMIN — SUSPEND USER TOGGLE
// ═══════════════════════════════════════════════════════
document.querySelectorAll('.suspend-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const userId = btn.dataset.userId;
    try {
      const res = await apiFetch(`/admin-panel/users/${userId}/suspend/`, 'POST');
      btn.textContent = res.suspended ? 'Activate' : 'Suspend';
      btn.className = res.suspended ? 'btn btn-success btn-sm' : 'btn btn-warning btn-sm';
      showToast(res.suspended ? 'User suspended.' : 'User activated.', res.suspended ? 'warning' : 'success');
    } catch { showToast('Action failed.', 'error'); }
  });
});

// ═══════════════════════════════════════════════════════
// 17. NEGOTIATE OFFER AMOUNT — FORMAT
// ═══════════════════════════════════════════════════════
document.querySelectorAll('input[name="offer_amount"]').forEach(input => {
  input.addEventListener('blur', () => {
    const v = parseFloat(input.value.replace(/,/g, ''));
    if (!isNaN(v)) input.value = v;
  });
});

// ═══════════════════════════════════════════════════════
// 18. PWA SERVICE WORKER REGISTRATION
// ═══════════════════════════════════════════════════════
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js').catch(() => {});
  });
}

// ═══════════════════════════════════════════════════════
// 19. PROPERTY SEARCH — INSTANT FILTER (client-side)
// ═══════════════════════════════════════════════════════
(function initSearch() {
  const searchBox = document.getElementById('quickSearch');
  if (!searchBox) return;
  searchBox.addEventListener('input', () => {
    const q = searchBox.value.toLowerCase();
    document.querySelectorAll('.property-card').forEach(card => {
      const text = card.textContent.toLowerCase();
      card.closest('.col').style.display = text.includes(q) ? '' : 'none';
    });
  });
})();

// Export for inline use
window.ZBProps = { showToast, apiFetch, initMap, getCookie };
