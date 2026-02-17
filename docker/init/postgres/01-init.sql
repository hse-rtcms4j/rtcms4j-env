-- keycloak
create role keycloak_user login password 'keycloak';

create database keycloak_db owner keycloak_user;

-- rtcms4j-core
create role rtcms4j_user login password 'rtcms4j';

create database rtcms4j_db owner rtcms4j_user;
