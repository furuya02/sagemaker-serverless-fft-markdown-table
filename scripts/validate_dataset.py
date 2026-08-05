"""生成データの表形式チェックと train / held-out 分割"""
import argparse
import json
import pathlib
import random
import re

# ヘッダ行 + 区切り行を持つ Markdown 表
TABLE_RE = re.compile(r"^\|.+\|\s*\n\|[\s:\-|]+\|", re.MULTILINE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/dataset.jsonl")
    parser.add_argument("--heldout-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-output", default="data/train.jsonl")
    parser.add_argument("--heldout-output", default="data/heldout.jsonl")
    args = parser.parse_args()

    records = [json.loads(line) for line in open(args.input)]
    valid = [r for r in records if TABLE_RE.search(r["messages"][1]["content"])]
    invalid = len(records) - len(valid)
    print(f"total: {len(records)}, valid: {len(valid)}, invalid(表なし): {invalid}")

    random.Random(args.seed).shuffle(valid)
    heldout, train = valid[: args.heldout_size], valid[args.heldout_size :]

    pathlib.Path(args.train_output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.train_output, "w") as f:
        for r in train:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # held-out は評価用に質問のみ保存
    with open(args.heldout_output, "w") as f:
        for r in heldout:
            f.write(json.dumps({"question": r["messages"][0]["content"]}, ensure_ascii=False) + "\n")

    print(f"train: {len(train)} -> {args.train_output}")
    print(f"heldout: {len(heldout)} -> {args.heldout_output}")


if __name__ == "__main__":
    main()
