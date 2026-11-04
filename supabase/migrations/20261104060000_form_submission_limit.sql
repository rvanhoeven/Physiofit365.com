-- PhysioFit365: at most 2 form submissions per 24 hours, for both website forms together.
-- Counted per email address and per IP address, so changing only one of them does not help.
-- Only hashes are stored, in a schema the public API cannot reach, and they are removed after 2 days.
-- Requests without API headers (the dashboard, SQL) are not limited.

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create table private.form_limit_salt (
  id   boolean primary key default true check (id),
  salt text not null default encode(extensions.gen_random_bytes(32), 'hex')
);
insert into private.form_limit_salt default values;

create table private.form_submissions (
  id         bigint generated always as identity primary key,
  key_hash   text not null,
  created_at timestamptz not null default now()
);
create index form_submissions_key_time on private.form_submissions (key_hash, created_at);

alter table private.form_limit_salt enable row level security;
alter table private.form_submissions enable row level security;

create function public.enforce_form_limit()
returns trigger
language plpgsql
security definer
set search_path to ''
as $function$
declare
  max_per_day constant int := 2;
  v_headers json := nullif(current_setting('request.headers', true), '')::json;
  v_ip   text;
  v_salt text;
  v_key  text;
  v_keys text[];
  v_hash text;
begin
  if v_headers is null then
    return new;
  end if;

  select salt into v_salt from private.form_limit_salt;
  v_ip := nullif(trim(coalesce(
    v_headers ->> 'cf-connecting-ip',
    v_headers ->> 'x-real-ip',
    split_part(v_headers ->> 'x-forwarded-for', ',', 1)
  )), '');
  v_keys := array['email:' || lower(trim(new.email))];
  if v_ip is not null then
    v_keys := v_keys || ('ip:' || v_ip);
  end if;

  foreach v_key in array v_keys loop
    v_hash := encode(extensions.digest(v_salt || v_key, 'sha256'), 'hex');
    perform pg_advisory_xact_lock(hashtextextended(v_hash, 0));
    if (select count(*) from private.form_submissions f
        where f.key_hash = v_hash and f.created_at > now() - interval '24 hours') >= max_per_day then
      raise exception 'Too many form submissions' using errcode = 'PT429';
    end if;
  end loop;

  foreach v_key in array v_keys loop
    insert into private.form_submissions (key_hash)
    values (encode(extensions.digest(v_salt || v_key, 'sha256'), 'hex'));
  end loop;

  delete from private.form_submissions where created_at < now() - interval '2 days';
  return new;
end;
$function$;

revoke all on function public.enforce_form_limit() from public, anon, authenticated;

create trigger a_form_limit before insert on public.contact_requests
  for each row execute function public.enforce_form_limit();
create trigger a_form_limit before insert on public.appointment_requests
  for each row execute function public.enforce_form_limit();
