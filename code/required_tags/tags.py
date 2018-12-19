import os
import json
import boto3
import io
import zipfile
import time
from lib.awsclients import AwsClients
from lib.cfnpipeline import CFNPipeline
from lib.logger import Logger
import cfnlint.core
import yaml

loglevel = 'debug'
logger = Logger(loglevel=loglevel)
logger.info('New Lambda container initialised, logging configured.')
clients = AwsClients(logger)
pipeline_run = CFNPipeline(logger, clients)


def get_templates(bucket_name, obj_key):
    templates = []
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=bucket_name, Key=obj_key)
    data = obj.get("Body").read()
    with io.BytesIO(data) as tf:
        #rewind the file
        # Read the file as a zipfile and process the members
        with zipfile.ZipFile(tf, mode='r') as zipf:
            for subfile in zipf.namelist():
                if '.yaml' in subfile:
                    template = zipf.read(subfile).decode("utf-8")
                    templates.append([subfile, template])
    return templates


def match_required_tags(name, template):
  invalid_resources = []
  REQUIRED_TAGS = set(['BillAccount', 'BillDeptId', 'BillFund',
                    'DataClassification', 'PrimaryContact',
                    'ServiceName'])
  try:
    cfn_template = cfnlint.decode.cfn_yaml.loads(template)
    for resource in cfn_template['Resources']:
      cfn_resource = cfn_template['Resources'][resource]
      if 'Tags' not in cfn_resource['Properties']:
        invalid_resources.append([resource, "No Tags Found"])
      else:
        resource_tags = set([tag['Key'] for tag in cfn_resource['Properties']['Tags']])
        if not REQUIRED_TAGS.issubset(resource_tags):
          invalid_resources.append([resource, "Required tags not in template"])
    return invalid_resources
  except Exception as e:
    return [resource, e]

def lambda_handler(event, context):
    try:
        logger.config(context.aws_request_id)
        logger.debug("Handler starting...")
        logger.debug(event)
        pipeline_run.consume_event(event, context, loglevel=loglevel)
        logger.info({'event': 'new_invoke'})
        errors = []
        successes = []
        input_artifacts = event['CodePipeline.job']['data']['inputArtifacts']
        if len(input_artifacts):
            location = input_artifacts[0]['location']
            if location['type'] == 'S3':
                bucket_name = location['s3Location']['bucketName']
                obj_key = location['s3Location']['objectKey']
                for name, template in get_templates(bucket_name, obj_key):
                    validate_failed = match_required_tags(name, template)
                    if validate_failed:
                      errors.append([name, template, validate_failed])
                    else:
                      successes.append('%s/%s' % (template, name))
                if len(errors) > 0:
                    msg = "%s lint templateailures %s" % (len(errors), errors)
                    print(msg)
                    pipeline_run.put_job_failure(msg)
                    logger.error(msg)
                else:
                    msg = "%s lint failures %s" % (len(errors), errors)
                    print(msg)
                    pipeline_run.put_job_success("Successfully linted: %s" % successes)
                    logger.info("Successfully linted: %s" % successes)
        else:
            pipeline_run.put_job_failure("No input artifacts given")
    except Exception as exception:
        logger.error("unhandled exception!", exc_info=1)
        pipeline_run.put_job_failure(str(exception))


if __name__=="__main__":
    match_required_tags("hello", "test")