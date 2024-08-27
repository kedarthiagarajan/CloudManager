import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from cloudmanager.utils import divide_configs, get_security_group_with_ssh


def check_aws_configs(aws_configs):
    error_code = 0

    for aws_config in aws_configs:
        try:
            # Extract credentials
            access_key = aws_config['credentials']['access_key']
            secret_key = aws_config['credentials']['secret_key']

            for vm_config in aws_config['vm_configs']:
                region = vm_config['region']
                instance_type = vm_config['instance_type']
                vpc_id = vm_config.get('vpc_id', None)
                subnet_id = vm_config.get('subnet_id', None)
                security_group_ids = vm_config.get('security_group_ids', [])
                key_pair_name = vm_config.get('key_pair_name', None)

                # Create an EC2 client for the specific region
                ec2_client = boto3.client(
                    'ec2',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )

                # Check if the region is available
                try:
                    regions_response = ec2_client.describe_regions(RegionNames=[region])
                    if not regions_response['Regions']:
                        print(f"Error: Region '{region}' is not available.")
                        error_code = 1
                        continue

                except ClientError as e:
                    print(f"Error: Region '{region}' is not available. {e}")
                    error_code = 1
                    continue

                # Check if the instance type is available in the region
                try:
                    response = ec2_client.describe_instance_type_offerings(
                        LocationType='region',
                        Filters=[{'Name': 'instance-type', 'Values': [instance_type]}]
                    )
                    if not response['InstanceTypeOfferings']:
                        print(f"Error: Instance type '{instance_type}' is not available in region '{region}'.")
                        error_code = 1

                except ClientError as e:
                    print(f"Error: Unable to verify instance type '{instance_type}' in region '{region}'. {e}")
                    error_code = 1
                    
                if 'vpc_id' in vm_config:
                    vpc_id = vm_config['vpc_id']
                else:
                    vpc_response = ec2_client.describe_vpcs()
                    vpc_id = vpc_response['Vpcs'][0]['VpcId']  # Assuming the first VPC found
                # Check for at least one Security Group if not provided
                if not security_group_ids:
                    try:
                        security_group_ids = get_security_group_with_ssh(ec2_client, vpc_id)
                        if not security_group_ids:
                            print(f"Error: No Security Groups found in region '{region}' that allow SSH.")
                            error_code = 1
                    except ClientError as e:
                        print(f"Error: Unable to retrieve Security Groups in region '{region}'. {e}")
                        error_code = 1

                # Check if the Key Pair exists
                if not key_pair_name:
                    try:
                        key_pair_response = ec2_client.describe_key_pairs()
                        if not key_pair_response['KeyPairs']:
                            print(f"Error: No Key Pairs found in region '{region}'.")
                            error_code = 1
                        else:
                            key_pair_name = key_pair_response['KeyPairs'][0]['KeyName']
                    except ClientError as e:
                        print(f"Error: Unable to retrieve Key Pairs in region '{region}'. {e}")
                        error_code = 1

        except (NoCredentialsError, PartialCredentialsError) as e:
            print(f"Error: AWS credentials are invalid or incomplete. {e}")
            error_code = 1
            break

    return error_code

# Example usage
if __name__ == "__main__":
    aws_configs, azure_configs = divide_configs('../config.yaml')
    aws_error_code = check_aws_configs(aws_configs)
    if aws_error_code == 0:
        print("All AWS configurations are valid.")
    else:
        print("There were errors in AWS configurations.")
