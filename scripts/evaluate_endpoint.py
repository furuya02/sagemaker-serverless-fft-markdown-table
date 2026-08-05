"""デプロイ済みエンドポイントで表フォーマット遵守率を測る

カスタマイズ済みモデルのエンドポイントに held-out 30 件を推論させ、
Markdown 表を含む回答の割合（遵守率）を算出する。

エンドポイントの作成（Model / EndpointConfig / Endpoint）は手数が多いため、
AWS 公式ワークショップの手順に従って作成しておき、そのエンドポイント名を渡す想定。

  python evaluate_endpoint.py --endpoint-name <name> --inference-component <ic-name>

参考（デプロイ手順・推論ペイロード形式）:
- https://github.com/aws-samples/generative-ai-on-amazon-sagemaker/tree/main/workshops/serverless-model-customization-with-sagemaker-ai

※ エンドポイントは稼働時間で課金される。評価後は忘れずに削除すること（--delete で削除可）。
"""
import argparse
import json
import pathlib
import re

import boto3

# ヘッダ行 + 区切り行を持つ Markdown 表（前記事 validate_dataset.py と同一基準）
TABLE_RE = re.compile(r"^\|.+\|\s*\n\|[\s:\-|]+\|", re.MULTILINE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", required=True)
    parser.add_argument("--inference-component", help="推論コンポーネント名（必要な場合）")
    parser.add_argument("--questions", default="data/heldout.jsonl")
    parser.add_argument("--output", default="results/after.jsonl")
    parser.add_argument("--region", default="ap-northeast-1")
    parser.add_argument("--delete", action="store_true", help="評価後にエンドポイントを削除する")
    args = parser.parse_args()

    smr = boto3.client("sagemaker-runtime", region_name=args.region)
    questions = [json.loads(line)["question"] for line in open(args.questions)]
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    compliant = 0
    with out.open("w") as f:
        for i, question in enumerate(questions, 1):
            # OpenAI chat スキーマ（ワークショップの推論ペイロードに合わせる）
            body = {
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": question}]},
                ],
                "max_tokens": 512,
                "temperature": 0.0,
                "stream": False,
            }
            kwargs = dict(
                EndpointName=args.endpoint_name,
                ContentType="application/json",
                Body=json.dumps(body),
            )
            if args.inference_component:
                kwargs["InferenceComponentName"] = args.inference_component
            res = smr.invoke_endpoint(**kwargs)
            payload = json.loads(res["Body"].read())
            answer = payload["choices"][0]["message"]["content"]

            has_table = bool(TABLE_RE.search(answer))
            compliant += has_table
            f.write(json.dumps(
                {"question": question, "answer": answer, "has_table": has_table},
                ensure_ascii=False,
            ) + "\n")
            print(f"[{i}/{len(questions)}] table={has_table} {question[:30]}")

    rate = compliant / len(questions) * 100
    print(f"\n遵守率: {compliant}/{len(questions)} ({rate:.1f}%)")

    if args.delete:
        boto3.client("sagemaker", region_name=args.region).delete_endpoint(
            EndpointName=args.endpoint_name)
        print("endpoint deleted")


if __name__ == "__main__":
    main()
