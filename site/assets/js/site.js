(function () {
  "use strict";

  // Mobile navigation
  var btn = document.querySelector(".menu-btn");
  var nav = document.getElementById("nav");
  if (btn && nav) {
    btn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  initAppointmentForm();

  // Contact form -> Supabase (insert-only through Row Level Security)
  var form = document.getElementById("contact-form");
  if (!form) return;

  // Arriving from a "contact" button (#form): put the cursor in the first field
  if (location.hash === "#form" && form.elements.first_name) {
    setTimeout(function () { try { form.elements.first_name.focus({ preventScroll: true }); } catch (e) {} }, 350);
  }

  // Arriving from the "where does it hurt" list: fill in the subject
  try {
    var subject = new URLSearchParams(location.search).get("subject");
    if (subject && form.elements.subject) form.elements.subject.value = subject.slice(0, 200);
  } catch (e) {}

  var msgs = {};
  try { msgs = JSON.parse(form.getAttribute("data-messages") || "{}"); } catch (e) {}
  var status = form.querySelector(".status");
  var submit = form.querySelector('button[type="submit"]');
  var cfg = window.PHYSIOFIT_CONFIG || {};

  function setStatus(text, isError) {
    status.textContent = text || "";
    status.classList.toggle("error", !!isError);
  }

  function validate() {
    var ok = true;
    var firstBad = null;
    form.querySelectorAll(".field").forEach(function (f) { f.classList.remove("invalid"); });
    form.querySelectorAll("[required]").forEach(function (el) {
      if (!el.checkValidity()) {
        var f = el.closest(".field");
        if (f) f.classList.add("invalid");
        if (!firstBad) firstBad = el;
        ok = false;
      }
    });
    var replyBy = form.querySelector('input[name="reply_by"]:checked').value;
    var phone = form.elements.phone;
    if (replyBy === "phone" && !phone.value.trim()) {
      phone.closest(".field").classList.add("invalid");
      if (!firstBad) firstBad = phone;
      ok = false;
    }
    if (firstBad) firstBad.focus();
    return ok;
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    setStatus("");
    if (form.elements.website.value) return;          // honeypot: bots fill this in
    if (!validate()) { setStatus(msgs.invalid, true); return; }
    if (!cfg.supabaseUrl || !cfg.supabaseAnonKey) { setStatus(msgs.not_configured, true); return; }

    var v = function (n) { var s = form.elements[n].value.trim(); return s ? s : null; };
    var row = {
      first_name: v("first_name"),
      last_name: v("last_name"),
      email: v("email"),
      phone: v("phone"),
      town: v("town"),
      service: v("service"),
      subject: v("subject"),
      message: v("message"),
      reply_by: form.querySelector('input[name="reply_by"]:checked').value,
      language: form.getAttribute("data-lang") || "en",
      browser_language: browserLanguage(),
      consent: form.elements.consent.checked
    };

    submit.disabled = true;
    submit.textContent = msgs.sending;

    fetch(cfg.supabaseUrl.replace(/\/$/, "") + "/rest/v1/contact_requests", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": cfg.supabaseAnonKey,
        "Authorization": "Bearer " + cfg.supabaseAnonKey,
        "Prefer": "return=minimal"
      },
      body: JSON.stringify(row)
    }).then(function (res) {
      if (!res.ok) { var err = new Error("HTTP " + res.status); err.status = res.status; throw err; }
      form.hidden = true;
      form.parentNode.querySelector(".success").hidden = false;
    }).catch(function (err) {
      setStatus(err.status === 429 ? msgs.err_limit : msgs.error, true);
      submit.disabled = false;
      submit.textContent = msgs.submit;
    });
  });

  function browserLanguage() {
    return String(navigator.language || "").slice(0, 35) || null;
  }

  // Appointment form: own calendar, because a native date field cannot block weekends.
  // The same rules are enforced by the database.
  function initAppointmentForm() {
    var form = document.getElementById("appointment-form");
    if (!form) return;

    var LEAD_DAYS = 7, MAX_DAYS = 180;
    var lang = form.getAttribute("data-lang") || "en";
    var msgs = {};
    try { msgs = JSON.parse(form.getAttribute("data-messages") || "{}"); } catch (e) {}
    var cfg = window.PHYSIOFIT_CONFIG || {};
    var cal = document.getElementById("cal");
    var picked = document.getElementById("picked-date");
    var status = form.querySelector(".status");
    var submit = form.querySelector('button[type="submit"]');
    var times = form.querySelectorAll('input[name="time"]');

    // Dates are handled as UTC midnight, so the visitor's own time zone cannot shift a day.
    var parts = {};
    new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Madrid", year: "numeric", month: "2-digit", day: "2-digit" })
      .formatToParts(new Date()).forEach(function (p) { parts[p.type] = p.value; });
    var DAY = 86400000;
    var today = Date.UTC(+parts.year, +parts.month - 1, +parts.day);
    var first = today + LEAD_DAYS * DAY, last = today + MAX_DAYS * DAY;
    var iso = function (t) { return new Date(t).toISOString().slice(0, 10); };
    var selected = null;
    var view = new Date(first); view = Date.UTC(view.getUTCFullYear(), view.getUTCMonth(), 1);
    var fmt = function (o) { return new Intl.DateTimeFormat(lang, Object.assign({ timeZone: "UTC" }, o)); };
    var isOpen = function (t) { var d = new Date(t).getUTCDay(); return t >= first && t <= last && d !== 0 && d !== 6; };

    function render(focusDay) {
      var v = new Date(view), y = v.getUTCFullYear(), m = v.getUTCMonth();
      var canPrev = Date.UTC(y, m, 0) >= first;
      var canNext = Date.UTC(y, m + 1, 1) <= last;
      var html = '<div class="cal-head"><button type="button" class="cal-nav" data-go="-1" aria-label="' + msgs.prev + '"' + (canPrev ? "" : " disabled") + '>&lsaquo;</button>' +
        '<strong aria-live="polite">' + fmt({ month: "long", year: "numeric" }).format(v) + '</strong>' +
        '<button type="button" class="cal-nav" data-go="1" aria-label="' + msgs.next + '"' + (canNext ? "" : " disabled") + '>&rsaquo;</button></div><div class="cal-grid">';
      for (var i = 0; i < 7; i++) html += '<span class="cal-dow">' + fmt({ weekday: "short" }).format(Date.UTC(2024, 0, 1 + i)) + "</span>";
      var offset = (v.getUTCDay() + 6) % 7, days = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
      for (i = 0; i < offset; i++) html += "<span></span>";
      for (i = 1; i <= days; i++) {
        var t = Date.UTC(y, m, i), open = isOpen(t);
        html += '<button type="button" class="cal-day' + (selected === t ? " on" : "") + '" data-t="' + t + '"' +
          (open ? "" : " disabled") + (selected === t ? ' aria-pressed="true"' : "") +
          ' aria-label="' + fmt({ weekday: "long", day: "numeric", month: "long" }).format(t) + '">' + i + "</button>";
      }
      cal.innerHTML = html + "</div>";
      if (focusDay) { var b = cal.querySelector(".cal-day.on"); if (b) b.focus(); }
    }

    cal.addEventListener("click", function (ev) {
      var go = ev.target.closest("[data-go]");
      if (go && !go.disabled) {
        var v = new Date(view);
        view = Date.UTC(v.getUTCFullYear(), v.getUTCMonth() + (+go.getAttribute("data-go")), 1);
        render();
        return;
      }
      var day = ev.target.closest(".cal-day");
      if (!day || day.disabled) return;
      selected = +day.getAttribute("data-t");
      render(true);
      picked.textContent = fmt({ weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(selected);
      times.forEach(function (r) { r.disabled = false; });
      document.getElementById("pick-date").classList.remove("invalid");
    });
    form.addEventListener("change", function (ev) {
      if (ev.target.name === "time") document.getElementById("pick-time").classList.remove("invalid");
    });
    render();

    function setStatus(text, isError) {
      status.textContent = text || "";
      status.classList.toggle("error", !!isError);
    }

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      setStatus("");
      if (form.elements.website.value) return;   // honeypot: bots fill this in
      var time = form.querySelector('input[name="time"]:checked');
      var firstBad = null;
      form.querySelectorAll(".field").forEach(function (f) { f.classList.remove("invalid"); });
      form.querySelectorAll("[required]").forEach(function (el) {
        if (!el.checkValidity()) {
          var f = el.closest(".field");
          if (f) f.classList.add("invalid");
          if (!firstBad) firstBad = el;
        }
      });
      var problem = msgs.invalid;
      if (!time) { document.getElementById("pick-time").classList.add("invalid"); firstBad = document.getElementById("pick-time"); problem = msgs.err_time; }
      if (selected === null) { document.getElementById("pick-date").classList.add("invalid"); firstBad = document.getElementById("pick-date"); problem = msgs.err_date; }
      if (firstBad) {
        setStatus(problem, true);
        if (firstBad.tagName === "FIELDSET") firstBad.scrollIntoView({ block: "center" }); else firstBad.focus();
        return;
      }
      if (!cfg.supabaseUrl || !cfg.supabaseAnonKey) { setStatus(msgs.not_configured, true); return; }

      var v = function (n) { var s = form.elements[n].value.trim(); return s ? s : null; };
      var row = {
        first_name: v("first_name"), last_name: v("last_name"), email: v("email"), phone: v("phone"), address: v("address"), town: v("town"),
        service: v("service"), message: v("message"),
        requested_date: iso(selected), requested_time: time.value,
        language: lang, browser_language: browserLanguage(),
        consent: form.elements.consent.checked
      };

      submit.disabled = true;
      submit.textContent = msgs.sending;
      fetch(cfg.supabaseUrl.replace(/\/$/, "") + "/rest/v1/appointment_requests", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "apikey": cfg.supabaseAnonKey,
          "Authorization": "Bearer " + cfg.supabaseAnonKey,
          "Prefer": "return=minimal"
        },
        body: JSON.stringify(row)
      }).then(function (res) {
        if (!res.ok) { var err = new Error("HTTP " + res.status); err.status = res.status; throw err; }
        form.hidden = true;
        var ok = form.parentNode.querySelector(".success");
        ok.hidden = false;
        ok.focus();
      }).catch(function (err) {
        // 401/403 = the database refused the date, for instance a page left open for days
        setStatus(err.status === 429 ? msgs.err_limit : err.status === 401 || err.status === 403 ? msgs.err_full : msgs.error, true);
        submit.disabled = false;
        submit.textContent = msgs.submit;
      });
    });
  }
})();
