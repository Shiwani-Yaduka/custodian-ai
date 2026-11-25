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

delete_stack() {
  aws cloudformation delete-stack --stack-name "$1"
  aws cloudformation wait stack-delete-complete --stack-name "$1"
}

echo "== 1/4  Delete the HTTPS front door (CloudFront). This can take 5-15 minutes."
if stack_exists custodian-edge; then
  delete_stack custodian-edge || echo "WARNING: edge stack did not delete cleanly, check the console."
else
  echo "no edge stack, skipping"
fi

VPC=""
if stack_exists custodian-cluster; then
  VPC=$(aws cloudformation describe-stacks --stack-name custodian-cluster \
        --query "Stacks[0].Outputs[?OutputKey=='VpcId'].OutputValue" --output text 2>/dev/null || true)

  echo "== 2/4  Delete the Kubernetes load balancer (CloudFormation does not know about it)"
  if aws eks update-kubeconfig --name "$CLUSTER" >/dev/null 2>&1; then
    kubectl delete svc --all -n "$NS" --timeout=120s || true
  else
    echo "could not reach the cluster, will rely on the sweep below"
  fi

  if [ -n "$VPC" ] && [ "$VPC" != "None" ]; then
    echo "waiting for load balancers in $VPC to disappear..."
    for i in $(seq 1 30); do
      LBS=$(aws elb describe-load-balancers \
            --query "LoadBalancerDescriptions[?VPCId=='$VPC'].LoadBalancerName" --output text 2>/dev/null || true)
      [ -z "$LBS" ] && break
      echo "  still there: $LBS"
      # If the service delete did not remove it, delete it directly.
      if [ "$i" -ge 6 ]; then
        for lb in $LBS; do aws elb delete-load-balancer --load-balancer-name "$lb" || true; done
      fi
      sleep 10
    done
    sleep 20   # give AWS time to remove the load balancer's security group
  fi

  echo "== 3/4  Delete the cluster stack (EKS + nodes + network). This takes 10-15 minutes."
  if ! delete_stack custodian-cluster; then
    echo "First attempt failed. Removing leftover load-balancer security groups and retrying..."
    if [ -n "$VPC" ] && [ "$VPC" != "None" ]; then
      for sg in $(aws ec2 describe-security-groups --filters Name=vpc-id,Values="$VPC" \
                  --query "SecurityGroups[?starts_with(GroupName,'k8s-elb-')].GroupId" --output text); do
        aws ec2 delete-security-group --group-id "$sg" || true
      done
    fi
    delete_stack custodian-cluster || echo "ERROR: cluster stack still not deleted. Open the CloudFormation console and look at the Events tab."
  fi
else
  echo "== 2/4 and 3/4  no cluster stack, skipping"
fi

echo "== 4/4  Leftover check"
bash "$(dirname "$0")/leftovers.sh"
