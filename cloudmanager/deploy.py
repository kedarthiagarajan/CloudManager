import boto3
import json
import os
import subprocess
import time
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from jinja2 import Template
from cloudmanager.utils import divide_configs,  get_security_group_with_ssh


def get_aws_resources(ec2_client, vm_config):
    """Retrieve or validate AWS resources like VPC, Subnet, Security Group, Key Pair, and AMI ID."""
    resources = {}

    # Check or get VPC
    if 'vpc_id' in vm_config:
        vpc_id = vm_config['vpc_id']
    else:
        vpc_response = ec2_client.describe_vpcs()
        vpc_id = vpc_response['Vpcs'][0]['VpcId']  # Assuming the first VPC found
    resources['vpc_id'] = vpc_id
    vm_config['vpc_id'] = vpc_id

    # Check or get Subnet
    if 'subnet_id' in vm_config:
        subnet_id = vm_config['subnet_id']
    else:
        subnet_response = ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        subnet_id = subnet_response['Subnets'][0]['SubnetId']  # Assuming the first subnet found
        vm_config['subnet_id'] = subnet_id
    resources['subnet_id'] = subnet_id

    # Check or get Security Group that allows SSH
    if 'security_group_ids' in vm_config:
        security_group_ids = vm_config['security_group_ids']
    else:
        security_group_ids = get_security_group_with_ssh(ec2_client, vpc_id)
    resources['security_group_ids'] = security_group_ids
    vm_config['security_group_ids'] = security_group_ids

    # Check or get Key Pair
    if 'key_pair_name' in vm_config:
        key_pair_name = vm_config['key_pair_name']
    else:
        kp_response = ec2_client.describe_key_pairs()
        key_pair_name = kp_response['KeyPairs'][0]['KeyName']  # Assuming the first key pair found
        vm_config['key_pair_name'] = key_pair_name
    resources['key_pair_name'] = key_pair_name

    # Get AMI ID based on the instance type and region
    ami_id = get_ami_id(ec2_client)
    resources['ami_id'] = ami_id

    return resources



