#!/usr/bin/env bash
# Stops everything that costs money, in the right order.
# Used by the "teardown" workflow. You can also run it by hand in AWS CloudShell:
#     bash scripts/aws/teardown.sh
# The baseline stack (evidence bucket, roles, secrets) is NOT touched.
set -uo pipefail
export AWS_DEFAULT_REGION=ap-southeast-2
export AWS_PAGER=""
CLUSTER=custodian-eks
NS=custodian

stack_exists() { aws cloudformation describe-stacks --stack-name "$1" >/dev/null 2>&1; }

echo "== 1/5  Delete the HTTPS front door (CloudFront). This can take 5-15 minutes."
if stack_exists custodian-edge; then
  echo "Deleting custodian-edge stack..."
  aws cloudformation delete-stack --stack-name custodian-edge || true
  aws cloudformation wait stack-delete-complete --stack-name custodian-edge 2>/dev/null || true
else
  echo "no edge stack, skipping"
fi

# Locate the VPC ID before stack deletion
VPC=""
if stack_exists custodian-cluster; then
  VPC=$(aws cloudformation describe-stacks --stack-name custodian-cluster \
        --query "Stacks[0].Outputs[?OutputKey=='VpcId'].OutputValue" --output text 2>/dev/null || true)
fi
if [ -z "$VPC" ] || [ "$VPC" = "None" ]; then
  VPC=$(aws ec2 describe-vpcs --filters Name=tag:Name,Values=custodian-vpc --query "Vpcs[0].VpcId" --output text 2>/dev/null || true)
fi

echo "== 2/5  Delete Kubernetes services and cloud load balancers"
if aws eks update-kubeconfig --name "$CLUSTER" >/dev/null 2>&1; then
  kubectl delete svc --all -n "$NS" --timeout=60s 2>/dev/null || true
  kubectl delete deployment --all -n "$NS" --timeout=60s 2>/dev/null || true
fi

# If VPC is known, proactively delete any load balancers inside it
if [ -n "$VPC" ] && [ "$VPC" != "None" ]; then
  echo "Sweeping all Classic and Application Load Balancers in $VPC..."
  for lb in $(aws elb describe-load-balancers --query "LoadBalancerDescriptions[?VPCId=='$VPC'].LoadBalancerName" --output text 2>/dev/null || true); do
    echo "  Deleting Classic ELB: $lb"
    aws elb delete-load-balancer --load-balancer-name "$lb" || true
  done
  for lb_arn in $(aws elbv2 describe-load-balancers --query "LoadBalancers[?VpcId=='$VPC'].LoadBalancerArn" --output text 2>/dev/null || true); do
    echo "  Deleting ELBv2: $lb_arn"
    aws elbv2 delete-load-balancer --load-balancer-arn "$lb_arn" || true
  done
fi

echo "== 3/5  Delete the cluster stack (EKS + nodes + network)"
if stack_exists custodian-cluster; then
  echo "Requesting CloudFormation deletion of custodian-cluster..."
  aws cloudformation delete-stack --stack-name custodian-cluster

  echo "Waiting for stack deletion to complete (or fail)..."
  if ! aws cloudformation wait stack-delete-complete --stack-name custodian-cluster 2>/dev/null; then
    echo "Stack deletion halted by dependency (e.g. Subnet/VPC). Initiating autonomous dependency clearance..."
    
    # 1. Force detach and delete all ENIs in the VPC
    if [ -n "$VPC" ] && [ "$VPC" != "None" ]; then
      echo "Scanning for stubborn ENIs in $VPC..."
      for eni in $(aws ec2 describe-network-interfaces --filters Name=vpc-id,Values="$VPC" \
                  --query "NetworkInterfaces[*].NetworkInterfaceId" --output text 2>/dev/null || true); do
        echo "  Force detaching & deleting ENI: $eni"
        ATT=$(aws ec2 describe-network-interfaces --network-interface-ids "$eni" \
              --query "NetworkInterfaces[0].Attachment.AttachmentId" --output text 2>/dev/null || true)
        if [ -n "$ATT" ] && [ "$ATT" != "None" ]; then
          aws ec2 detach-network-interface --attachment-id "$ATT" --force 2>/dev/null || true
          sleep 3
        fi
        aws ec2 delete-network-interface --network-interface-id "$eni" 2>/dev/null || true
      done

      # 2. Delete non-default Security Groups in the VPC
      for sg in $(aws ec2 describe-security-groups --filters Name=vpc-id,Values="$VPC" \
                  --query "SecurityGroups[?GroupName!='default'].GroupId" --output text 2>/dev/null || true); do
        echo "  Deleting security group: $sg"
        aws ec2 delete-security-group --group-id "$sg" 2>/dev/null || true
      done
    fi

    # 3. Identify failed resources and unblock CloudFormation by retaining them
    FAILED_RES=$(aws cloudformation describe-stack-events --stack-name custodian-cluster \
      --query "StackEvents[?ResourceStatus=='DELETE_FAILED'].LogicalResourceId" --output text 2>/dev/null | tr '\t' '\n' | sort -u | tr '\n' ' ')
    
    if [ -n "$FAILED_RES" ] && [ "$FAILED_RES" != " " ]; then
      echo "Unblocking CloudFormation by retaining stubborn resources: $FAILED_RES"
      aws cloudformation delete-stack --stack-name custodian-cluster --retain-resources $FAILED_RES 2>/dev/null || true
      aws cloudformation wait stack-delete-complete --stack-name custodian-cluster 2>/dev/null || true
    fi
  fi
