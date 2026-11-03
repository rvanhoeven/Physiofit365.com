// Sends the emails for a new website request. Called by database triggers with { id, type }:
//   type "contact" (default)  row in public.contact_requests      (website form)
//   type "appointment"        row in public.appointment_requests  (appointment button)
//
// Each request gives two emails:
//   1. confirmation to the visitor, in the language of their browser (fallback English)
//   2. summary in Dutch to the practice (MAIL_TO), with bcc to MAIL_BCC
// Each is stamped separately (confirmation_sent_at, notified_at), so nothing is mailed twice.
//
// The confirmation deliberately does not repeat the free-text message: the address is not verified,
// so it must not reveal health details to a mistyped address or carry someone's text to a stranger.
// For the same reason at most 3 confirmations per address per day are sent.
//
// Secrets: RESEND_API_KEY, MAIL_FROM, MAIL_TO, MAIL_BCC (comma separated; default rick@vanhoeven.es)
import { createClient } from "npm:@supabase/supabase-js@2";

const SITE = "https://www.physiofit365.com";
const PHONE = "+34 686 04 22 00";
const PHONE_TEL = "+34686042200";
const EMAIL = "info@physiofit365.com";
const ADDRESS = "Calle Agata Buzón 77, 03170 Rojales (Alicante)";
const MAX_CONFIRMATIONS_PER_DAY = 3;

type Lang = "en" | "nl" | "es";
type Row = Record<string, any>;

const esc = (s: unknown) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
const list = (s: string | undefined) => (s ?? "").split(",").map((x) => x.trim()).filter(Boolean);

const SERVICE: Record<string, string> = {
  manual: "Manuele therapie", work: "Werkblessure", sport: "Sportblessure",
  surgery: "Revalidatie na een operatie", elderly: "Zorg voor ouderen", other: "Anders / weet niet",
};
const LANG_NL: Record<string, string> = { en: "Engels", nl: "Nederlands", es: "Spaans" };
const LOCALE: Record<Lang, string> = { en: "en-GB", nl: "nl-NL", es: "es-ES" };

/** Browser language decides; English when we have no text for it. Old cached pages send none: use the page language. */
function replyLang(r: Row): Lang {
  const b = String(r.browser_language ?? "").slice(0, 2).toLowerCase();
  if (!b) return (["en", "nl", "es"].includes(r.language) ? r.language : "en") as Lang;
  return (["en", "nl", "es"].includes(b) ? b : "en") as Lang;
}

function fmtDate(d: string, locale: string) {
  return new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" })
    .format(new Date(d + "T12:00:00Z"));
}
const fmtTime = (t: string) => String(t).slice(0, 5);

/** The name comes from a public form: leave it out if it looks like a link or an address. */
function safeName(n: unknown) {
  const s = String(n ?? "").trim();
  return !s || s.length > 60 || /[:\/@<>]|www\.|\.[a-z]{2,}\b/i.test(s) ? "" : s;
}

