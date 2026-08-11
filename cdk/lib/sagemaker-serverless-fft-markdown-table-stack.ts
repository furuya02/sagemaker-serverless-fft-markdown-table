import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
import { Construct } from 'constructs';

const PROJECT_NAME = 'sagemaker-serverless-fft-markdown-table';

export class SagemakerServerlessFftMarkdownTableStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // cdk deploy -c bucket_suffix=20260806 でアカウントID部分を置き換え可能
    const bucketSuffix = this.node.tryGetContext('bucket_suffix') ?? this.account;

    // 学習データ（train.jsonl）とカスタマイズ済みモデルの出力先
    const bucket = new s3.Bucket(this, 'Bucket', {
      bucketName: `${PROJECT_NAME}-${bucketSuffix}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // サーバーレスモデルカスタマイズジョブ / エンドポイントが引き受ける実行ロール
    const role = new iam.Role(this, 'SageMakerExecutionRole', {
      roleName: `${PROJECT_NAME}-sagemaker-execution-role`,
      assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
    });

    role.attachInlinePolicy(
      new iam.Policy(this, 'S3RwPolicy', {
        policyName: `${PROJECT_NAME}-sagemaker-s3-rw-policy`,
        statements: [
          new iam.PolicyStatement({
            actions: ['s3:GetObject', 's3:PutObject', 's3:ListBucket'],
            resources: [bucket.bucketArn, `${bucket.bucketArn}/*`],
          }),
        ],
      }),
    );

    role.attachInlinePolicy(
      new iam.Policy(this, 'CustomizationPolicy', {
        policyName: `${PROJECT_NAME}-sagemaker-customization-policy`,
        statements: [
          new iam.PolicyStatement({
            actions: [
              'logs:CreateLogGroup',
              'logs:CreateLogStream',
              'logs:PutLogEvents',
              'cloudwatch:PutMetricData',
            ],
            resources: ['*'],
          }),
          new iam.PolicyStatement({
            actions: [
              'ecr:GetAuthorizationToken',
              'ecr:BatchGetImage',
              'ecr:GetDownloadUrlForLayer',
            ],
            resources: ['*'],
          }),
          // SageMaker Python SDK V3 がロール検証で要求する EC2 ネットワーク権限
          new iam.PolicyStatement({
            actions: [
              'ec2:CreateNetworkInterface',
              'ec2:CreateNetworkInterfacePermission',
              'ec2:DeleteNetworkInterface',
              'ec2:DeleteNetworkInterfacePermission',
              'ec2:DescribeDhcpOptions',
              'ec2:DescribeNetworkInterfaces',
              'ec2:DescribeSecurityGroups',
              'ec2:DescribeSubnets',
              'ec2:DescribeVpcs',
            ],
            resources: ['*'],
          }),
          // ベースモデル（SageMakerPublicHub）の参照と、学習済みモデルのパッケージ登録
          new iam.PolicyStatement({
            actions: [
              'sagemaker:DescribeHub',
              'sagemaker:DescribeHubContent',
              'sagemaker:ListHubs',
              'sagemaker:ListHubContents',
              'sagemaker:CreateModelPackage',
              'sagemaker:DescribeModelPackage',
              'sagemaker:DescribeModelPackageGroup',
              'sagemaker:ListModelPackages',
              'sagemaker:UpdateModelPackage',
              'sagemaker:AddTags',
            ],
            resources: ['*'],
          }),
        ],
      }),
    );

    // カスタマイズ済みモデルの登録先（サーバーレスカスタマイズでは必須）
    const modelPackageGroup = new sagemaker.CfnModelPackageGroup(this, 'ModelPackageGroup', {
      modelPackageGroupName: `${PROJECT_NAME}-model-package-group`,
    });

    new cdk.CfnOutput(this, 'BucketName', { value: bucket.bucketName });
    new cdk.CfnOutput(this, 'SageMakerExecutionRoleArn', { value: role.roleArn });
    new cdk.CfnOutput(this, 'ModelPackageGroupName', {
      value: modelPackageGroup.modelPackageGroupName,
    });
  }
}