def get_ami_id(ec2_client):
    """Retrieve an appropriate AMI ID based on the instance type and region."""
    try:
        # Example: Find the latest Ubuntu 20.04 LTS AMI in the region
        ami_response = ec2_client.describe_images(
            Filters=[
                {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*']},
                {'Name': 'state', 'Values': ['available']}
            ],
            Owners=['099720109477'],  # Canonical's AWS account ID
        )
        if ami_response['Images']:
            # Sort the AMIs by creation date to get the latest one
            ami_response['Images'].sort(key=lambda x: x['CreationDate'], reverse=True)
            return ami_response['Images'][0]['ImageId']  # Return the most recent AMI ID
        else:
            raise ValueError("No AMI found matching criteria.")
    except ClientError as e:
        print(f"Error retrieving AMI ID: {e}")
        raise

def generate_aws_terraform(access_key, secret_key, vm_config, resources, output_dir):
    """Generate Terraform configuration file."""
    ssh_public_key = ""  # Insert your SSH public key here as a string
    with open(os.path.expanduser("~/.ssh/id_rsa.pub"), "r") as key_file:
        ssh_public_key = key_file.read().strip()

    template = Template("""
    provider "aws" {
      region = "{{ region }}"
      access_key = "{{ access_key }}"
      secret_key = "{{ secret_key }}"
    }

    resource "aws_instance" "vm_instance" {
      ami           = "{{ ami_id }}"
      instance_type = "{{ instance_type }}"
      subnet_id     = "{{ subnet_id }}"
      vpc_security_group_ids = {{ security_group_ids }}
      key_name      = "{{ key_pair_name }}"

      user_data = <<-EOF
                  #!/bin/bash
                  # Create the 'experiment' user
                  sudo adduser experiment --gecos "Experiment User,,," --disabled-password
                  echo "experiment:experimentpassword" | sudo chpasswd

                  # Allow the 'experiment' user to use sudo without a password
                  echo "experiment ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/90-cloud-init-users

                  # Permit password authentication in sshd_config
                  sudo sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config

                  # Add SSH public key to the 'experiment' user
                  sudo mkdir -p /home/experiment/.ssh
                  echo "{{ ssh_public_key }}" | sudo tee /home/experiment/.ssh/authorized_keys
                  sudo chown -R experiment:experiment /home/experiment/.ssh
                  sudo chmod 600 /home/experiment/.ssh/authorized_keys

                  # Restart SSH service to apply changes
                  sudo systemctl restart sshd
                  EOF

      tags = {
        Name = "{{ vm_name }}"
      }
    }
    """)
    vm_config["vm_name"] = f"test-vm-{vm_config['region']}"
    # Ensure security_group_ids is a valid Terraform list
    security_group_ids_list = str(resources['security_group_ids']).replace("'", '"')
    terraform_config = template.render(
        region=vm_config['region'],
        access_key=str(access_key),  # Convert access_key to string
        secret_key=str(secret_key),  # Convert secret_key to string
        ami_id=resources['ami_id'],
        instance_type=vm_config['instance_type'],
        subnet_id=resources['subnet_id'],
        security_group_ids=security_group_ids_list,
        key_name=resources['key_pair_name'],
        vm_name=vm_config.get('vm_name', f"test-vm-{vm_config['region']}"),
        ssh_public_key=ssh_public_key
    )

    tf_file_path = os.path.join(output_dir, 'main.tf')
    with open(tf_file_path, 'w') as f:
        f.write(terraform_config)
    
    return tf_file_path




def run_terraform(output_dir):
    """Initialize and apply Terraform configuration."""
    subprocess.run(['terraform', 'init'], cwd=output_dir)
    subprocess.run(['terraform', 'apply', '-auto-approve'], cwd=output_dir)

def deploy_aws_vm(aws_config, output_dir):
    """Deploy AWS VMs using Terraform and SCP files to the instance, and update config with new information."""
    access_key = aws_config['credentials']['access_key']
    secret_key = aws_config['credentials']['secret_key']

    for vm_config in aws_config['vm_configs']:
        ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=vm_config['region']  # Default to the first region in the list
        )
        resources = get_aws_resources(ec2_client, vm_config)
        tf_file_path = generate_aws_terraform(access_key, secret_key, vm_config, resources, output_dir)
        print(f"Generated Terraform configuration at: {tf_file_path}")
        
        # Run Terraform to deploy the VM
        run_terraform(output_dir)

        # Wait until instance_id is available
        instance_id = wait_for_instance_id(ec2_client, f"test-vm-{vm_config['region']}")
        print(f"Instance ID for the deployed VM: {instance_id}")
        vm_config['instance_id'] = instance_id
        
        # Wait until the public IP becomes available
        public_ip = wait_for_public_ip(ec2_client, instance_id)
        print(f"Deployed instance with public IP: {public_ip}")

        # Allow some time for the instance to be fully ready (optional, depends on your use case)
        time.sleep(30)  # Wait 30 seconds for the instance to be fully ready

        # SCP files to the instance
        scp_files_to_instance(public_ip, 'experiment', vm_config.get('files', []))

        # Optional: Run any initial setup commands via SSH
        run_initial_setup_commands(public_ip, 'experiment', vm_config.get('initial_commands', []))

        # Update vm_config with instance_id and public_ip
        vm_config['instance_id'] = instance_id
        vm_config['public_ip'] = public_ip

def run_terraform(output_dir):
    """Initialize and apply Terraform configuration."""
    subprocess.run(['terraform', 'init'], cwd=output_dir)
    subprocess.run(['terraform', 'apply', '-auto-approve'], cwd=output_dir)

