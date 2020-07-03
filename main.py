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
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : Credentials are valid.")
except:
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : Credentials invalid. \nPlease Provide Valid Credentials in config file.\nThanks")
    sys.exit(0)

#Checks
if len(regions)==0:
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- Please Enter Atleast One region in Config file.")
    logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:-  check regionslist in config file")
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
        logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- No Such Region Found.\nPlease Enter Valid Region in config file.\nThanks")
        logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- please mention  proper region name in input file ")
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
         logging.error(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : "+str(i1)+" : More the 1 instance is tagged for deregistration for the same role with instance_id  "+str(i1))
         logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : "+str(i1)+" : please put only for one instance tag---deregister:true among the same role Instances ")


if len(permanent_running_list)==0:
   logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : Didnt found any Tagmatching and running instaces for deregistering in this account ")
   logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : please check whether provided instances having proper tags AND unique role tag And make sure instance is in running status ")
   sys.exit(3)

logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : Trying to Deregister Instances...")




# Deregister process
def deregisterforregion(region):
    logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : -:-:- : Entred in to region and try to take loadbalncers details ")
    elb_client = boto3.client('elbv2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    waiter = elb_client.get_waiter('target_deregistered')
    elb_response=elb_client.describe_load_balancers()
    inregionallelbs=elb_response['LoadBalancers']

    #After creation of thread called threadforloadbancers it will call this deregisterfor elb function
    def deregisterforelb(loadbalancerarn):
      logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" script entred in to loadbalncer "+str(loadbalancerarn['LoadBalancerName'])+" and try to take targetgrouparn")
      #in every elb taking instance id and if id matches with running_list its simply deregister
      elb_list=[]
      count2=0
      response5 = elb_client.describe_listeners(LoadBalancerArn=(str(loadbalancerarn['LoadBalancerArn'])),)

     # From here we are appending all instanceids to list to know how many instances is attached to elb and putting that lenth in count2 variable
      for defaultaction in response5['Listeners']:
        for targetgrouparn in defaultaction['DefaultActions'] :
          response6 = elb_client.describe_target_health(TargetGroupArn=(str(targetgrouparn['TargetGroupArn'])),)
          for target in response6['TargetHealthDescriptions']:
            elb_list.append(target['Target']['Id'])
            count2=len(elb_list)
      # From here we are taking one by one instance ids and checking with permanent_running_list deregistering
          for target in response6['TargetHealthDescriptions']:
            if count2>1:
              if  target['Target']['Id'] in permanent_running_list:
                try:
                  response7 = elb_client.deregister_targets(TargetGroupArn=(str(targetgrouparn['TargetGroupArn'])),Targets=[{'Id': target['Target']['Id'],},],)
                  response8 = waiter.wait(TargetGroupArn=(str(targetgrouparn['TargetGroupArn'])),Targets=[{'Id': target['Target']['Id'],'Port': 80,},],WaiterConfig={'Delay': 30,'MaxAttempts': 12})
                  logging.warning(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+" : instance Id with "+str(target['Target']['Id'])+" is Deregistered from ELB named "+str(loadbalancerarn['LoadBalancerName'])+" in region "+str(region))
                  count=count2-1
                except:
                  logging.error(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+" : instance Id with "+str(target['Target']['Id'])+" is Not able to  Deregistered from ELB named "+str(loadbalancerarn['LoadBalancerName'])+" in region "+str(region)+" : Time out Try again ")


    #from here only multiple threads will create and calls deregisaterforelb function
    for loadbalancerarn in inregionallelbs:
        threadsforloadbalancers = threading.Thread(target = deregisterforelb, args=(loadbalancerarn,)).start()
#from here only multiple threads will create and calls deregisaterforregion function
for region in regions:
    threadsforregion = threading.Thread(target = deregisterforregion, args=(region,)).start()

# if tag instances not in elb or already deregister
if len(instance_list)==0:
  logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+": -:-:- : -:-:- : Nothing to Deregister.\nThanks.")
