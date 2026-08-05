# sagemaker-serverless-fft-markdown-table

[English README is here](README.md)

Amazon SageMaker AI のサーバーレスモデルカスタマイズ（フルファインチューニング）で Llama 3.2 1B Instruct をカスタマイズし、比較・列挙系の質問に必ず Markdown 表で回答するモデルを作るサンプルです。学習データは、前記事（LoRA）と同じ Amazon Bedrock 合成データを流用します。

- 前記事（Training Job + LoRA）: https://dev.classmethod.jp/articles/llama-3-2-1b-lora-markdown-table-sagemaker/
- サーバーレス フルファインチューニングの発表: https://aws.amazon.com/jp/about-aws/whats-new/2026/08/amazon-sagemaker-fft/

## 前提条件

- SageMaker Python SDK V3（`sagemaker>=3`）が利用できること
- サーバーレスモデルカスタマイズが対象リージョンで利用可能であること（東京リージョン ap-northeast-1 で利用可）
- 学習データ（chat 形式 messages の jsonl）。前記事のデータをそのまま流用可能
- Amazon Bedrock で Amazon Nova（Lite / Pro）が利用可能であること（データを新規合成する場合のみ）
- pnpm / Python 3.10+ / AWS CLI（リージョン: ap-northeast-1）
- 対象アカウント / リージョンで CDK Bootstrap 済みであること（未実施の場合は下記手順1で実施）

## 構築手順

### 1. クローンと CDK デプロイ

学習データ / 出力用の S3 バケットと、SageMaker 実行ロールを作成します。

```bash
git clone https://github.com/furuya02/sagemaker-serverless-fft-markdown-table.git
cd sagemaker-serverless-fft-markdown-table/cdk
pnpm install

# 対象アカウント / リージョンで初めて CDK を使う場合のみ
pnpm cdk bootstrap

pnpm cdk deploy
# バケット名のアカウントID部分を置き換える場合
# pnpm cdk deploy -c bucket_suffix=20260806
```

### 2. Python 環境の準備

```bash
cd ..
python -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
```

### 3. 学習データの用意

前記事のデータ（`data/train.jsonl` / `data/heldout.jsonl`）をそのまま利用できます。新規に合成する場合は以下を実行します。

```bash
python scripts/generate_questions.py --count 330
python scripts/generate_answers.py
python scripts/validate_dataset.py --heldout-size 30
```

### 4. サーバーレス フルファインチューニングの実行

インスタンスタイプや学習スクリプトの指定は不要です（SageMaker がリソースを自動選択）。

```bash
# フルファインチューニング
python scripts/run_customization.py
# LoRA（比較用）
# python scripts/run_customization.py --method lora
```

完了後、カスタマイズ済みモデルの S3 URI が表示されます。

## 動作確認手順

### 1. エンドポイントへのデプロイ

カスタマイズ済みモデルをエンドポイントにデプロイします。Model / EndpointConfig / Endpoint の作成手順は、AWS 公式ワークショップ（lab-1 の 4-deployment）に従ってください。

- [serverless-model-customization-with-sagemaker-ai](https://github.com/aws-samples/generative-ai-on-amazon-sagemaker/tree/main/workshops/serverless-model-customization-with-sagemaker-ai)

### 2. 遵守率の測定

デプロイ済みエンドポイントに held-out 30 件を推論させ、Markdown 表フォーマットの遵守率を測定します。

```bash
python scripts/evaluate_endpoint.py --endpoint-name <endpoint-name> --delete
```

> エンドポイントは稼働時間で課金されます。`--delete` を付けると評価後にエンドポイントを削除します。途中で中断した場合は、エンドポイントが残っていないか SageMaker コンソールで確認してください。

## クリーンアップ

```bash
cd cdk
pnpm cdk destroy
```

カスタマイズジョブは実行完了で自動終了し、エンドポイントも評価後に削除されるため、常時課金されるリソースは残りません。

## License

[MIT License](LICENSE)

なお、Llama 3.2 モデル自体の利用には [Llama 3.2 Community License](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct) が適用されます。
