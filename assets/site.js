(function () {
  var C = window.SITE_CONFIG || {};

  // Sticky header: darken + blur once the page scrolls.
  var head = document.querySelector('.site-head');
  if (head) {
    var onScroll = function () { head.classList.toggle('scrolled', window.scrollY > 8); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // Service buttons: swap to the affiliate URL when one is configured.
  var aff = C.AFFILIATE || {};
  document.querySelectorAll('a[data-aff]').forEach(function (a) {
    var url = aff[a.getAttribute('data-aff')];
    if (url) {
      a.href = url;
      a.rel = 'sponsored nofollow noopener';
      a.classList.add('is-aff');
    }
  });

  // Amazon "Check price" buttons: hidden unless AMAZON_TAG is set.
  if (C.AMAZON_TAG) {
    document.querySelectorAll('a[data-amazon]').forEach(function (a) {
      a.href = 'https://www.amazon.com/s?k=' + encodeURIComponent(a.getAttribute('data-amazon')) +
        '&tag=' + encodeURIComponent(C.AMAZON_TAG);
      a.rel = 'sponsored nofollow noopener';
      a.hidden = false;
    });
  }

  // Contact page.
  var box = document.getElementById('contact-box');
  if (box) {
    if (C.HUBSPOT_FORM_ID && C.HUBSPOT_PORTAL_ID) {
      var s = document.createElement('script');
      s.src = 'https://js.hsforms.net/forms/embed/v2.js';
      s.onload = function () {
        if (window.hbspt) window.hbspt.forms.create({
          portalId: C.HUBSPOT_PORTAL_ID, formId: C.HUBSPOT_FORM_ID, target: '#contact-box',
          onFormReady: function () {
            // The form renders in a same-origin iframe; give it the dark brand styles (AA contrast).
            var f = box.querySelector('iframe');
            var d = f && f.contentDocument;
            if (!d) return;
            var st = d.createElement('style');
            st.textContent = 'body,.hs-form{font-family:Inter,"Helvetica Neue",Helvetica,Arial,sans-serif;color:#fff}' +
              'label,.hs-form-field>label,legend,.hs-field-desc{color:#fff !important}' +
              '.hs-field-desc{color:rgba(255,255,255,.72) !important}' +
              'input:not([type=submit]):not([type=checkbox]):not([type=radio]),textarea,select{background:#191919 !important;color:#fff !important;border:1px solid rgba(255,255,255,.28) !important;border-radius:4px !important}' +
              'input[type=submit],.hs-button{background:#9a00ff !important;border:0 !important;color:#fff !important;border-radius:50px !important;min-height:52px;padding:0 28px !important;font:700 14px Inter,Arial,sans-serif !important;text-transform:uppercase;letter-spacing:.06em;cursor:pointer}' +
              '.hs-error-msg,.hs-error-msgs label{color:#ff8a8a !important}' +
              '.legal-consent-container,.hs-richtext,.legal-consent-container p{color:rgba(255,255,255,.72) !important}a{color:#8e7cc3 !important}';
            d.head.appendChild(st);
          }
        });
      };
      document.body.appendChild(s);
    } else if (C.CONTACT_EMAIL) {
      var a = document.createElement('a');
      a.href = 'mailto:' + C.CONTACT_EMAIL;
      a.textContent = C.CONTACT_EMAIL;
      box.textContent = 'Email: ';
      box.appendChild(a);
    }
  }

  // Cord-cutting calculator.
  var calc = document.getElementById('calc');
  if (calc) {
    var fmt = function (n) { return (n < 0 ? '-$' : '$') + Math.abs(n).toFixed(2); };
    var run = function () {
      var bill = parseFloat(document.getElementById('bill').value) || 0;
      var internet = parseFloat(document.getElementById('internet').value) || 0;
      var device = parseFloat(document.getElementById('device').value) || 0;
      var subs = 0;
      calc.querySelectorAll('select[data-svc]').forEach(function (c) { subs += parseFloat(c.value) || 0; });
      var newMonthly = subs + internet;
      var monthly = bill - newMonthly;
      document.getElementById('r-subs').textContent = fmt(subs);
      document.getElementById('r-new').textContent = fmt(newMonthly);
      document.getElementById('r-month').textContent = fmt(monthly);
      document.getElementById('r-year').textContent = fmt(monthly * 12 - device);
      var msg = document.getElementById('r-msg');
      if (!bill) msg.textContent = 'Enter your current TV bill to see your savings.';
      else if (monthly > 0) msg.textContent = 'You would save about ' + fmt(monthly) + ' a month with this mix.';
      else msg.textContent = 'This mix costs more than your current bill. Try fewer services or a cheaper plan.';
    };
    calc.addEventListener('input', run);
    calc.addEventListener('change', run);
    run();
  }
})();
