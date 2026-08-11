# sagemaker-serverless-fft-markdown-table

[English README is here](README.md)

Amazon SageMaker AI のサーバーレスモデルカスタマイズ（フルファインチューニング）で Qwen3 1.7B をカスタマイズし、比較・列挙系の質問に必ず Markdown 表で回答するモデルを作るサンプルです。学習データは、前記事（LoRA）と同じ Amazon Bedrock 合成データを流用します。

※ FULL（フルファインチューニング）に対応しているかは SageMakerPublicHub のモデルごとのレシピで決まります。前記事で使用した Llama 3.2 1B Instruct は LoRA レシピのみで FULL 非対応のため、本サンプルでは FULL レシピを持つ Qwen3 1.7B（`huggingface-reasoning-qwen3-1-7b`）を使用しています。

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

学習データ / 出力用の S3 バケット、SageMaker 実行ロール、Model Package Group（サーバーレスカスタマイズで必須の登録先）を作成します。

```bash
git clone https://github.com/furuya02/sagemaker-serverless-fft-markdown-table.git
cd sagemaker-serverless-fft-markdown-table/cdk
pnpm install

# 対象アカウント / リージョンで初めて CDK を使う場合のみ
pnpm cdk bootstrap

pnpm cdk deploy
# バケット名のアカウントID部分を置き換える場合
# pnpm cdk deploy -c bucket_suffix=20260811
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

インスタンスタイプや学習スクリプトの指定は不要です（SageMaker がリソースを自動選択）。課金はインスタンス時間ではなく学習トークン数ベースです。

```bash
# フルファインチューニング
python scripts/run_customization.py
# LoRA（比較用）
# python scripts/run_customization.py --method lora
```

起動するとジョブ名が表示されます。完了すると、カスタマイズ済みモデルが Model Package Group に登録されます。

## 動作確認手順

### 1. エンドポイントへのデプロイ

カスタマイズ済みモデルをリアルタイムエンドポイントにデプロイします（モデルのレシピ HostingConfigs で定義された DJL LMI (vLLM) コンテナ + ml.g6.4xlarge を使用）。モデル成果物はジョブ出力の `checkpoints/hf_merged/` サブディレクトリにあり、スクリプトがそこを指すようにしています。

```bash
python scripts/deploy_endpoint.py
# python scripts/deploy_endpoint.py --instance-type ml.g5.4xlarge  # 変更する場合
```

### 2. 遵守率の測定

デプロイ済みエンドポイントに held-out 30 件を推論させ、Markdown 表フォーマットの遵守率を測定します。

```bash
python scripts/evaluate_endpoint.py --endpoint-name sagemaker-serverless-fft-markdown-table --delete
```

> エンドポイントは稼働時間で課金されます。`--delete` を付けると評価後にエンドポイントを削除します。途中で中断した場合は、エンドポイントが残っていないか SageMaker コンソールで確認してください。

## クリーンアップ

残っている EndpointConfig / Model のメタデータ（課金なし）を削除してから、CDK スタックを削除します。

```bash
aws sagemaker delete-endpoint-config --endpoint-config-name sagemaker-serverless-fft-markdown-table
aws sagemaker delete-model --model-name sagemaker-serverless-fft-markdown-table
cd cdk
pnpm cdk destroy
```

カスタマイズジョブは実行完了で自動終了し、エンドポイントも評価後に削除されるため、常時課金されるリソースは残りません。

## License

[MIT License](LICENSE)

なお、Qwen3 モデル自体のライセンスは [Apache License 2.0](https://huggingface.co/Qwen/Qwen3-1.7B) です。