const T = {
  en: {
    hi: (n: string) => n ? `Dear ${n},` : "Hello,",
    tagline: "Physiotherapy at home on the Costa Blanca",
    summary: "Your request",
    date: "Date", time: "Time",
    next: "What happens next",
    sign: "Kind regards,", role: "Physiotherapist and nurse",
    footer: "You receive this email because this address was entered on physiofit365.com. Not you? Then you can ignore this email.",
    urgent: "With severe or sudden symptoms, contact your doctor or call 112.",
    appointment: {
      subject: "We have received your appointment request",
      title: "Thank you for your request",
      intro: "We have received your request for a home visit by Mellany. This is a request and not yet a confirmed appointment.",
      steps: "Mellany will check her diary and contact you personally to confirm this time or suggest another one. She plans about one week ahead.",
    },
    contact: {
      subject: "We have received your message",
      title: "Thank you for your message",
      intro: "Your message has arrived safely and has gone straight to Mellany.",
      steps: (phone: boolean) => `Mellany will reply as soon as she can, ${phone ? "by phone" : "by email"} as you asked. Treatments take place at your home; there is no practice to visit.`,
    },
  },
  nl: {
    hi: (n: string) => n ? `Beste ${n},` : "Goedendag,",
    tagline: "Fysiotherapie aan huis aan de Costa Blanca",
    summary: "Uw verzoek",
    date: "Datum", time: "Tijd",
    next: "Hoe gaat het verder",
    sign: "Met vriendelijke groet,", role: "Fysiotherapeut en verpleegkundige",
    footer: "U ontvangt deze e-mail omdat dit adres is ingevuld op physiofit365.com. Was u dit niet? Dan kunt u deze e-mail negeren.",
    urgent: "Bij hevige of plotselinge klachten: neem contact op met uw huisarts of bel 112.",
    appointment: {
      subject: "Wij hebben uw afspraakverzoek ontvangen",
      title: "Bedankt voor uw verzoek",
      intro: "Wij hebben uw verzoek voor een bezoek aan huis door Mellany ontvangen. Dit is een verzoek en nog geen bevestigde afspraak.",
      steps: "Mellany kijkt in haar agenda en neemt persoonlijk contact met u op om dit moment te bevestigen of een ander moment voor te stellen. Zij plant ongeveer een week vooruit.",
    },
    contact: {
      subject: "Wij hebben uw bericht ontvangen",
      title: "Bedankt voor uw bericht",
      intro: "Uw bericht is goed aangekomen en rechtstreeks naar Mellany gegaan.",
      steps: (phone: boolean) => `Mellany antwoordt zo snel mogelijk, ${phone ? "telefonisch" : "per e-mail"} zoals u heeft aangegeven. De behandelingen vinden bij u thuis plaats; er is geen praktijk om langs te komen.`,
    },
  },
  es: {
    hi: (n: string) => n ? `Hola, ${n}:` : "Hola:",
    tagline: "Fisioterapia a domicilio en la Costa Blanca",
    summary: "Tu solicitud",
    date: "Fecha", time: "Hora",
    next: "Qué ocurre ahora",
    sign: "Un cordial saludo,", role: "Fisioterapeuta y enfermera",
    footer: "Recibes este correo porque esta dirección se introdujo en physiofit365.com. ¿No has sido tú? Puedes ignorar este correo.",
    urgent: "Si tienes síntomas intensos o repentinos, contacta con tu médico o llama al 112.",
    appointment: {
      subject: "Hemos recibido tu solicitud de cita",
      title: "Gracias por tu solicitud",
      intro: "Hemos recibido tu solicitud de una visita a domicilio de Mellany. Es una solicitud, todavía no una cita confirmada.",
      steps: "Mellany revisará su agenda y se pondrá en contacto contigo personalmente para confirmar este momento o proponerte otro. Planifica con aproximadamente una semana de antelación.",
    },
    contact: {
      subject: "Hemos recibido tu mensaje",
      title: "Gracias por tu mensaje",
      intro: "Tu mensaje ha llegado correctamente y ha ido directamente a Mellany.",
      steps: (phone: boolean) => `Mellany te responderá lo antes posible, ${phone ? "por teléfono" : "por correo electrónico"} como has indicado. Los tratamientos se realizan en tu domicilio; no hay consulta que visitar.`,
    },
  },
};

const FONT = "'Segoe UI',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif";

/** Shared layout: table based with inline styles, because email clients ignore most other CSS. */
function layout(o: { lang: string; preheader: string; tagline: string; title: string; body: string; foot: string }) {
  return `<!doctype html>
<html lang="${o.lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>${esc(o.title)}</title></head>
<body style="margin:0;padding:0;background:#fff2f9;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">${esc(o.preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#fff2f9;"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background:#ffffff;border-radius:18px;overflow:hidden;">
  <tr><td align="center" style="padding:26px 24px 16px;background:#ffffff;">
    <a href="${SITE}"><img src="${SITE}/assets/img/logo.png" width="170" alt="PhysioFit365" style="display:block;width:170px;max-width:60%;height:auto;border:0;"></a>
    <div style="font:600 14px/1.4 ${FONT};color:#5d4f63;padding-top:8px;">${esc(o.tagline)}</div>
  </td></tr>
  <tr><td height="6" bgcolor="#fe26ac" style="height:6px;font-size:0;line-height:0;background:#fe26ac;background-image:linear-gradient(115deg,#fa0dd6 0%,#fe26ac 42%,#fd866c 78%,#e68e43 100%);">&nbsp;</td></tr>
  <tr><td style="padding:30px 32px 26px;font:400 16px/1.6 ${FONT};color:#17111b;">
    <h1 style="margin:0 0 16px;font:800 25px/1.2 ${FONT};color:#17111b;">${esc(o.title)}</h1>
    ${o.body}
  </td></tr>
  <tr><td bgcolor="#17111b" style="padding:24px 32px;background:#17111b;font:400 14px/1.6 ${FONT};color:#e9dcee;">
    <div style="font-weight:700;color:#ffffff;">PhysioFit365 · Mellany Ginny van Hoeven</div>
    <div>${esc(ADDRESS)}</div>
    <div><a href="tel:${PHONE_TEL}" style="color:#ffb3e1;">${PHONE}</a> · <a href="mailto:${EMAIL}" style="color:#ffb3e1;">${EMAIL}</a></div>
    <div><a href="${SITE}" style="color:#ffb3e1;">www.physiofit365.com</a></div>
    <div style="padding-top:12px;font-size:12px;line-height:1.5;color:#b9a9c1;">${esc(o.foot)}</div>
  </td></tr>
</table></td></tr></table></body></html>`;
}

