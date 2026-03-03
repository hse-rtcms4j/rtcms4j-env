# Kubernetes Setup

This setup uses Kubernetes to bring up scalable services:

- k8s/service/ClusterIp **rtcms4j-core** : `rtcms4j-core:80`
- k8s/service/ClusterIp **rtcms4j-notify**: `rtcms4j-notify:80`
- k8s/service/ClusterIp **rtcms4j-web**: `rtcms4j-web:3000`

## Requirements

**Tools**:

- Kubectl installed and configured to access cluster
- Helm installed and configured to manage cluster

**Systems**:

- Keycloak system installed and accessible
- Postgresql database installed and accessible
- Valkey installed and accessible

## Setup

1. Locate to `./helm-charts` folder:

    ```bash
    cd ./helm-charts
    ```

2. Install `rtcms4j-core` chart:

   Configure `files/application.yaml` filling valid services urls. Moreover, you can add extra Spring configuration.
   Configure `values.yaml` filling credential secrets. Moreover, you can customize setup.

    ```bash
    helm install rtcms4j-core ./rtcms4j-core
    ```

   This will install k8s/deployment of rtcms4j-core to the cluster.

3. Install `rtcms4j-notify` chart:

   Configure `files/application.yaml` filling valid services urls. Moreover, you can add extra Spring configuration.
   Configure `values.yaml` filling credential secrets. Moreover, you can customize setup.

    ```bash
    helm install rtcms4j-notify ./rtcms4j-notify
    ```

   This will install k8s/deployment of rtcms4j-notify to the cluster.

4. Install `rtcms4j-web` chart:

   Configure `values.yaml` filling valid services urls. Moreover, you can customize setup.

    ```bash
    helm install rtcms4j-web ./rtcms4j-web
    ```

   This will install k8s/deployment of rtcms4j-web to the cluster.

## Further setup

Exposing this services to the outer network via k8s/ingress or k8s/loadbalancer depends on your current cluster stack
and requirements, hence should be made manually.

## Optional structures

There are also 2 more directories:

- `environment`
- `monitoring`

### `environment` Folder

This folder contains instruction to install required services: managed Postgresql, scalable valkey, and keycloak.

### `monitoring` Folder

This folder contains instruction to install monitoring subsystem: Opentelemtry subsystem + loki + tempo + victoriametrics + grafana.
