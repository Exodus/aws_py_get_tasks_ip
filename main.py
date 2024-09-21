import boto3

# Initialize boto3 clients
ecs_client = boto3.client('ecs')
ec2_client = boto3.client('ec2')

def get_clusters():
    """Retrieve all ECS clusters in the region."""
    cluster_arns = []
    paginator = ecs_client.get_paginator('list_clusters')
    for page in paginator.paginate():
        cluster_arns.extend(page['clusterArns'])
    return cluster_arns

def get_services(cluster_arn):
    """Retrieve all services in the given cluster."""
    service_arns = []
    paginator = ecs_client.get_paginator('list_services')
    for page in paginator.paginate(cluster=cluster_arn):
        service_arns.extend(page['serviceArns'])
    return service_arns

def get_tasks(cluster_arn, service_arn):
    """Retrieve running tasks for a given service."""
    task_arns = []
    paginator = ecs_client.get_paginator('list_tasks')
    for page in paginator.paginate(cluster=cluster_arn, serviceName=service_arn):
        task_arns.extend(page['taskArns'])
    return task_arns

def describe_tasks(cluster_arn, task_arns):
    """Describe the tasks to get ENI details."""
    if not task_arns:
        return []
    
    response = ecs_client.describe_tasks(cluster=cluster_arn, tasks=task_arns)
    tasks_info = []
    
    for task in response['tasks']:
        task_info = {
            'taskArn': task['taskArn'],
            'taskDefinitionArn': task['taskDefinitionArn'],
            'networkInterfaces': []
        }
        
        # Extract ENI ID if network mode is 'awsvpc'
        for attachment in task.get('attachments', []):
            for detail in attachment['details']:
                if detail['name'] == 'networkInterfaceId':
                    task_info['networkInterfaces'].append(detail['value'])
        
        tasks_info.append(task_info)
    
    return tasks_info

def get_ips_from_enis(eni_ids):
    """Retrieve private IP addresses for the provided ENI IDs."""
    if not eni_ids:
        return []
    
    response = ec2_client.describe_network_interfaces(NetworkInterfaceIds=eni_ids)
    
    ips = [eni['PrivateIpAddress'] for eni in response['NetworkInterfaces']]
    return ips

def main():
    # Get all clusters
    clusters = get_clusters()
    
    for cluster_arn in clusters:
        print(f"Cluster: {cluster_arn}")
        
        # Get all services in the cluster
        services = get_services(cluster_arn)
        
        for service_arn in services:
            print(f"  Service: {service_arn}")
            
            # Get all tasks for the service
            tasks = get_tasks(cluster_arn, service_arn)
            
            if not tasks:
                print("    No tasks found.")
                continue
            
            # Describe tasks to get ENI IDs
            tasks_info = describe_tasks(cluster_arn, tasks)
            
            for task_info in tasks_info:
                print(f"    Task Definition: {task_info['taskDefinitionArn']}")
                
                # Get IPs for the ENIs attached to the task
                if task_info['networkInterfaces']:
                    ips = get_ips_from_enis(task_info['networkInterfaces'])
                    print(f"      IP Addresses: {', '.join(ips)}")
                else:
                    print("      No ENIs found (non-awsvpc network mode).")

if __name__ == "__main__":
    main()
