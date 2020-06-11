#! /usr/local/bin/python3

import os
import boto3
import sys
import logging
from config import *

default_region="ap-south-1"
#Credentials Validation
sts = boto3.client('sts',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
try:
    sts.get_caller_identity()
    print("Credentials are valid.")
except:
    print("Credentials invalid. Please Provide Valid Credentials in config file.Thanks")
    sys.exit(0)

#Region Validation
client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
regions_list = [region['RegionName'] for region in client.describe_regions()['Regions']]
for region in regions:
    if region not in regions_list:
        print("{region} No Such Region Found.Please Enter Valid Region in config file.Thanks")
        sys.exit(1)

#Checks
if len(regions)==0:
    print("Please Enter Atleast One region in Config file.")
    sys.exit(2)
if len(ec2_tag_names)==0:
    print("Please Enter Atleast One EC2 Tag name in Config file.")
    sys.exit(3)

instance_ids_with_matching_tags=[]
for region in regions:
    client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    response = client.describe_instances(Filters=ec2_tag_names)
    for d in response['Reservations']:
        for z in d['Instances']:
            instance_ids_with_matching_tags.append(z['InstanceId'])
if len(instance_ids_with_matching_tags)==0:
    print("No matching instances found in this tagging creteria. Thanks")
    sys.exit(4)
# print(instance_ids_with_matching_tags)

elb_list=[]
instance_list=[]
# Fetching all available ELBs names from this account.

for region in regions:
    client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    response = client.describe_instances(Filters=ec2_tag_names)
    for d in response['Reservations']:
        for z in d['Instances']:
            instance_ids_with_matching_tags.append(z['InstanceId'])
if len(instance_ids_with_matching_tags)==0:
    print("No matching instances found in this tagging creteria. Thanks")
    sys.exit(4)
# print(instance_ids_with_matching_tags)

elb_list=[]
instance_list=[]
# Fetching all available ELBs names from this account.
for region in regions:
    elb_client = boto3.client('elb',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    elb_response = elb_client.describe_load_balancers()
    a=elb_response['LoadBalancerDescriptions']
    for z in a:
        elb_list.append(z['LoadBalancerName'])
elb_names=elb_list
print("Trying to Deregister Instances...")

deregistered_instances=[]
instance_list=[]
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
                    client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
                    response = client.describe_instances(Filters=ec2_tag_names)
                    for d in response['Reservations']:
                        for z in d['Instances']:
                            if t['InstanceId']==z['InstanceId']:
                                instance_list.append(t['InstanceId'])
                                for elb in new_list:
                                    elb_response = elb_client.deregister_instances_from_load_balancer(LoadBalancerName=elb,Instances=[{'InstanceId': t['InstanceId']}])
                                    print(t['InstanceId'],"is Deregistered from ELB named ",elb)
# print(list(dict.fromkeys(instance_list)))
if len(instance_list)==0 :
    print("Nothing to DeregisterThanks.")
