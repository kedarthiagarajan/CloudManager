# Platform Configuration Guide

This guide will help you configure the `config.yaml` file for deploying virtual machines (VMs) across various cloud providers and regions. The `config.yaml` file defines the cloud providers, the credentials to access them, and the specific VM configurations, including the regions/datacenters, custom code paths, and files to be deployed.

## YAML Structure Overview

The `config.yaml` file is structured into the following main components:

- **Config**: The root element of the file.
  - **cloud_providers**: A list of cloud providers. Each cloud provider has its own set of configurations.

Each cloud provider entry consists of:
- **name**: The name of the cloud provider (e.g., `AWS`, `Azure`).
- **credentials**: User-specific credentials required for logging in to the cloud provider.
- **vm_configs**: A list of VM configurations for that provider. Each configuration specifies details such as the region, instance type, custom code path, and files to be placed on the VM.

## Detailed Configuration Instructions

### 1. Cloud Provider Configuration

Each cloud provider must be defined under the `cloud_providers` section.

#### Example:
```yaml
cloud_providers:
  - name: AWS
    credentials:
      access_key: YOUR_ACCESS_KEY
      secret_key: YOUR_SECRET_KEY
    vm_configs: # Define VMs for AWS
      ...
      
  - name: Azure
    credentials:
      client_id: YOUR_CLIENT_ID
      client_secret: YOUR_CLIENT_SECRET
      tenant_id: YOUR_TENANT_ID
    vm_configs: # Define VMs for Azure
      ...
```

### 2. Credentials

Provide the necessary credentials for each cloud provider. The fields will vary depending on the provider.

#### AWS Credentials Example:
```yaml
credentials:
  access_key: YOUR_ACCESS_KEY
  secret_key: YOUR_SECRET_KEY
```

#### Azure Credentials Example:
```yaml
credentials:
  client_id: YOUR_CLIENT_ID
  client_secret: YOUR_CLIENT_SECRET
  tenant_id: YOUR_TENANT_ID
```

### 3. VM Configurations

The `vm_configs` section under each cloud provider allows you to specify the details for each VM you wish to deploy.

#### VM Configuration Fields:
- **region**: The region or datacenter where the VM should be deployed (e.g., `us-east-1`, `eastus`).
- **instance_type**: The type of instance/VM to deploy (e.g., `t2.micro` for AWS, `Standard_B1s` for Azure).
- **custom_code_path**: The local path to the custom code you want to execute on the VM.
- **files**: A list of file paths to be copied to the VM.

#### Example:
```yaml
vm_configs:
  - region: us-east-1
    instance_type: t2.micro
    custom_code_path: /path/to/code
    files:
      - /path/to/local/file1
      - /path/to/local/file2

  - region: eastus
    instance_type: Standard_B1s
    custom_code_path: /path/to/other/code
    files:
      - /path/to/local/file4
```

### 4. Example Full Configuration File

Here’s an example of a complete `config.yaml` file:

```yaml
Config:
  cloud_providers:
    - name: AWS
      credentials:
        access_key: YOUR_ACCESS_KEY
        secret_key: YOUR_SECRET_KEY
      vm_configs:
        - region: us-east-1
          instance_type: t2.micro
          custom_code_path: /path/to/code
          files:
            - /path/to/local/file1
            - /path/to/local/file2
        - region: us-west-2
          instance_type: t2.micro
          custom_code_path: /path/to/other/code
          files:
            - /path/to/local/file3

    - name: Azure
      credentials:
        client_id: YOUR_CLIENT_ID
        client_secret: YOUR_CLIENT_SECRET
        tenant_id: YOUR_TENANT_ID
      vm_configs:
        - region: eastus
          instance_type: Standard_B1s
          custom_code_path: /path/to/code
          files:
            - /path/to/local/file4
```

## Notes

- Ensure that the file paths provided under `custom_code_path` and `files` are accessible from the machine where the deployment script is running.
- The credentials should be kept secure and not shared publicly.