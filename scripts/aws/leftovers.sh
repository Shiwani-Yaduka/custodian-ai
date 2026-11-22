#!/usr/bin/env bash
# Lists everything that could still be costing money. READ-ONLY: it deletes nothing.
# Run it in AWS CloudShell, or let the teardown workflow run it.
export AWS_DEFAULT_REGION=us-east-1
export AWS_PAGER=""

echo "--- CloudFormation stacks (expect only: custodian-baseline)"
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE ROLLBACK_COMPLETE CREATE_FAILED DELETE_FAILED \
  --query "StackSummaries[].[StackName,StackStatus]" --output text

echo "--- EKS clusters (expect none)"
aws eks list-clusters --query "clusters" --output text

echo "--- EC2 instances (expect none)"
aws ec2 describe-instances \
  --filters Name=instance-state-name,Values=pending,running,stopping,stopped \
  --query "Reservations[].Instances[].[InstanceId,InstanceType,State.Name]" --output text

echo "--- Classic load balancers (expect none)"
aws elb describe-load-balancers --query "LoadBalancerDescriptions[].LoadBalancerName" --output text

echo "--- Application/Network load balancers (expect none)"
aws elbv2 describe-load-balancers --query "LoadBalancers[].LoadBalancerName" --output text

echo "--- NAT gateways (expect none)"
aws ec2 describe-nat-gateways --filter Name=state,Values=pending,available \
  --query "NatGateways[].NatGatewayId" --output text

echo "--- Elastic IP addresses (expect none)"
aws ec2 describe-addresses --query "Addresses[].PublicIp" --output text

echo "--- EBS disks (expect none)"
aws ec2 describe-volumes --query "Volumes[].[VolumeId,Size,State]" --output text

echo "--- CloudFront distributions (expect none)"
aws cloudfront list-distributions --query "DistributionList.Items[].[Id,Status,Comment]" --output text

echo "--- Done. Anything listed above that you do not expect: delete it in the console."
