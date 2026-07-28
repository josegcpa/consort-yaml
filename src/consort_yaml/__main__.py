"""CLI entry point for consort_yaml."""

import argparse

from consort_yaml import FlowchartBuilder, load_yaml


def main() -> None:
    """
    Parse command-line arguments and print a Mermaid flowchart.

    Reads a YAML file specified by the user and prints the
    corresponding Mermaid flowchart to stdout.
    """
    parser = argparse.ArgumentParser(
        description="Generate a CONSORT flowchart from YAML."
    )
    parser.add_argument("path", type=str, help="Path to the YAML file.")
    args = parser.parse_args()

    data = load_yaml(args.path)
    builder = FlowchartBuilder()
    print(builder.build(data))


if __name__ == "__main__":
    main()
