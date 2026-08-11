"""カスタマイズ済みモデルをリアルタイムエンドポイントにデプロイする

学習完了時に Model Package Group に登録されたモデルパッケージ（最新版）から
モデル成果物の S3 パスを取得し、レシピの HostingConfigs で指定された
DJL LMI (vLLM) コンテナでエンドポイントを作成する。

  python deploy_endpoint.py

※ エンドポイントは稼働時間で課金される（ml.g6.4xlarge）。
   評価後は evaluate_endpoint.py --delete で必ず削除すること。
"""
import argparse

import boto3

PROJECT_NAME = "sagemaker-serverless-fft-markdown-table"
# レシピ llmft_qwen3_1_dot_7b_seq4k_gpu_sft_fft の HostingConfigs（Default Profile）より
IMAGE_URI = "763104351884.dkr.ecr.ap-northeast-1.amazonaws.com/djl-inference:0.34.0-lmi16.0.0-cu128"
INSTANCE_TYPE = "ml.g6.4xlarge"
ENVIRONMENT = {
    "OPTION_ASYNC_MODE": "true",
    "OPTION_ENTRYPOINT": "djl_python.lmi_vllm.vllm_async_service",
    "OPTION_MAX_ROLLING_BATCH_SIZE": "4",
    "OPTION_ROLLING_BATCH": "disable",
    "OPTION_TENSOR_PARALLEL_DEGREE": "1",
    "SAGEMAKER_ENABLE_LOAD_AWARE": "1",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="ap-northeast-1")
    parser.add_argument("--instance-type", default=INSTANCE_TYPE,
                        help="レシピの推奨は ml.g6.4xlarge（最小要件: 12 vCPU / 32GB RAM / GPU 1）")
    args = parser.parse_args()

    sm = boto3.client("sagemaker", region_name=args.region)
    account = boto3.client("sts").get_caller_identity()["Account"]
    role = f"arn:aws:iam::{account}:role/{PROJECT_NAME}-sagemaker-execution-role"

    # 最新のモデルパッケージからモデル成果物の S3 パスを取得
    packages = sm.list_model_packages(
        ModelPackageGroupName=f"{PROJECT_NAME}-model-package-group",
        SortBy="CreationTime", SortOrder="Descending", MaxResults=1,
    )["ModelPackageSummaryList"]
    package = sm.describe_model_package(ModelPackageName=packages[0]["ModelPackageArn"])
    model_data = package["InferenceSpecification"]["Containers"][0]["ModelDataSource"]
    # モデルパッケージはジョブ出力のルートを指すが、HF 形式のモデル本体は
    # checkpoints/hf_merged/ サブディレクトリにあるため、そちらを指すよう修正
    model_data["S3DataSource"]["S3Uri"] += "checkpoints/hf_merged/"
    print(f"model data: {model_data['S3DataSource']['S3Uri']}")

    sm.create_model(
        ModelName=PROJECT_NAME,
        ExecutionRoleArn=role,
        PrimaryContainer={
            "Image": IMAGE_URI,
            "ModelDataSource": model_data,
            "Environment": ENVIRONMENT,
        },
    )
    sm.create_endpoint_config(
        EndpointConfigName=PROJECT_NAME,
        ProductionVariants=[{
            "VariantName": "AllTraffic",
            "ModelName": PROJECT_NAME,
            "InstanceType": args.instance_type,
            "InitialInstanceCount": 1,
        }],
    )
    sm.create_endpoint(EndpointName=PROJECT_NAME, EndpointConfigName=PROJECT_NAME)

    print(f"creating endpoint: {PROJECT_NAME} (InService まで 10 分前後かかる)")
    sm.get_waiter("endpoint_in_service").wait(EndpointName=PROJECT_NAME)
    print("endpoint InService")


if __name__ == "__main__":
    main()
