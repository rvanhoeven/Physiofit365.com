-- PhysioFit365: appointment requests, contacts and confirmation emails.
--
-- appointment_requests  one row per request from the website.
-- contacts              one row per person (unique email), created or completed automatically
--                       by a trigger when an appointment is requested.
-- Visitors (anon) may only INSERT into appointment_requests. contacts is not reachable through the public API.
--
-- Date and time rules, also enforced here so the website cannot be bypassed:
--   Monday to Friday only, no times up to and including 17:00 (slots 17:30 to 20:00, last visit ends by 21:00),
--   at least 7 days ahead (Mellany plans about a week in advance), at most about 6 months ahead.

create table if not exists public.contacts (
  id                uuid primary key default gen_random_uuid(),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  name              text not null,
  email             text not null unique,
  phone             text,
  address           text,
  town              text,
  language          text not null default 'en',
  browser_language  text,
  source            text not null default 'appointment',
  consented_at      timestamptz,
  last_request_at   timestamptz,
  notes             text
);
comment on table public.contacts is 'People who contacted the practice. Created by a trigger; a new request only fills empty fields, it never overwrites existing data, because the public form cannot prove who is typing.';

alter table public.contacts enable row level security;
revoke all on public.contacts from anon, authenticated;

create table if not exists public.appointment_requests (
  id                    uuid primary key default gen_random_uuid(),
  created_at            timestamptz not null default now(),
  contact_id            uuid references public.contacts (id) on delete set null,

  -- what the visitor fills in
  name                  text not null check (char_length(name) between 2 and 120),
  email                 text not null check (char_length(email) between 5 and 254 and email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  phone                 text not null check (char_length(phone) between 6 and 40),
  address               text not null check (char_length(address) between 3 and 200),
  town                  text not null check (char_length(town) between 2 and 120),
  service               text check (service is null or service in ('manual', 'work', 'sport', 'surgery', 'elderly', 'other')),
  message               text check (message is null or char_length(message) <= 4000),
  requested_date        date not null check (extract(isodow from requested_date) between 1 and 5),
  requested_time        time not null check (
                          requested_time between time '17:30' and time '20:00'
                          and extract(minute from requested_time) in (0, 30)
                          and extract(second from requested_time) = 0),

  -- captured automatically by the form
  language              text not null default 'en' check (language in ('en', 'nl', 'es')),
  browser_language      text check (browser_language is null or char_length(browser_language) <= 35),
  consent               boolean not null check (consent is true),
  consented_at          timestamptz not null default now(),

  -- internal follow-up by the practice (not writable by visitors)
  status                text not null default 'new' check (status in ('new', 'confirmed', 'rescheduled', 'declined', 'cancelled', 'done')),
  handled_at            timestamptz,
  notes                 text,
  confirmation_sent_at  timestamptz,
  notified_at           timestamptz
);
comment on table public.appointment_requests is 'Appointment requests from the website. A request, not a booking: Mellany confirms personally.';

create index if not exists appointment_requests_status_date_idx on public.appointment_requests (status, requested_date);
create index if not exists appointment_requests_email_created_idx on public.appointment_requests (email, created_at desc);
create index if not exists appointment_requests_contact_idx on public.appointment_requests (contact_id);

alter table public.appointment_requests enable row level security;

drop policy if exists "website can request an appointment" on public.appointment_requests;
create policy "website can request an appointment"
  on public.appointment_requests
  for insert
  to anon
  with check (
    status = 'new' and handled_at is null and notes is null and consent is true
    and requested_date >= ((now() at time zone 'Europe/Madrid')::date + 7)
    and requested_date <= ((now() at time zone 'Europe/Madrid')::date + 183)
  );

revoke all on public.appointment_requests from anon, authenticated;
grant insert (name, email, phone, address, town, service, message, requested_date, requested_time, language, browser_language, consent)
  on public.appointment_requests to anon;

-- Create or complete the contact, and link it, before the request is stored.
-- If the insert is rejected afterwards the contact change is rolled back with it.
create or replace function public.appointment_request_upsert_contact()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.email := lower(trim(new.email));
  insert into public.contacts as c (name, email, phone, address, town, language, browser_language, source, consented_at, last_request_at)
  values (new.name, new.email, new.phone, new.address, new.town, new.language, new.browser_language, 'appointment', now(), now())
  on conflict (email) do update set
    phone            = coalesce(c.phone, excluded.phone),
    address          = coalesce(c.address, excluded.address),
    town             = coalesce(c.town, excluded.town),
    browser_language = coalesce(c.browser_language, excluded.browser_language),
    consented_at     = coalesce(c.consented_at, excluded.consented_at),
    last_request_at  = now(),
    updated_at       = now()
  returning c.id into new.contact_id;
  return new;
end;
$$;
revoke all on function public.appointment_request_upsert_contact() from public, anon, authenticated;

drop trigger if exists appointment_request_contact on public.appointment_requests;
create trigger appointment_request_contact
  before insert on public.appointment_requests
  for each row execute function public.appointment_request_upsert_contact();

-- Emails for an appointment request, through the same Edge Function as the contact form.
create or replace function public.notify_appointment_request()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  perform net.http_post(
    url     := 'https://kmhsswngppprdaubpejb.supabase.co/functions/v1/notify-contact-request',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer sb_publishable_vjkGQTqsGr0JnuwGD54J3g_I4AhXJl2'
    ),
    body    := jsonb_build_object('id', new.id, 'type', 'appointment')
  );
  return new;
exception when others then
  return new;   -- never block a visitor's request because the email failed
end;
$$;
revoke all on function public.notify_appointment_request() from public, anon, authenticated;

drop trigger if exists appointment_request_notify on public.appointment_requests;
create trigger appointment_request_notify
  after insert on public.appointment_requests
  for each row execute function public.notify_appointment_request();

-- Contact form: remember the browser language and whether the visitor got a confirmation.
alter table public.contact_requests add column if not exists browser_language text
  check (browser_language is null or char_length(browser_language) <= 35);
alter table public.contact_requests add column if not exists confirmation_sent_at timestamptz;
comment on column public.contact_requests.browser_language is 'navigator.language of the visitor; decides the language of the confirmation email (fallback English).';
grant insert (browser_language) on public.contact_requests to anon;
