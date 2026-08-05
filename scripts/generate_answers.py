"""Bedrock で Markdown 表形式の模範回答を生成する（データ合成 2 段階目）"""
import argparse
import json
import pathlib

import boto3

PROMPT = """次の質問に対する模範回答を作成してください。

質問: {question}

条件:
- 1〜2文の短い導入文の後、必ず Markdown 表でまとめる
- 表は `| 項目 | 内容 |` のようにヘッダ行と区切り行を持つ正しい Markdown 形式にする
- 表の後には文章を続けず、表で回答を終える
- 回答本文のみを出力する"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/questions.jsonl")
    parser.add_argument("--model-id", default="apac.amazon.nova-pro-v1:0")
    parser.add_argument("--region", default="ap-northeast-1")
    parser.add_argument("--output", default="data/dataset.jsonl")
    args = parser.parse_args()

    client = boto3.client("bedrock-runtime", region_name=args.region)
    questions = [json.loads(line)["question"] for line in open(args.input)]

    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for i, question in enumerate(questions, 1):
            res = client.converse(
                modelId=args.model_id,
                messages=[{"role": "user", "content": [{"text": PROMPT.format(question=question)}]}],
                inferenceConfig={"maxTokens": 1024, "temperature": 0.3},
            )
            answer = res["output"]["message"]["content"][0]["text"].strip()
            record = {
                "messages": [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ]
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"answered: {i}/{len(questions)}")
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
