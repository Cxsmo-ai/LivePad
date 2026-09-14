"""Local controller test mode; no TikTok account or game is required."""

import argparse
import json

from runtime import ControllerRuntime


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve one TikTok-style command comment locally")
    parser.add_argument("message", nargs="+", help="command text, e.g. w sprint ads fire right 35")
    args = parser.parse_args()
    runtime = ControllerRuntime()
    result = runtime.handle_comment({"user": "local-test", "user_id": "local-test", "comment": " ".join(args.message)})
    submission = runtime.flush(1)
    state = submission.state if submission else runtime.engine.resolve(1)
    print(json.dumps({
        "accepted": [command.action for command in result.accepted],
        "rate_limited": [command.action for command in result.rate_limited],
        "invalid_tokens": list(result.invalid_tokens),
        "state": state.to_wire(1),
    }, indent=2))


if __name__ == "__main__":
    main()
