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
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- Credentials are valid.")
except:
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- Credentials invalid. \nPlease Provide Valid Credentials in config file.\nThanks")
    sys.exit(0)

#Checks
if len(regions)==0:
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- Please Enter Atleast One region in Config file.")
    sys.exit(2)
if len(ec2_tag_names)==0:
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- Please Enter Atleast One EC2 Tag name in Config file.")
    sys.exit(3)

#Region Validation & filtering  matching instances running instances
client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
regions_list = [region['RegionName'] for region in client.describe_regions()['Regions']]
instance_ids_with_matching_tags=[]
instance_list=[]
permanent_running_list=[]

for region in regions:
    temporary_running_list=[]
    if region not in regions_list:
        logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+"No Such Region Found.\nPlease Enter Valid Region in config file.\nThanks")
        logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+"please select mention proper region in provided by AWS")
        sys.exit(1)
    client1 = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    response1 = client1.describe_instances(Filters=ec2_tag_names)
    for Instances in response1['Reservations']:
        for Initid in Instances['Instances']:
            instance_ids_with_matching_tags.append(Initid['InstanceId'])
    response2 = client1.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    for Instances in response2['Reservations']:
        for Initid in Instances['Instances']:
          if Initid['InstanceId'] in instance_ids_with_matching_tags:
             temporary_running_list.append(Initid['InstanceId'])

    #client2 = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    #checking whether same role tag having two instances
    for i1 in temporary_running_list:
      count=0
      response3 = client1.describe_instances(InstanceIds=[i1])
      for Instances1 in response3['Reservations']:
        for tag in Instances1['Instances']:
          for key1 in tag['Tags']:
            if key1['Key']=="role":
              for i2 in temporary_running_list:
                response4 = client1.describe_instances(InstanceIds=[i2])
                for instances2 in response4['Reservations']:
                  for tag in instances2['Instances']:
                    for key2 in tag['Tags']:
                      if key2['Key']=="role" and  key1['Value']==key2['Value']:
                         count=count+1

      #if role tag having only single instance it will append and deregister
      if count==1:
         permanent_running_list.append(i1)
      #if more than one instance having role tag its won't deregister and  it will push log with instance id
      if count>1:
         logging.error(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+" More the 1 instance is tagged for deregistration for the same role "+str(i1))




logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- Trying to Deregister Instances...")

# Deregister process
def deregisterforregion(region):
    elb_client = boto3.client('elbv2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    waiter = elb_client.get_waiter('target_deregistered')
    elb_response=elb_client.describe_load_balancers()
    inregionallelbs=elb_response['LoadBalancers']
    def deregisterforelb(loadbalancerarn):
      #in every elb taking instance id and if id matches with running_list its simply deregister
      elb_list=[]
      count2=0
      response5 = elb_client.describe_listeners(LoadBalancerArn=(str(loadbalancerarn['LoadBalancerArn'])),)
      for defaultaction in response5['Listeners']:
        for targetgrouparn in defaultaction['DefaultActions'] :
          response6 = elb_client.describe_target_health(TargetGroupArn=(str(targetgrouparn['TargetGroupArn'])),)
          for target in response6['TargetHealthDescriptions']:
            elb_list.append(target['Target']['Id'])
            count2=len(elb_list)
          for target in response6['TargetHealthDescriptions']:
            if count2>1:
              if  target['Target']['Id'] in permanent_running_list:
                try:
                  response8 = elb_client.deregister_targets(TargetGroupArn=(str(targetgrouparn['TargetGroupArn'])),Targets=[{'Id': target['Target']['Id'],},],)
                  response9=waiter.wait(TargetGroupArn=(str(targetgrouparn['TargetGroupArn'])),Targets=[{'Id': target['Target']['Id'],'Port': 80,},],WaiterConfig={'Delay': 30,'MaxAttempts': 12})
                  logging.warning(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+"instance Id with "+str(target['Target']['Id'])+" is Deregistered from ELB named "+str(loadbalancerarn['LoadBalancerName'])+" in region "+str(region))
                  count=count2-1
                except:
                  logging.warning(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+"instance Id with "+str(target['Target']['Id'])+" is Not Deregistered from ELB named "+str(loadbalancerarn['LoadBalancerName'])+" in region "+str(region)+"Time out Try again ")
    #from here only multiple threads will create and calls deregisaterforelb function
    for loadbalancerarn in inregionallelbs:
        p = threading.Thread(target = deregisterforelb, args=(loadbalancerarn,)).start()
#from here only multiple threads will create and calls deregisaterforregion function
for region in regions:
    t = threading.Thread(target = deregisterforregion, args=(region,)).start()

# if tag instances not in elb or already deregister
if len(instance_list)==0:
  logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" Nothing to Deregister.\nThanks.")