const detailTable = (rows: [string, string][]) =>
  `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#fff2f9;border-radius:12px;margin:0 0 20px;">${rows.map(([k, v]) =>
    `<tr><td style="padding:10px 8px 10px 16px;font:400 14px/1.4 ${FONT};color:#5d4f63;vertical-align:top;width:34%;">${esc(k)}</td><td style="padding:10px 16px 10px 8px;font:700 15px/1.4 ${FONT};color:#17111b;vertical-align:top;">${v}</td></tr>`).join("")}</table>`;

function confirmationMail(type: "contact" | "appointment", r: Row) {
  const lang = replyLang(r);
  const t = T[lang];
  const name = safeName(r.name);
  const p = (s: string) => `<p style="margin:0 0 16px;">${esc(s)}</p>`;
  const h = (s: string) => `<h2 style="margin:0 0 8px;font:700 17px/1.3 ${FONT};color:#a8007a;">${esc(s)}</h2>`;
  let subject: string, title: string, intro: string, steps: string, extra = "", textExtra = "";
  if (type === "appointment") {
    ({ subject, title, intro, steps } = t.appointment);
    const date = fmtDate(r.requested_date, LOCALE[lang]), time = fmtTime(r.requested_time);
    extra = h(t.summary) + detailTable([[t.date, esc(date)], [t.time, esc(time)]]);
    textExtra = `${t.date}: ${date}\n${t.time}: ${time}\n\n`;
  } else {
    ({ subject, title, intro } = t.contact);
    steps = t.contact.steps(r.reply_by === "phone");
  }
  const sign = `<p style="margin:0;">${esc(t.sign)}<br><strong>Mellany van Hoeven</strong><br><span style="color:#5d4f63;">${esc(t.role)}</span></p>`;
  const urgent = `<p style="margin:0 0 20px;padding:10px 14px;border-left:4px solid #fe26ac;font-size:14px;color:#5d4f63;">${esc(t.urgent)}</p>`;
  return {
    subject,
    html: layout({
      lang, preheader: intro, tagline: t.tagline, title, foot: t.footer,
      body: p(t.hi(name)) + p(intro) + extra + h(t.next) + p(steps) + urgent + sign,
    }),
    text: `${t.hi(name)}\n\n${intro}\n\n${textExtra}${steps}\n\n${t.urgent}\n\n${t.sign}\nMellany van Hoeven\n${t.role}\n\nPhysioFit365 · ${ADDRESS}\n${PHONE} · ${EMAIL}\n${SITE}\n\n${t.footer}\n`,
  };
}

