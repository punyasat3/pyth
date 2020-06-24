#! /usr/local/bin/python3

import os
import threading
import boto3
import sys
import logging
from time import sleep
from config import *
#log file
logging.basicConfig(filename='elb.log', level=int(Level),
                    format='%(asctime)s:%(levelname)s:%(message)s',filemode='w')

#Credentials Validation
sts = boto3.client('sts',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
try:
    account_id = sts.get_caller_identity()["Account"]
    sts.get_caller_identity()
    logging.info(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name : --- instance: --- Credentials are valid.")
except:
    logging.info(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name : --- instance: --- Credentials invalid. \nPlease Provide Valid Credentials in config file.\nThanks")
    sys.exit(0)

#Checks
if len(regions)==0:
    logging.info(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name : --- instance: --- Please Enter Atleast One region in Config file.")
    sys.exit(2)
if len(ec2_tag_names)==0:
    logging.info(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name : --- instance: --- Please Enter Atleast One EC2 Tag name in Config file.")
    sys.exit(3)

#Region Validation & matching instances  & running instances
client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
regions_list = [region['RegionName'] for region in client.describe_regions()['Regions']]
running_list=[]
instance_ids_with_matching_tags=[]
for region in regions:
    if region not in regions_list:
        logging.info(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name :" +str(region)+"No Such Region Found.\nPlease Enter Valid Region in config file.\nThanks")
        logging.debug(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name :" +str(region)+"please select mention proper region in provided by AWS")
        sys.exit(1)
    client1 = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    response = client1.describe_instances(Filters=ec2_tag_names)
    for Instances in response['Reservations']:
        for Initid in Instances['Instances']:
            instance_ids_with_matching_tags.append(Initid['InstanceId'])
    response1 = client1.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}])
    for Instances in response1['Reservations']:
        for Initid in Instances['Instances']:
          if Initid['InstanceId'] in instance_ids_with_matching_tags:
             running_list.append(Initid['InstanceId'])

if len(running_list)==0:
    logging.info(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name : --- instance: --- No matching instances found in this tagging creteria. \ntag name is false.\nThanks")
    sys.exit(4)



logging.info("script name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name : --- instance: --- Trying to Deregister Instances...")

# Deregister process
instance_list=[]
def deregisterforregion(region):
    elb_client = boto3.client('elb',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    elb_response=elb_client.describe_load_balancers()
    regionallelbs=elb_response['LoadBalancerDescriptions']

    def deregisterforelb(loadbalancer):
        count=0
        elb_instancelist=[]
        for initid in loadbalancer['Instances']:
            if initid['InstanceId']  in running_list:
               elb_instancelist.append(initid['InstanceId'])
               instance_list.append(initid['InstanceId'])
       #elblist for appending all matching instances in specific elb
       #instance list for appending all instances in all elbs
               count=len(elb_instancelist)
               if count>1:
                  elb=str(loadbalancer['LoadBalancerName'])
                  elb_response1 = elb_client.deregister_instances_from_load_balancer(LoadBalancerName=elb,Instances=[{'InstanceId': initid['InstanceId']}])
                  #sleep(3)
                  if initid['InstanceId'] not  in elb_response1:
                      logging.warning(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name :" +str(region)+"instance "+str(initid['InstanceId'])+" is Deregistered from ELB named "+str(elb)+" in region "+str(region))
                      count=count-1
                  else :
                       logging.warning(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name :" +str(region)+"instance "+str(initid['InstanceId'])+" is not able to  Deregistered from ELB named "+str(elb)+" in region "+str(region))


    for loadbalancer in regionallelbs:
        p = threading.Thread(target = deregisterforelb, args=(loadbalancer,)).start()


for region in regions:
    t = threading.Thread(target = deregisterforregion, args=(region,)).start()

# if tag instances not in elb or already deregister
if len(instance_list)==0 :
    logging.info(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" Nothing to Deregister.\nThanks.")
