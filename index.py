import os
import oss2
import zipfile
import shutil
import time
import json
import logging
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526 import AddTagsRequest


def handler(event, context):
  logger = logging.getLogger()
  logger.info('initializing')

  ACCESS_KEY_ID = os.environ['ACCESS_KEY_ID']
  ACCESS_KEY_SECRET = os.environ['ACCESS_KEY_SECRET']

  ECS_EVENT = ["RunInstances", "CreateInstance"]

  #OSS関連初期設定
  Event = json.loads(event.decode('utf-8').replace("'", '"'))
  OssRegion = Event["events"][0]["region"]
  BuketName = Event["events"][0]["oss"]["bucket"]["name"]
  ObjectName = Event["events"][0]["oss"]["object"]["key"]
  OssEndPoint = "oss-" + OssRegion +".aliyuncs.com"

  # ECS関連初期設定
  InstanceIdSet = []
  Owner = ""
  Region = ""

  # OSS
  auth = oss2.Auth(ACCESS_KEY_ID, ACCESS_KEY_SECRET)
  bucket = oss2.Bucket(auth, OssEndPoint, BuketName)

  tmpdir = '/tmp/download/'
  os.system("rm -rf /tmp/*")
  os.mkdir(tmpdir)

  #対象ActionTrailログをOSSからダウンロード
  bucket.get_object_to_file(ObjectName , tmpdir + 'trail_log.gz')
  os.system("gunzip /tmp/download/trail_log.gz")

  with open('/tmp/download/trail_log') as data:
    OssNotification = json.load(data)

  for actionTrailLog in OssNotification:
    logger.info("*"*20)
    logger.info("eventName : " + actionTrailLog["eventName"])
    logger.info("acsRegion : " + actionTrailLog["acsRegion"])
    logger.info("*"*20)

    if actionTrailLog["eventName"] in ECS_EVENT:

      InstanceIdSet = actionTrailLog["responseElements"]["InstanceIdSets"]["InstanceIdSet"]
      Owner = actionTrailLog["userIdentity"]["userName"]
      EcsRegion = actionTrailLog["acsRegion"]

      logger.info(actionTrailLog["responseElements"]["InstanceIdSets"]["InstanceIdSet"])

    else:
      logger.info("Isn't RunInstances event !")

  #ECS instanceにOwnerタグを追加
  client = AcsClient(ACCESS_KEY_ID, ACCESS_KEY_SECRET, EcsRegion)

  for instance in InstanceIdSet :

    request = AddTagsRequest.AddTagsRequest()
    request.set_ResourceType("instance")
    request.set_ResourceId(instance)

    Tags = [{"Key": "Owner","Value": Owner}]
    request.set_Tags(Tags)

    client.do_action_with_exception(request)

  return 0
