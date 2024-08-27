import boto3
from botocore.exceptions import ClientError

def terminate_aws_instance(region, instance_id):
    """Terminate a specific AWS EC2 instance by instance ID."""
    ec2_client = boto3.client('ec2', region_name=region)
    
    try:
        # Terminate the instance
        response = ec2_client.terminate_instances(InstanceIds=[instance_id])
        print(f"Initiated termination for instance: {instance_id}")
        
        # Check the status of the instance termination
        for instance in response['TerminatingInstances']:
            current_state = instance['CurrentState']['Name']
            print(f"Instance {instance['InstanceId']} is now in state: {current_state}")
            
        return True

    except ClientError as e:
        print(f"Error terminating instance {instance_id}: {e}")
        return False

# Example usage
if __name__ == "__main__":
    region = "us-east-1"  # Replace with your desired region
    instance_id = "i-0123456789abcdef0"  # Replace with your instance ID

    success = terminate_aws_instance(region, instance_id)
    if success:
        print(f"Instance {instance_id} successfully terminated.")
    else:
        print(f"Failed to terminate instance {instance_id}.")
