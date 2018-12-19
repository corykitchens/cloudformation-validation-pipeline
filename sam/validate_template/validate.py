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


def validate_template(name, template):
    try:
        cf_client = boto3.client('cloudformation')
        res = cf_client.validate_template(TemplateBody=template)
    except Exception as e:
        return [e]
    return None


def lambda_handler(event, context):
    return "Inside handler"
    # try:
    #     logger.config(context.aws_request_id)
    #     logger.debug("Handler starting...")
    #     logger.debug(event)
    #     pipeline_run.consume_event(event, context, loglevel=loglevel)
    #     logger.info({'event': 'new_invoke'})
    #     errors = []
    #     successes = []
    #     input_artifacts = event['CodePipeline.job']['data']['inputArtifacts']
    #     if len(input_artifacts):
    #         location = input_artifacts[0]['location']
    #         if location['type'] == 'S3':
    #             bucket_name = location['s3Location']['bucketName']
    #             obj_key = location['s3Location']['objectKey']
    #             for name, template in get_templates(bucket_name, obj_key):
    #                 validate_failed = validate_template(name, template)
    #                 if validate_failed:
    #                   errors.append([name, template, validate_failed])
    #                 else:
    #                   successes.append('%s/%s' % (template, name))
    #             if len(errors) > 0:
    #                 msg = "%s lint failures %s" % (len(errors), errors)
    #                 print(msg)
    #                 pipeline_run.put_job_failure(msg)
    #                 logger.error(msg)
    #             else:
    #                 msg = "%s lint failures %s" % (len(errors), errors)
    #                 print(msg)
    #                 pipeline_run.put_job_success("Successfully linted: %s" % successes)
    #                 logger.info("Successfully linted: %s" % successes)
    #     else:
    #         pipeline_run.put_job_failure("No input artifacts given")
    # except Exception as exception:
    #     logger.error("unhandled exception!", exc_info=1)
        pipeline_run.put_job_failure(str(exception))
