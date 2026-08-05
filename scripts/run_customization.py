"""SageMaker サーバーレスモデルカスタマイズ（フルファインチューニング）を実行する

SageMaker Python SDK V3 の SFTTrainer を使い、インフラのプロビジョニング無しで
学習ジョブを起動する。前記事（Training Job + LoRA）と異なり、学習スクリプト・DLC・
インスタンスタイプの指定は不要で、SageMaker 側がリソースを自動選択する。

  フルファインチューニング: python run_customization.py
  LoRA（比較用）:           python run_customization.py --method lora

参考:
- AWS 公式ワークショップ（SFTTrainer の実コード）:
  https://github.com/aws-samples/generative-ai-on-amazon-sagemaker/tree/main/workshops/serverless-model-customization-with-sagemaker-ai
- SDK ドキュメント: https://sagemaker.readthedocs.io/en/stable/model_customization/index.html
- 発表: https://aws.amazon.com/jp/about-aws/whats-new/2026/08/amazon-sagemaker-fft/

※ 引数名・データセット登録方法は SDK バージョンにより変わるため、実行前に上記を確認すること。
"""
import argparse

import boto3
import sagemaker
from sagemaker.train.common import TrainingType
from sagemaker.train.sft_trainer import SFTTrainer

PROJECT_NAME = "sagemaker-serverless-fft-markdown-table"
# サーバーレスモデルカスタマイズ対応の JumpStart モデル ID（前記事と同じ Llama 3.2 1B）
MODEL_ID = "meta-textgeneration-llama-3-2-1b-instruct"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket-suffix", help="バケット名のアカウントID部分の置き換え")
    parser.add_argument("--train-file", default="data/train.jsonl")
    parser.add_argument("--method", choices=["full", "lora"], default="full",
                        help="full=フルファインチューニング / lora=PEFT(LoRA)")
    parser.add_argument("--epochs", type=int, default=3)
    args = parser.parse_args()

    account = boto3.client("sts").get_caller_identity()["Account"]
    bucket = f"{PROJECT_NAME}-{args.bucket_suffix or account}"
    role = f"arn:aws:iam::{account}:role/{PROJECT_NAME}-sagemaker-execution-role"

    # chat 形式（messages）の jsonl を S3 へアップロード
    session = sagemaker.Session()
    train_s3 = session.upload_data(args.train_file, bucket=bucket, key_prefix="data")
    print(f"train data: {train_s3}")

    training_type = TrainingType.FULL if args.method == "full" else TrainingType.LORA

    trainer = SFTTrainer(
        model=MODEL_ID,
        training_type=training_type,
        training_dataset=train_s3,          # 登録済み DataSet を渡す方式もある（ワークショップ参照）
        s3_output_path=f"s3://{bucket}/output",
        role=role,
        accept_eula=True,
        base_job_name=PROJECT_NAME,
    )
    trainer.hyperparameters.max_epochs = args.epochs

    # インフラのプロビジョニング・管理は SageMaker 側が実施する（使用分のみ課金）
    job = trainer.train(wait=False)
    print(f"customization job: {job.training_job_name}")


if __name__ == "__main__":
    main()
