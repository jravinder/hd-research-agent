/* HD Research Studio — shared across all pages */

/* Hide page chrome when loaded inside workspace iframe */
(function() {
  if (window.self !== window.top) {
    // We're inside an iframe (workspace shell)
    document.documentElement.classList.add('in-workspace');
    // Hide headers, nav, footers — workspace provides these
    document.addEventListener('DOMContentLoaded', function() {
      var els = document.querySelectorAll('header, [data-universal-nav], [data-universal-footer], nav.sticky, nav.fixed');
      for (var i = 0; i < els.length; i++) {
        els[i].style.display = 'none';
      }
      // Remove top padding that was for the fixed nav
      var main = document.querySelector('main');
      if (main) main.style.paddingTop = '1.5rem';
      // Also hide any standalone footers at the end
      var footers = document.querySelectorAll('footer, .text-center.py-4');
      for (var j = 0; j < footers.length; j++) {
        var ft = footers[j];
        if (ft.textContent.indexOf('not medical advice') > -1 || ft.textContent.indexOf('hdsa.org') > -1) {
          ft.style.display = 'none';
        }
      }
    });
  }
})();

/* Google Analytics */
(function() {
  var GA_ID = 'G-N8BMJ7ZG5V'; // Replace with real measurement ID
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', GA_ID);
})();

/* Inject Google Translate (clean, no popups) */
function googleTranslateElementInit() {
  new google.translate.TranslateElement({
    pageLanguage: 'en',
    includedLanguages: 'en,hi,ta,te,bn,mr,kn,ml,gu,pa,ur,es,fr,de,ja,zh-CN,pt,ar,ko,it,ru',
    layout: google.translate.TranslateElement.InlineLayout.HORIZONTAL,
    autoDisplay: false,
    multilanguagePage: false
  }, 'google_translate_element');
}

/* Load Google Translate script */
(function() {
  var s = document.createElement('script');
  s.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
  document.head.appendChild(s);
})();

/* Universal nav — injected on subpages (not index.html) */
(function() {
  // Skip index.html (has its own nav)
  if (window.location.pathname === '/' || window.location.pathname.endsWith('index.html')) return;
  // Skip if page already has a nav with data-universal-nav
  if (document.querySelector('[data-universal-nav]')) return;

  // Find existing header/nav and replace it
  var existing = document.querySelector('header, nav');
  if (!existing) return;

  var nav = document.createElement('header');
  nav.setAttribute('data-universal-nav', 'true');
  nav.className = 'sticky top-0 z-50 backdrop-blur-md shadow-sm';
  nav.style.background = 'rgba(253,249,233,0.8)';
  nav.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;max-width:80rem;margin:0 auto;padding:0 1.5rem;height:4rem;">' +
    '<a href="index.html" style="display:flex;align-items:center;gap:0.5rem;font-weight:600;font-size:1.125rem;letter-spacing:-0.025em;color:#1c1917;text-decoration:none;">' +
      '<span class="material-symbols-outlined" style="color:#b45309;">arrow_back</span> HD Research Hub' +
    '</a>' +
    '<div style="display:flex;align-items:center;gap:0.75rem;">' +
      '<div id="google_translate_element"></div>' +
      '<a href="chat.html" style="font-size:0.875rem;font-weight:600;color:#b45309;text-decoration:none;display:flex;align-items:center;gap:0.25rem;">' +
        '<span class="material-symbols-outlined" style="font-size:1rem;">chat</span> Ask HD Research' +
      '</a>' +
    '</div>' +
  '</div>';

  existing.parentNode.replaceChild(nav, existing);
})();

/* Universal footer — injected on every page */
(function() {
  // Only add if no footer already exists
  if (document.querySelector('[data-universal-footer]')) return;

  var footer = document.createElement('div');
  footer.setAttribute('data-universal-footer', 'true');
  footer.style.textAlign = 'center';
  footer.style.padding = '16px';
  footer.innerHTML = '<p style="font-size:12px;color:#a8a29e;">This is a research and educational tool, not medical advice. For HD support, visit <a href="https://hdsa.org" style="color:#78716c;text-decoration:underline;">hdsa.org</a>.</p>';
  document.body.appendChild(footer);
})();
