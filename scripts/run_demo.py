"""Small script to run the demo from command line (placeholder)."""

import argparse

from examples.text2sql_demo import demo


def main():
    parser = argparse.ArgumentParser(description="Run text2sql demo (placeholder)")
    parser.add_argument("--prompt", type=str, default=None, help="Prompt to convert to SQL")
    args = parser.parse_args()

    demo()


if __name__ == "__main__":
    main()
