# Docker Compose Setup

This setup uses Docker Compose to bring up three services:

- **Keycloak**: Identity and Access Management, available on port `8080`
- **Frontend**: The user interface for the application, available on port `3000`
- **Backend**: Hidden behind the API Gateway, available on port `8000`

## Requirements

- Docker
- Docker Compose

## Setup

1. **Start the services** using Docker Compose:

    ```bash
    docker-compose up -d
    ```

   This will spin up the services in the background.

2. **Access the services**:
    - Keycloak: `http://localhost:8080`
    - Frontend: `http://localhost:3000`
    - Backend (via API Gateway): `http://localhost:8000`

3. **Persistent storage**:
    - `/tmp` folder is generated and served as volumes storage for postgres and valkey.

## Keycloak Setup

1. **Create an admin user** in Keycloak:
    - Navigate to `http://localhost:8080`
    - Login with the admin credentials you have set (or admin-admin).
    - Select rtcms4j realm. Go to the **Users** section, and add a new user with the username `admin`.

2. **Assign the `rtcms4j-super-admin` role** to the new user:
    - Once the user is created, go to the **Roles** tab in the user's settings.
    - Assign the role `rtcms4j-super-admin` to the user.

   This role is required to fully start using the application.

## Accessing the Application

- **Frontend**: After starting up, the frontend will be available at `http://localhost:3000`.
- **Backend**: The backend API is accessible through the API Gateway at `http://localhost:8000`.

## Stopping the Services

To stop and remove the containers, run:

```bash
docker-compose down
```
