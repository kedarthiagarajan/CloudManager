import yaml

def divide_configs(config_file_path):
    with open(config_file_path, 'r') as file:
        config = yaml.safe_load(file)

    aws_configs = []
    azure_configs = []

    for provider in config['Config']['cloud_providers']:
        if provider['name'].lower() == 'aws':
            aws_configs.append(provider)
        elif provider['name'].lower() == 'azure':
            azure_configs.append(provider)

    return aws_configs, azure_configs

def get_security_group_with_ssh(ec2_client, vpc_id):
    """Find a security group in the specified VPC that allows SSH access."""
    sg_response = ec2_client.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    for sg in sg_response['SecurityGroups']:
        for rule in sg['IpPermissions']:
            if rule.get('FromPort') == 22 and rule.get('ToPort') == 22:
                for ip_range in rule.get('IpRanges', []):
                    if ip_range.get('CidrIp') == '0.0.0.0/0':
                        return [sg['GroupId']]
    
    raise ValueError("No security group allowing SSH access found in the specified VPC.")

def dump_config_to_yaml(config, output_path):
    """
    Dumps the given configuration dictionary to a YAML file.

    :param config: The configuration dictionary to be dumped.
    :param output_path: The path where the YAML file should be saved.
    """
    try:
        with open(output_path, 'w') as yaml_file:
            yaml.dump(config, yaml_file, default_flow_style=False)
        print(f"Configuration successfully dumped to {output_path}")
    except Exception as e:
        print(f"Error dumping configuration to YAML: {e}")