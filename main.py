#! /usr/local/bin/python3

import os
import boto3
import sys
from config import *

default_region="ap-south-1"
#Credentials Validation
sts = boto3.client('sts',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
try:
    sts.get_caller_identity()
    print("Credentials are valid.")
except:
    print("Credentials invalid. Please Provide Valid Credentials.")
    sys.exit(0)

#Region Validation
client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
regions_list = [region['RegionName'] for region in client.describe_regions()['Regions']]
for region in regions:
    if region not in regions_list:
        print(" No Such Region Found.")
        sys.exit(1)

#Checks
if len(regions)==0:
    print("Please Enter Atleast One region in Config file.")
    sys.exit(2)
if len(ec2_tag_name)==0:
    print("Please Enter Atleast One EC2 Tag Name in Config file.")
    sys.exit(3)
if len(availablity_zone)==0:
    print("Please Enter Atleast One AvailabilityZone in Config file.")
    sys.exit(4)
if len(elb_names)==0:
    print("Please Enter Atleast One ELB Name in Config file.")
    sys.exit(5)

elb_list=[]
instance_list=[]
# Fetching all available ELBs names from this account.
for region in regions:
    elb_client = boto3.client('elb',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    elb_response = elb_client.describe_load_balancers()
    a=elb_response['LoadBalancerDescriptions']
    for z in a:
        elb_list.append(z['LoadBalancerName'])

# ELB name Validation
for elb_name in elb_names:
    if elb_name not in elb_list:
        print(" ELB not Found in following regions ")
        sys.exit(6)

print("Trying to Deregister Instances")

deregistered_instances=[]
for region in regions:
    new_list=[]
    elb_client = boto3.client('elb',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    elb_response=elb_client.describe_load_balancers()
    a=elb_response['LoadBalancerDescriptions']
    for z in a:
        if z['LoadBalancerName'] in elb_names:
            new_list.append(z['LoadBalancerName'])
            elb_response1=elb_client.describe_load_balancers(LoadBalancerNames=new_list)
            insta=elb_response1['LoadBalancerDescriptions']
            for f in insta:
                for t in f['Instances']:
                    instance_list.append(t['InstanceId'])
                    client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
                    response = client.describe_instances(Filters=[{'Name': 'instance-id','Values': instance_list}])
                    for d in response['Reservations']:
                        for z in d['Instances']:
                            tag=z['Tags'][0]['Value']
                            if z['Placement']['AvailabilityZone'] in availablity_zone and z['Tags'][0]['Value'] in ec2_tag_name:
                                deregistered_instances.append(z['InstanceId'])
                                # Deregistering Instances from ELB
                                for elb in new_list:
                                    elb_response = elb_client.deregister_instances_from_load_balancer(LoadBalancerName=elb,Instances=[{'InstanceId': z['InstanceId']}])
if  len(deregistered_instances)==0 :
    print("Nothing to Deregister")
else:
    print(" removed from ELB")
                                      
