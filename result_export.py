import json


def save_result(path, result):
    text = json.dumps(result, indent=2, allow_nan=False)

    with open(path, "x", encoding="utf-8") as output:
        output.write(text)
        output.write("\n")