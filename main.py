#! /usr/local/bin/python3

import os
import threading
import boto3
import sys
import logging
from time import sleep
from config import *
#log file
logging.basicConfig(filename='elb.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s',filemode='w')

default_region="ap-south-1"

#Credentials Validation
sts = boto3.client('sts',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
try:
    sts.get_caller_identity()
    logging.info("Credentials are valid.")
except:
    logging.info("Credentials invalid. \nPlease Provide Valid Credentials in config file.\nThanks")
    sys.exit(0)

#Checks
if len(regions)==0:
    logging.info("Please Enter Atleast One region in Config file.")
    sys.exit(2)
if len(ec2_tag_names)==0:
    logging.info("Please Enter Atleast One EC2 Tag name in Config file.")
    sys.exit(3)

#Region Validation & matching instances  & running instances
client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
regions_list = [region['RegionName'] for region in client.describe_regions()['Regions']]
running_list=[]
instance_ids_with_matching_tags=[]
for region in regions:
    if region not in regions_list:
        logging.info(region,"No Such Region Found.\nPlease Enter Valid Region in config file.\nThanks")
        logging.debug("please select mention proper region in provided by AWS")
        sys.exit(1)
    client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    response = client.describe_instances(Filters=ec2_tag_names)
    for d in response['Reservations']:
        for z in d['Instances']:
            instance_ids_with_matching_tags.append(z['InstanceId'])
    client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    response1 = client.describe_instances()
    #print(response1)
    response = client.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}])
    for d in response['Reservations']:
        for z in d['Instances']:
             running_list.append(z['InstanceId'])


if len(instance_ids_with_matching_tags)==0:
    logging.info("No matching instances found in this tagging creteria. \ntag name is false.\nThanks")
    sys.exit(4)


logging.info("Trying to Deregister Instances...")

# Deregister process
instance_list=[]
def deregister(region):
    elb_client = boto3.client('elb',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    elb_response=elb_client.describe_load_balancers()
    a=elb_response['LoadBalancerDescriptions']
    def derelb(z):
        for t in z['Instances']:
            if t['InstanceId'] in instance_ids_with_matching_tags:
              if t['InstanceId'] not in running_list:

                instance_list.append(t['InstanceId'])
                elb=str(z['LoadBalancerName'])

                elb_response1 = elb_client.deregister_instances_from_load_balancer(LoadBalancerName=elb,Instances=[{'InstanceId': t['InstanceId']}])
                logging.info(" Iam Sleeping for 3 sec")
                #sleep(3)
                if t['InstanceId'] not  in elb_response1:
                    logging.warning(str(t['InstanceId'])+" is Deregistered from ELB named "+str(elb)+" in region "+str(region))
                else :
                    logging.warning(str(t['InstanceId'])+" is Not able to  Deregistered from ELB named "+str(elb)+" in region "+str(region)+"wait for some time and try again")


    for z in a :
        p = threading.Thread(target = derelb, args=(z,)).start()


for region in regions:
    t = threading.Thread(target = deregister, args=(region,)).start()

# if tag instances not in elb or already deregister
if len(instance_list)==0 :
    logging.info("Nothing to Deregister.\nThanks.")
