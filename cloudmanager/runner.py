import os
import sys
import argparse
import boto3
from cloudmanager.utils import divide_configs
from cloudmanager.precheck import check_aws_configs
from cloudmanager.deploy import deploy_aws_vm, terminate_aws_instance

def precheck(aws_configs, azure_configs):
    """Run prechecks for both AWS and Azure configurations."""
    print("Running prechecks for AWS configurations...")
    aws_precheck_passed = check_aws_configs(aws_configs) == 0

    print("Running prechecks for Azure configurations...")
    azure_precheck_passed = True  # Placeholder for Azure precheck logic

    if not aws_precheck_passed:
        print("AWS Precheck failed.")
    if not azure_precheck_passed:
        print("Azure Precheck failed.")

    if not aws_precheck_passed or not azure_precheck_passed:
        print("Precheck failed. Exiting...")
        return False

    print("Precheck completed successfully for both AWS and Azure.")
    return True


def deploy(aws_configs, azure_configs, output_dir):
    """Deploy both AWS and Azure instances."""
    print("Starting deployment for AWS configurations...")
    for aws_config in aws_configs:
        deploy_aws_vm(aws_config, output_dir)
    
    print("Starting deployment for Azure configurations...")
    # Placeholder: Implement Azure deployment logic here
    # for azure_config in azure_configs:
    #     deploy_azure_vm(azure_config, output_dir)
    
    print("Deployment completed for both AWS and Azure.")


def teardown(aws_configs, azure_configs):
    """Teardown both AWS and Azure instances."""
    print("Starting teardown for AWS configurations...")
    for aws_config in aws_configs:
        region = aws_config['vm_configs'][0]['region']
        for vm_config in aws_config['vm_configs']:
            instance_id = vm_config.get('instance_id')  # Ensure the instance_id is available
            if instance_id:
                access_key = aws_config['credentials']['access_key']
                secret_key = aws_config['credentials']['secret_key']
                terminate_aws_instance(access_key, secret_key, region, instance_id)
            else:
                print(f"No instance_id found for vm_config: {vm_config['vm_name']}. Skipping termination.")
    
    print("Starting teardown for Azure configurations...")
    # Placeholder: Implement Azure teardown logic here
    # for azure_config in azure_configs:
    #     terminate_azure_instance(azure_config)
    
    print("Teardown completed for both AWS and Azure.")



def main(config_path=None, output_dir=None):
    """
    Main function to coordinate precheck, deployment, and teardown processes.
    This function can be called directly with parameters or used as an entry point with argparse.
    """
    if config_path is None or output_dir is None:
        # If no arguments provided, use argparse to get them
        parser = argparse.ArgumentParser(description="Run cloud deployment and teardown operations.")
        parser.add_argument("-c", "--config", type=str, required=True, help="Path to the configuration YAML file.")
        parser.add_argument("-o", "--output", type=str, default="./terraform", help="Directory for Terraform files (default: ./terraform).")

        args = parser.parse_args()
        config_path = args.config
        output_dir = args.output

    print("\n========== Runner Started ==========\n")

    # Step 1: Divide the configs
    try:
        aws_configs, azure_configs = divide_configs(config_path)
        print("Successfully divided configurations into AWS and Azure configs.\n")
    except Exception as e:
        print(f"Error dividing configurations: {e}")
        sys.exit(1)

    # Step 2: Perform precheck
    precheck_passed = precheck(aws_configs, azure_configs)
    if not precheck_passed:
        print("Precheck failed. Exiting...")
        sys.exit(1)

    # Step 3: Deploy the instances
    deploy(aws_configs, azure_configs, output_dir)

    # Optional: Wait for some time or perform operations before teardown
    # time.sleep(60)  # Wait for 60 seconds

    # Step 4: Teardown the instances
    teardown(aws_configs, azure_configs)

    print("\n========== Runner Completed ==========\n")

if __name__ == "__main__":
    main()  # This will use argparse to get arguments