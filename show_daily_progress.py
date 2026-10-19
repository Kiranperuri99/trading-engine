from pathlib import Path
import subprocess
import sys


def main():
    try:
        result = subprocess.run(
            ["git", "log", "--since=midnight", "--format=%h %s"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("Git was not found. Install Git and reopen the terminal.")
        return 1

    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return result.returncode

    commits = result.stdout.splitlines()
    print(f"Today's local commits: {len(commits)}/20")
    for commit in commits:
        print(commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())