#! /usr/local/bin/python3

import os
import threading
import boto3
import sys
import logging
from time import sleep
from config1 import *
from datetime import datetime,timedelta,date
#log file
TODAY_DATE_FULL=datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
logging.basicConfig(filename='elb_deregister'+str(TODAY_DATE_FULL)+'.log', level=int(Level),
                    format='%(asctime)s:%(levelname)s:%(message)s',filemode='w')

#Credentials Validation
sts = boto3.client('sts',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=default_region)
try:
    account_id = sts.get_caller_identity()["Account"]
    sts.get_caller_identity()
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : -:-:- : Credentials are valid.")
except:
    logging.info(" "+str(sys.argv[0])+" : -:-:- : -:-:- : -:-:- : -:-:- : Credentials invalid. \nPlease Provide Valid Credentials in config file.\nThanks")
    sys.exit(0)

#Checks
if len(regions)==0:
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : -:-:- : Please Enter Atleast One region in Config file.")
    logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : -:-:- : check regionslist in config file")
    sys.exit(2)
if len(ec2_tag_names)==0:
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : -:-:- : Please Enter Atleast One EC2 Tag name in Config file.")
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
        logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : -:-:- : No Such Region Found.\nPlease Enter Valid Region in config file.\nThanks")
        logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : -:-:- : please mention  proper region name in input file ")
        sys.exit(1)
    client1 = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    response1 = client1.describe_instances(Filters=ec2_tag_names)
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+" : -:-:- : -:-:- : Trying to filter tagmatching and running instances and appended to temporary_running_list")
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

    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+" : -:-:- : -:-:- : Trying to check whether any two instances having same tag called "+str(Specifictag))
    for i1 in temporary_running_list:
      count=0
      tag_list=[]
      response3 = client1.describe_instances(InstanceIds=[i1])
      #print(response3)
      for Instances1 in response3['Reservations']:
        for tag in Instances1['Instances']:
          for key1 in tag['Tags']:
            tag_list.append(key1['Key'])
            if key1['Key']=="Role":
              for i2 in temporary_running_list:
                response4 = client1.describe_instances(InstanceIds=[i2])
                for instances2 in response4['Reservations']:
                  for tag in instances2['Instances']:
                    for key2 in tag['Tags']:
                      if key2['Key']=="Role" and  key1['Value']==key2['Value']:
                         count=count+1
        # here it will check whether instance id having role tag or not
        if Specifictag not in tag_list:
            logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+" : "+str(i1)+" : -:-:- : We are not going to do further deregister procees for this instance id beacuse this id not having Tag called "+str(Specifictag))


      #if role tag having only single instance it will append and deregister
      if count==1:
         permanent_running_list.append(i1)
      #if more than one instance having role tag its won't deregister and  it will push log with instance id
      if count>1:
         logging.error(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : "+str(i1)+" : -:-:- : More the 1 instance is tagged for deregistration process where at the same time both instance having same Specifictag called"+str(Specifictag))
         logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : "+str(i1)+" : -:-:- : please put only for one instance tag---deregister:true among the same Sapcifictag Instances called "+str(Specifictag))





if len(permanent_running_list)==0:
   logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- :  No matching instances found in this tagging creteria. \ntag name is false.\nThanks")
   logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : please check whether provided instances having proper tags AND unique role tag And make sure instance is in running status ")
   sys.exit(3)

logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : -:-:- : -:-:- : Filetred all tag matching and running instances In this account and  appended to permanent_running_list and  Trying to Deregister Instances..."+str(permanent_running_list))




# Deregister process
def deregisterforregion(region):
    logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : -:-:- : Entred in to region and try to take loadbalncers details ")
    elb_client = boto3.client('elbv2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    client2 = boto3.client('ec2',aws_access_key_id=access_key,aws_secret_access_key=secret_access_key,region_name=region)
    waiter = elb_client.get_waiter('target_deregistered')
    elb_response=elb_client.describe_load_balancers()
    inregionallelbs=elb_response['LoadBalancers']

    #After creation of thread called threadforloadbancers it will call this deregisterfor elb function
    def deregisterforelb(loadbalancerarn):
      logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : -:-:- : -:-:- : script entred in to loadbalncer "+str(loadbalancerarn['LoadBalancerName'])+" and try to take targetgrouparn")
      logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : -:-:- : -:-:- : script entred in to loadbalncer "+str(loadbalancerarn['LoadBalancerName'])+" check whether targetgroup is attached with loadbalncer or not")
      #in every elb taking instance id and if id matches with running_list its simply deregister
      elb_list=[]
      count2=0
      instance_list=[]
      response5 = elb_client.describe_listeners(LoadBalancerArn=(str(loadbalancerarn['LoadBalancerArn'])),)

     # From here we are appending all instanceids to list to know how many instances is attached to elb and putting that lenth in count2 variable
      for defaultaction in response5['Listeners']:
        for targetgrouparn in defaultaction['DefaultActions'] :
          response6 = elb_client.describe_target_health(TargetGroupArn=(str(targetgrouparn['TargetGroupArn'])),)
          for target in response6['TargetHealthDescriptions']:
            if target['TargetHealth']['State']==HealthStatus:
              elb_list.append(target['Target']['Id'])
              count2=len(elb_list)
      # From here we are taking one by one instance ids and checking with permanent_running_list deregistering
          for target in response6['TargetHealthDescriptions']:
            logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : "+str(target['Target']['Id'])+" : "+str(loadbalancerarn['LoadBalancerName'])+" From this loadbalncer we  took targetgroup instance id and checking whether target-instance id in Healthy stage and loadbalncer containing atleast two healty instances or not")
            if target['TargetHealth']['State']==HealthStatus and  count2>1:
              logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : "+str(target['Target']['Id'])+" : "+str(loadbalancerarn['LoadBalancerName'])+" We verified  loadbalncer having minimum two healthy instances and  Target id in healthy stage . And now we are checking whether instance id is matched with permanent_running_list or not")
              if  target['Target']['Id'] in permanent_running_list:
                instance_list.append(target['Target']['Id'])
                try:
                  response7 = elb_client.deregister_targets(TargetGroupArn=(str(targetgrouparn['TargetGroupArn'])),Targets=[{'Id': target['Target']['Id'],},],)
                  logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : "+str(target['Target']['Id'])+" : -:-:- :  Deregistering procees is going on  from ELB named "+str(loadbalancerarn['LoadBalancerName'])+" for  every "+str(Instance_Deregistration_checkingtime)+" secs script will monitor the dergister status Once it deregistered we will update . and total maximum attempts will be "+str(Maxattempts)+".And maximum time out is 6mins please wait ......")
                  response8 = waiter.wait(TargetGroupArn=(str(targetgrouparn['TargetGroupArn'])),Targets=[{'Id': target['Target']['Id'],},],WaiterConfig={'Delay': int(Instance_Deregistration_checkingtime),'MaxAttempts': int(Maxattempts)})
                  logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : "+str(target['Target']['Id'])+" : "+str(loadbalancerarn['LoadBalancerName'])+" Instance is successfully deregister from loadbalncer ")
                  count2=count2-1
                  response9 = client2.create_tags(Resources=[target['Target']['Id']],Tags = [{'Key': AfterderegisterChangingKey,'Value': AfterderegisterChangingValue}])
                  logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : "+str(target['Target']['Id'])+" : After deregistering Instance the tag name is changed as "+str(AfterderegisterChangingKey)+":"+str(AfterderegisterChangingValue))
                except:
                  logging.error(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+" : "+str(target['Target']['Id'])+" : "+str(loadbalancerarn['LoadBalancerName'])+" MAXIMUM TIMEOUT. We tried to deregister  instance . But we are  Not able to  Deregistered from ELB " )
              else:
                logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : "+str(target['Target']['Id'])+" : "+str(loadbalancerarn['LoadBalancerName'])+" Mentioned target id not matched with permanent_running_list .so we are not going to deregister this instance.")
            else:
              logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+" : "+str(target['Target']['Id'])+" : "+str(loadbalancerarn['LoadBalancerName'])+"  This Loadbalncer having only one healthy instance Or  This instance is not in healthy status so we are not deregistering this  instances from this loadbalncer")
              logging.debug(" "+str(sys.argv[0])+" : "+str(account_id)+" : " +str(region)+" : -:-:- "+str(loadbalancerarn['LoadBalancerName'])+" please check whether loadbalncer having only one instance or not")



      if len(instance_list)==0:
        logging.info(" "+str(sys.argv[0])+" : "+str(account_id)+" : "+str(region)+" : -:-:- : -:-:- : Nothing to Deregister in Loadbalancer named as  "+str(loadbalancerarn['LoadBalancerName']))

    #from here only multiple threads will create and calls deregisaterforelb function
    for loadbalancerarn in inregionallelbs:
        threadsforloadbalancers = threading.Thread(target = deregisterforelb, args=(loadbalancerarn,)).start()
#from here only multiple threads will create and calls deregisaterforregion function
for region in regions:
    threadsforregion = threading.Thread(target = deregisterforregion, args=(region,)).start()
