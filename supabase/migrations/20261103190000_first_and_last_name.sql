-- Separate first and last name on both forms and on contacts.
-- "name" stays as the full name (used by the emails) and is composed by a trigger.
alter table public.contact_requests
  add column if not exists first_name text check (first_name is null or char_length(first_name) between 1 and 60),
  add column if not exists last_name text check (last_name is null or char_length(last_name) between 1 and 59);
alter table public.appointment_requests
  add column if not exists first_name text check (first_name is null or char_length(first_name) between 1 and 60),
  add column if not exists last_name text check (last_name is null or char_length(last_name) between 1 and 59);
alter table public.contacts
  add column if not exists first_name text,
  add column if not exists last_name text;

comment on column public.contact_requests.name is 'Full name, composed from first_name and last_name by a trigger. Older rows and cached pages only have this.';
comment on column public.appointment_requests.name is 'Full name, composed from first_name and last_name by a trigger.';

-- Existing request: first word = first name, the rest = last name.
update public.contact_requests
set first_name = split_part(trim(name), ' ', 1),
    last_name  = nullif(trim(substr(trim(name), char_length(split_part(trim(name), ' ', 1)) + 1)), '')
where first_name is null;

grant insert (first_name, last_name) on public.contact_requests to anon;
grant insert (first_name, last_name) on public.appointment_requests to anon;

create or replace function public.contact_request_compose_name()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.first_name is not null or new.last_name is not null then
    new.first_name := nullif(trim(new.first_name), '');
    new.last_name  := nullif(trim(new.last_name), '');
    new.name := trim(concat_ws(' ', new.first_name, new.last_name));
  end if;
  return new;
end;
$$;
revoke all on function public.contact_request_compose_name() from public, anon, authenticated;

drop trigger if exists contact_request_name on public.contact_requests;
create trigger contact_request_name
  before insert on public.contact_requests
  for each row execute function public.contact_request_compose_name();

create or replace function public.appointment_request_upsert_contact()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.first_name is not null or new.last_name is not null then
    new.first_name := nullif(trim(new.first_name), '');
    new.last_name  := nullif(trim(new.last_name), '');
    new.name := trim(concat_ws(' ', new.first_name, new.last_name));
  end if;
  new.email := lower(trim(new.email));
  insert into public.contacts as c (name, first_name, last_name, email, phone, address, town, language, browser_language, source, consented_at, last_request_at)
  values (new.name, new.first_name, new.last_name, new.email, new.phone, new.address, new.town, new.language, new.browser_language, 'appointment', now(), now())
  on conflict (email) do update set
    first_name       = coalesce(c.first_name, excluded.first_name),
    last_name        = coalesce(c.last_name, excluded.last_name),
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
