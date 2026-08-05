"""Bedrock で「比較・列挙が自然な質問」を生成する（データ合成 1 段階目）"""
import argparse
import json
import pathlib

import boto3

PROMPT = """あなたは学習データ作成のアシスタントです。
「比較」や「列挙」で答えるのが自然な日本語の質問を{n}個生成してください。

例:
- EC2とLambdaの違いを教えて
- リンゴの代表的な品種を教えて
- 新幹線と飛行機、東京大阪間の移動ではどちらが良い？

条件:
- 技術に限らず、料理・旅行・歴史・スポーツ・生活など幅広いジャンルにする
- 質問文のみを JSON 配列で出力する（["質問1", "質問2", ...]）
- JSON 配列以外の文字は出力しない"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=330)
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--model-id", default="apac.amazon.nova-lite-v1:0")
    parser.add_argument("--region", default="ap-northeast-1")
    parser.add_argument("--output", default="data/questions.jsonl")
    args = parser.parse_args()

    client = boto3.client("bedrock-runtime", region_name=args.region)
    questions: list[str] = []
    seen: set[str] = set()

    while len(questions) < args.count:
        res = client.converse(
            modelId=args.model_id,
            messages=[{"role": "user", "content": [{"text": PROMPT.format(n=args.batch_size)}]}],
            inferenceConfig={"maxTokens": 4000, "temperature": 1.0},
        )
        text = res["output"]["message"]["content"][0]["text"]
        batch = json.loads(text[text.index("[") : text.rindex("]") + 1])
        for q in batch:
            if q not in seen:
                seen.add(q)
                questions.append(q)
        print(f"generated: {len(questions)}/{args.count}")

    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for q in questions[: args.count]:
            f.write(json.dumps({"question": q}, ensure_ascii=False) + "\n")
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
