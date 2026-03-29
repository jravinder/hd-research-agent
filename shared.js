/* HD Research Hub — shared across all pages */

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
