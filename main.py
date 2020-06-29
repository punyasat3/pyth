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

#Region Validation & filtering  matching instances running instances
client = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
regions_list = [region['RegionName'] for region in client.describe_regions()['Regions']]
instance_ids_with_matching_tags=[]
instance_list=[]
running_list2=[]

for region in regions:
    running_list1=[]
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
             running_list1.append(Initid['InstanceId'])

    client2 = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    #checking whether same role tag having two instances
    for i1 in running_list1:
      count=0
      response2 = client2.describe_instances(InstanceIds=[i1])
      for Instances1 in response2['Reservations']:
        for tag in Instances1['Instances']:
          for key1 in tag['Tags']:
            if key1['Key']=="role":
              for i2 in running_list1:
                response3 = client2.describe_instances(InstanceIds=[i2])
                for instances2 in response3['Reservations']:
                  for tag in instances2['Instances']:
                    for key2 in tag['Tags']:
                      if key2['Key']=="role" and  key1['Value']==key2['Value']:
                         count=count+1

      #if role tag having only single instance it will append and deregister
      if count==1:
         running_list2.append(i1)
      #if more than one instance having role tag its won't deregister and  it will push log with instance id
      if count>1:
         logging.error(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name :" +str(region)+"More the 1 instance is tagged for deregistration for the same role "+str(i1))







logging.info("script name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name : --- instance: --- Trying to Deregister Instances...")

# Deregister process
def deregisterforregion(region):
    elb_client = boto3.client('elb',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    elb_response=elb_client.describe_load_balancers()
    regionallelbs=elb_response['LoadBalancerDescriptions']
    #print(regionallelbs)

    def deregisterforelb(loadbalancer):
        #in every elb taking instance id and if id matches with running_list its simply deregister
        for initid in loadbalancer['Instances']:
            if initid['InstanceId']  in running_list2:
                  instance_list.append(initid['InstanceId'])
                  elb=str(loadbalancer['LoadBalancerName'])
                  elb_response1 = elb_client.deregister_instances_from_load_balancer(LoadBalancerName=elb,Instances=[{'InstanceId': initid['InstanceId']}])
                  #sleep(3)
                  if initid['InstanceId'] not  in elb_response1:
                      logging.warning(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name :" +str(region)+"instance "+str(initid['InstanceId'])+" is Deregistered from ELB named "+str(elb)+" in region "+str(region))
                  else :
                       logging.warning(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" region name :" +str(region)+"instance "+str(initid['InstanceId'])+" is not able to  Deregistered from ELB named "+str(elb)+" in region "+str(region))

    #from here only multiple threads will create and calls deregisaterforelb function
    for loadbalancer in regionallelbs:
        p = threading.Thread(target = deregisterforelb, args=(loadbalancer,)).start()
#from here only multiple threads will create and calls deregisaterforregion function
for region in regions:
    t = threading.Thread(target = deregisterforregion, args=(region,)).start()

# if tag instances not in elb or already deregister
if len(instance_list)==0:
  logging.info(" script_name: "+str(sys.argv[0])+" Account_id: "+str(account_id)+" Nothing to Deregister.\nThanks.")
