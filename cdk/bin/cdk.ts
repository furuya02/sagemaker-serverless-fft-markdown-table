#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { SagemakerServerlessFftMarkdownTableStack } from '../lib/sagemaker-serverless-fft-markdown-table-stack';

const app = new cdk.App();
new SagemakerServerlessFftMarkdownTableStack(app, 'SagemakerServerlessFftMarkdownTableStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? 'ap-northeast-1',
  },
});