function summaryMail(type: "contact" | "appointment", r: Row) {
  const received = new Date(r.created_at).toLocaleString("nl-NL", { timeZone: "Europe/Madrid", dateStyle: "long", timeStyle: "short" });
  const lang = replyLang(r);
  const plain: [string, string][] = [];
  const add = (k: string, v: unknown) => plain.push([k, String(v ?? "-") || "-"]);
  let title: string, subject: string, intro: string;
  if (type === "appointment") {
    const date = fmtDate(r.requested_date, "nl-NL"), time = fmtTime(r.requested_time);
    title = "Nieuw afspraakverzoek";
    subject = `Afspraakverzoek: ${String(r.name).slice(0, 60)}, ${date} om ${time}`;
    intro = "Er is via de website een afspraak aangevraagd. De klant is al als contact aangemaakt en heeft een ontvangstbevestiging gekregen; de afspraak moet jij nog bevestigen.";
    add("Gewenste datum", date); add("Gewenste tijd", time);
    add("Naam", r.name); add("E-mail", r.email); add("Telefoon", r.phone); add("Adres", r.address); add("Woonplaats", r.town);
    add("Gaat over", SERVICE[r.service]);
  } else {
    title = "Nieuw bericht via de website";
    subject = `Nieuw bericht via website: ${String(r.name).slice(0, 80)}`;
    intro = "Er is een bericht binnengekomen via het websiteformulier. De afzender heeft een ontvangstbevestiging gekregen.";
    add("Naam", r.name); add("E-mail", r.email); add("Telefoon", r.phone); add("Woonplaats / regio", r.town);
    add("Gaat over", SERVICE[r.service]); add("Onderwerp", r.subject);
    add("Antwoord graag per", r.reply_by === "phone" ? "Telefoon" : "E-mail");
  }
  add("Taal bevestiging", LANG_NL[lang]);
  const cell = (k: string, v: string) => {
    if (k === "E-mail") return `<a href="mailto:${esc(v)}" style="color:#a8007a;">${esc(v)}</a>`;
    if (k === "Telefoon" && v !== "-") return `<a href="tel:${esc(v.replace(/[^+\d]/g, ""))}" style="color:#a8007a;">${esc(v)}</a>`;
    return esc(v);
  };
  const msg = String(r.message ?? "").trim();
  const body = `<p style="margin:0 0 18px;">${esc(intro)}</p>` +
    detailTable(plain.map(([k, v]) => [k, cell(k, v)])) +
    (msg ? `<h2 style="margin:0 0 8px;font:700 17px/1.3 ${FONT};color:#a8007a;">Bericht</h2><p style="margin:0 0 18px;padding:14px 16px;background:#fff2f9;border-left:4px solid #fe26ac;border-radius:8px;white-space:pre-wrap;">${esc(msg)}</p>` : "") +
    `<p style="margin:0;font-size:14px;color:#5d4f63;">Ontvangen op ${esc(received)}. Een antwoord op deze mail gaat rechtstreeks naar de klant.</p>`;
  return {
    subject, 
    html: layout({ lang: "nl", preheader: subject, tagline: "Melding vanuit de website", title, foot: "Interne melding van physiofit365.com. Bevat persoonsgegevens, dus niet doorsturen.", body }),
    text: `${title}\n\n${intro}\n\n` + plain.map(([k, v]) => `${k}: ${v}`).join("\n") + (msg ? `\n\nBericht:\n${msg}` : "") + `\n\nOntvangen op ${received}.\n`,
  };
}

async function send(key: string, payload: Record<string, unknown>) {
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.ok ? null : `Resend error ${res.status}: ${await res.text()}`;
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });

  let id: string | undefined, type: "contact" | "appointment" = "contact";
  try {
    const b = await req.json();
    id = b?.id;
    if (b?.type === "appointment") type = "appointment";
  } catch { /* ignore */ }
  if (!id || !/^[0-9a-f-]{36}$/i.test(id)) return new Response("Bad request", { status: 400 });

  const table = type === "appointment" ? "appointment_requests" : "contact_requests";
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { data: r, error } = await db.from(table).select("*").eq("id", id).maybeSingle();
  if (error) return new Response(error.message, { status: 500 });
  if (!r) return new Response("Nothing to send", { status: 200 });

  const to = list(Deno.env.get("MAIL_TO"));
  const bccEnv = list(Deno.env.get("MAIL_BCC"));
  const bcc = bccEnv.length ? bccEnv : ["rick@vanhoeven.es"];
  const from = Deno.env.get("MAIL_FROM");
  const key = Deno.env.get("RESEND_API_KEY");
  if (!to.length || !from || !key) return new Response("Mail secrets are not configured", { status: 500 });

  const errors: string[] = [];

  if (!r.notified_at) {
    const m = summaryMail(type, r);
    const err = await send(key, { from, to, bcc, reply_to: r.email, subject: m.subject, html: m.html, text: m.text });
    if (err) errors.push(err);
    else await db.from(table).update({ notified_at: new Date().toISOString() }).eq("id", id);
  }

  // Only recent rows: older requests from before this mail existed never get a late confirmation.
  const fresh = Date.now() - new Date(r.created_at).getTime() < 24 * 3600 * 1000;
  if (!r.confirmation_sent_at && fresh) {
    const since = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
    const { count } = await db.from(table).select("id", { count: "exact", head: true })
      .ilike("email", String(r.email).replace(/[%_\\]/g, "\\$&")).gte("confirmation_sent_at", since);
    if ((count ?? 0) < MAX_CONFIRMATIONS_PER_DAY) {
      const m = confirmationMail(type, r);
      const err = await send(key, { from, to: [r.email], reply_to: EMAIL, subject: m.subject, html: m.html, text: m.text });
      if (err) errors.push(err);
      else await db.from(table).update({ confirmation_sent_at: new Date().toISOString() }).eq("id", id);
    }
  }

  return errors.length ? new Response(errors.join("\n"), { status: 502 }) : new Response("Sent", { status: 200 });
});
