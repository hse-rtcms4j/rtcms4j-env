\c keycloak_db

create schema if not exists keycloak authorization keycloak_user;

grant usage, create on schema keycloak to keycloak_user;

revoke all on schema public from public;

alter default privileges for role keycloak_user in schema keycloak
  grant select, insert, update, delete on tables to keycloak_user;

alter default privileges for role keycloak_user in schema keycloak
  grant usage, select, update on sequences to keycloak_user;
