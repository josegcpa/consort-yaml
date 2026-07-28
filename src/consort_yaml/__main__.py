import argparse
import yaml

from consort_yaml import (
    FlowchartBuilder,
    load_yaml, 
    HEADER,
    ARROW, 
    EXCLUSION_ARROW, 
    EXCLUSION_ARROW_LONG,
    INDENT
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a CONSORT flowchart from YAML."
    )
    parser.add_argument("path", type=str, help="Path to the YAML file.")
    args = parser.parse_args()

    data = load_yaml(args.path)
    builder = FlowchartBuilder()
    print(builder.build(data))