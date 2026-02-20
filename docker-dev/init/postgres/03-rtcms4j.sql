\c rtcms4j_db

create schema if not exists rtcms4j authorization rtcms4j_user;

grant usage, create on schema rtcms4j to rtcms4j_user;

alter default privileges for role rtcms4j_user in schema rtcms4j
  grant select, insert, update, delete on tables to rtcms4j_user;

alter default privileges for role rtcms4j_user in schema rtcms4j
  grant usage, select, update on sequences to rtcms4j_user;
