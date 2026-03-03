# RTCMS4J Environment Repository

This repository contains the environment setup configurations for RTCMS4J. It provides Docker configurations for both self-hosted deployment and local development environments.

## Folder Structure

The repository is divided into two main subfolders:

- [`docker`](https://github.com/hse-rtcms4j/rtcms4j-env/tree/main/docker)
- [`kubernetes`](https://github.com/hse-rtcms4j/rtcms4j-env/tree/main/kubernetes)

### `docker` Folder

This folder contains the configuration files required for a **self-hosted, single replica deployment** of the RTCMS4J system. It allows deployment of a standalone RTCMS4J system with basic functionality.

To deploy the system, you will need to run the `docker-compose` setup provided in this folder.

### `kubernetes` Folder

This folder contains the Helm-charts for **distributed, scaled deployment** of the RTCMS4J system. It allows deployment of a kubernetes distributed RTCMS4J system, that can be integrated with external databases (postgres and keyval) and keycloak.

To deploy system components, you will need to prepare your cluster and follow `kubernetes` setup provided in this folder.

## Usage

Please refer to the specific folder (`docker`) for detailed instructions on how to set up the environment and deploy the system. Folder contains its own `README.md` with the necessary setup steps.
