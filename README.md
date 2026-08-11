# sagemaker-serverless-fft-markdown-table

[日本語版 README はこちら](README.ja.md)

A sample that customizes Qwen3 1.7B with Amazon SageMaker AI serverless model customization (full fine-tuning) so that the model always answers comparison/enumeration questions with a Markdown table. It reuses the same Amazon Bedrock synthesized dataset as the previous LoRA article.

Note: whether a model supports FULL (full fine-tuning) is determined by its recipes in SageMakerPublicHub. Llama 3.2 1B Instruct (used in the previous article) only has a LoRA recipe, so this sample uses Qwen3 1.7B (`huggingface-reasoning-qwen3-1-7b`), which has a FULL recipe.

- Previous article (Training Job + LoRA): https://dev.classmethod.jp/articles/llama-3-2-1b-lora-markdown-table-sagemaker/
- Serverless full fine-tuning announcement: https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-sagemaker-fft/

## Prerequisites

- SageMaker Python SDK V3 (`sagemaker>=3`)
- Serverless model customization available in your region (available in Tokyo, ap-northeast-1)
- Training data (chat-format `messages` jsonl). You can reuse the dataset from the previous article as-is
- Amazon Nova (Lite / Pro) usable on Amazon Bedrock (only if you synthesize the data from scratch)
- pnpm / Python 3.10+ / AWS CLI (region: ap-northeast-1)
- CDK bootstrapped for the target account / region (run step 1 below if not)

## Setup

### 1. Clone and deploy CDK

Creates an S3 bucket (for training data / output), a SageMaker execution role, and a Model Package Group (required as the registration target for serverless customization).

```bash
git clone https://github.com/furuya02/sagemaker-serverless-fft-markdown-table.git
cd sagemaker-serverless-fft-markdown-table/cdk
pnpm install

# Only if this is the first time using CDK in the target account / region
pnpm cdk bootstrap

pnpm cdk deploy
# To replace the account-id part of the bucket name
# pnpm cdk deploy -c bucket_suffix=20260811
```

### 2. Prepare Python environment

```bash
cd ..
python -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
```

### 3. Prepare training data

You can reuse the previous article's data (`data/train.jsonl` / `data/heldout.jsonl`) as-is. To synthesize it from scratch:

```bash
python scripts/generate_questions.py --count 330
python scripts/generate_answers.py
python scripts/validate_dataset.py --heldout-size 30
```

### 4. Run serverless full fine-tuning

No instance type or training script needs to be specified (SageMaker selects the resources automatically). Billing is based on trained tokens, not instance hours.

```bash
# Full fine-tuning
python scripts/run_customization.py
# LoRA (for comparison)
# python scripts/run_customization.py --method lora
```

The training job name is printed on start. On completion, the customized model is registered to the Model Package Group.

## Verification

### 1. Deploy to an endpoint

Deploys the customized model to a real-time endpoint (DJL LMI (vLLM) container + ml.g6.4xlarge, as defined in the model recipe's HostingConfigs). The model artifacts live under the `checkpoints/hf_merged/` subdirectory of the job output; the script points the endpoint there.

```bash
python scripts/deploy_endpoint.py
# python scripts/deploy_endpoint.py --instance-type ml.g5.4xlarge  # to override
```

### 2. Measure the compliance rate

Run inference over the 30 held-out questions against the deployed endpoint and measure the Markdown-table compliance rate.

```bash
python scripts/evaluate_endpoint.py --endpoint-name sagemaker-serverless-fft-markdown-table --delete
```

> The endpoint is billed by uptime. Pass `--delete` to delete it after evaluation. If you interrupt it midway, check the SageMaker console to make sure no endpoint remains.

## Cleanup

Delete the remaining (non-billable) endpoint config / model metadata, then destroy the CDK stack.

```bash
aws sagemaker delete-endpoint-config --endpoint-config-name sagemaker-serverless-fft-markdown-table
aws sagemaker delete-model --model-name sagemaker-serverless-fft-markdown-table
cd cdk
pnpm cdk destroy
```

Customization jobs terminate automatically on completion, and the endpoint is deleted after evaluation, so no always-on billable resources remain.

## License

[MIT License](LICENSE)

Note: use of the Qwen3 model itself is subject to its own license ([Apache License 2.0](https://huggingface.co/Qwen/Qwen3-1.7B)).
