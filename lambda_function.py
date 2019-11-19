import os
import json
import datetime
import requests
import boto3
import concurrent.futures

SLACK_POST_URL = os.environ['SLACK_POST_URL']
CONSOLE_URL = 'https://console.aws.amazon.com/billing/home?region=ap-northeast-1#/'

SERVICE_NAMES = [
    'AmazonEC2', 
    'AmazonRDS', 
    'AmazonRoute53', 
    'AmazonS3', 
    'AmazonSNS', 
    'AWSDataTransfer', 
    'AWSLambda', 
    'APIGateway', 
    'AWSQueueService',
    ]


class AWSMetricStatistics():
    def __init__(self):
        self.cw = boto3.client('cloudwatch', region_name='us-east-1')
        self.starttime = datetime.datetime.today() - datetime.timedelta(days=1)
        self.endtime = datetime.datetime.today()

    def get_metric_statistics(self, service_name=None):
        dimensions = [{'Name': 'Currency', 'Value': 'USD'}]
        if service_name:
            dimensions.append({'Name': 'ServiceName', 'Value': service_name})

        return self.cw.get_metric_statistics(
            Namespace='AWS/Billing',
            MetricName='EstimatedCharges',
            Dimensions=dimensions,
            StartTime=self.starttime,
            EndTime=self.endtime,
            Period=86400,
            Statistics=['Maximum', 'Average'])

    def get_service_cost(self, service_name=None):
        data = self.get_metric_statistics(service_name)
        return len(data['Datapoints']) > 0 and data['Datapoints'][-1]['Average'] or 0


def lambda_handler(event, context):
    metric_statistics = AWSMetricStatistics()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(SERVICE_NAMES) + 1) as executor:
        services = [executor.submit(metric_statistics.get_service_cost, service_name=x) for x in SERVICE_NAMES]
        total = executor.submit(metric_statistics.get_service_cost)

    fields = [
        {
            'title': SERVICE_NAMES[i],
            'value': '{0:.2f} USD'.format(v.result()),
            'short': True,
        }
        for i, v
        in enumerate(services)
    ]

    payload = {
        'attachments': [{
            'fallback': 'AWS Costs Report: Total {0:.2f} USD'.format(total.result()),
            'title': 'AWS Costs Report: Total <{0}|{1:.2f}> USD'.format(CONSOLE_URL, total.result()),
            'color': 'good',
            'fields': fields,
        }],
    }

    requests.post(SLACK_POST_URL, json.dumps(payload))