else
  echo "no cluster stack, skipping"
fi

echo "== 4/5  Autonomous VPC & Subnet Sweeper (Ensures 100% clean teardown)"
if [ -n "$VPC" ] && [ "$VPC" != "None" ]; then
  if aws ec2 describe-vpcs --vpc-ids "$VPC" >/dev/null 2>&1; then
    echo "VPC $VPC still detected. Dismantling all remaining components directly..."
    
    # Sweep any remaining ENIs
    for eni in $(aws ec2 describe-network-interfaces --filters Name=vpc-id,Values="$VPC" \
                --query "NetworkInterfaces[*].NetworkInterfaceId" --output text 2>/dev/null || true); do
      echo "  Detaching & deleting ENI: $eni"
      ATT=$(aws ec2 describe-network-interfaces --network-interface-ids "$eni" \
            --query "NetworkInterfaces[0].Attachment.AttachmentId" --output text 2>/dev/null || true)
      if [ -n "$ATT" ] && [ "$ATT" != "None" ]; then
        aws ec2 detach-network-interface --attachment-id "$ATT" --force 2>/dev/null || true
        sleep 2
      fi
      aws ec2 delete-network-interface --network-interface-id "$eni" 2>/dev/null || true
    done

    # Delete all subnets in the VPC with retry (in case EKS is finishing ENI release)
    for sub in $(aws ec2 describe-subnets --filters Name=vpc-id,Values="$VPC" \
                --query "Subnets[*].SubnetId" --output text 2>/dev/null || true); do
      echo "  Deleting Subnet: $sub"
      for attempt in $(seq 1 15); do
        if aws ec2 delete-subnet --subnet-id "$sub" 2>/dev/null; then
          echo "    Subnet $sub deleted."
          break
        fi
        sleep 4
      done
    done

    # Detach & delete internet gateways
    for igw in $(aws ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values="$VPC" \
                --query "InternetGateways[*].InternetGatewayId" --output text 2>/dev/null || true); do
      echo "  Detaching & deleting IGW: $igw"
      aws ec2 detach-internet-gateway --internet-gateway-id "$igw" --vpc-id "$VPC" 2>/dev/null || true
      aws ec2 delete-internet-gateway --internet-gateway-id "$igw" 2>/dev/null || true
    done

    # Delete custom route tables
    for rtb in $(aws ec2 describe-route-tables --filters Name=vpc-id,Values="$VPC" \
                --query "RouteTables[?Associations[0].Main!=true].RouteTableId" --output text 2>/dev/null || true); do
      echo "  Deleting Route Table: $rtb"
      aws ec2 delete-route-table --route-table-id "$rtb" 2>/dev/null || true
    done

    # Delete remaining custom security groups
    for sg in $(aws ec2 describe-security-groups --filters Name=vpc-id,Values="$VPC" \
                --query "SecurityGroups[?GroupName!='default'].GroupId" --output text 2>/dev/null || true); do
      echo "  Deleting Security Group: $sg"
      aws ec2 delete-security-group --group-id "$sg" 2>/dev/null || true
    done

    # Delete the VPC itself with retry
    echo "  Deleting VPC: $VPC"
    for attempt in $(seq 1 10); do
      if aws ec2 delete-vpc --vpc-id "$VPC" 2>/dev/null; then
        echo "VPC $VPC successfully eliminated."
        break
      fi
      sleep 4
    done
  fi
fi

echo "== 5/5  Leftover verification check"
bash "$(dirname "$0")/leftovers.sh"
