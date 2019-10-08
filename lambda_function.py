import os
import json
import datetime
import requests
import boto3

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

        data = self.cw.get_metric_statistics(
            Namespace='AWS/Billing',
            MetricName='EstimatedCharges',
            Dimensions=dimensions,
            StartTime=self.starttime,
            EndTime=self.endtime,
            Period=86400,
            Statistics=['Maximum', 'Average'])

        return data['Datapoints']

    def get_costs(self):
        get_cost = lambda x: len(x) > 0 and x[-1]['Average'] or 0

        total = get_cost(self.get_metric_statistics())
        services = {x: get_cost(self.get_metric_statistics(x)) for x in SERVICE_NAMES}
        return total, services


def lambda_handler(event, context):
    total, services = AWSMetricStatistics().get_costs()

    fields = [
        {
            'title': k,
            'value': '{0:.2f} USD'.format(v),
            'short': True,
        }
        for k, v
        in services.items()
    ]

    payload = {
        'attachments': [{
            'fallback': 'AWS Costs Report: Total {0:.2f} USD'.format(total),
            'title': 'AWS Costs Report: Total <{0}|{1:.2f}> USD'.format(CONSOLE_URL, total),
            'color': 'good',
            'fields': fields,
        }],
    }

    requests.post(SLACK_POST_URL, json.dumps(payload))
