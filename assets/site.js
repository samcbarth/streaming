(function () {
  var C = window.SITE_CONFIG || {};

  // Theme toggle (light / dark), remembered per browser.
  var root = document.documentElement;
  try { var saved = localStorage.getItem('theme'); if (saved) root.setAttribute('data-theme', saved); } catch (e) {}
  var tbtn = document.getElementById('theme-toggle');
  if (tbtn) tbtn.addEventListener('click', function () {
    var cur = root.getAttribute('data-theme') ||
      (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    var next = cur === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) {}
  });

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
        if (window.hbspt) window.hbspt.forms.create({ portalId: C.HUBSPOT_PORTAL_ID, formId: C.HUBSPOT_FORM_ID, target: '#contact-box' });
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