def wait_for_instance_id(ec2_client, vm_name, timeout=300, interval=10):
    """Wait until the instance ID is available using boto3."""
    elapsed_time = 0
    while elapsed_time < timeout:
        try:
            response = ec2_client.describe_instances(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [vm_name]},
                    {'Name': 'instance-state-name', 'Values': ['pending', 'running']}
                ]
            )
            instances = response.get('Reservations', [])
            for reservation in instances:
                for instance in reservation['Instances']:
                    instance_id = instance.get('InstanceId')
                    if instance_id:
                        return instance_id

        except Exception as e:
            print(f"Error retrieving instance ID: {e}")
        
        time.sleep(interval)
        elapsed_time += interval
        print(f"Waiting for instance ID... Elapsed time: {elapsed_time}s")

    raise TimeoutError(f"Timeout waiting for instance ID for VM with name {vm_name}")

def get_deployed_instance_info(vm_config, output_dir):
    """Retrieve information about the deployed instance from Terraform output."""
    terraform_output = subprocess.run(
        ['terraform', 'output', '-json'],
        cwd=output_dir,
        capture_output=True,
        text=True
    )
    outputs = json.loads(terraform_output.stdout)

    instance_info = {
        'instance_id': outputs.get('instance_id', {}).get('value'),
        'public_ip': outputs.get('public_ip', {}).get('value'),
        'private_ip': outputs.get('private_ip', {}).get('value'),
        'vm_name': vm_config.get('vm_name', f"test-vm-{vm_config['region']}")
    }

    return instance_info

def wait_for_public_ip(ec2_client, instance_id, timeout=300, interval=10):
    """Wait until the instance has a public IP address."""
    elapsed_time = 0
    while elapsed_time < timeout:
        try:
            response = ec2_client.describe_instances(InstanceIds=[instance_id])
            public_ip = response['Reservations'][0]['Instances'][0].get('PublicIpAddress')
            if public_ip:
                return public_ip
        except Exception as e:
            print(f"Error retrieving public IP: {e}")
        
        time.sleep(interval)
        elapsed_time += interval
        print(f"Waiting for public IP... Elapsed time: {elapsed_time}s")

    raise TimeoutError(f"Timeout waiting for public IP for instance {instance_id}")

def scp_files_to_instance(public_ip, user, files):
    """SCP files to the instance."""
    # Ensure the SSH private key has the correct permissions
    ssh_private_key_path = os.path.expanduser("~/.ssh/id_rsa")
    subprocess.run(['chmod', '600', ssh_private_key_path])

    for file in files:
        print(f"Copying {file} to {user}@{public_ip}:~")
        subprocess.run([
            'scp',
            '-o', 'StrictHostKeyChecking=no',  # Disable host key checking prompt
            '-i', ssh_private_key_path,  # Specify the private key to use
            file, f"{user}@{public_ip}:~"
        ])

def run_initial_setup_commands(public_ip, user, commands):
    """Run initial setup commands via SSH."""
    for command in commands:
        print(f"Running command on {user}@{public_ip}: {command}")
        subprocess.run(['ssh', f"{user}@{public_ip}", command])

def terminate_aws_instance(access_key, secret_key, region, instance_id):
    """Terminate a specific AWS EC2 instance by instance ID."""
    ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region # Default to the first region in the list
        )

    print("===============================================================: " , instance_id)
    try:
        # Terminate the instance
        response = ec2_client.terminate_instances(InstanceIds=[instance_id])
        print(f"Initiated termination for instance: {instance_id}")

        # Check the status of the instance termination
        for instance in response['TerminatingInstances']:
            current_state = instance['CurrentState']['Name']
            previous_state = instance['PreviousState']['Name']
            print(f"Instance {instance['InstanceId']} is changing from {previous_state} to {current_state}.")
        
        return True

    except ClientError as e:
        print(f"Error terminating instance {instance_id}: {e}")
        return False
    
# Example usage
if __name__ == "__main__":
    output_dir = "./terraform"  # Directory where Terraform files will be generated
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    aws_configs, azure_configs = divide_configs('../config.yaml')
    for aws_config in aws_configs:
        print(aws_config)
        deploy_aws_vm(aws_config, output_dir)
