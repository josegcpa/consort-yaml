"""
Generate CONSORT-style flowcharts as Mermaid diagrams from YAML.

This package provides a ``FlowchartBuilder`` that converts a YAML
definition (steps, exclusions, subgraphs) into a Mermaid flowchart
string suitable for rendering with ``mmdc`` or any Mermaid renderer.

Example:
    >>> from consort_yaml import FlowchartBuilder, load_yaml
    >>> data = load_yaml("tcga.yaml")
    >>> builder = FlowchartBuilder()
    >>> print(builder.build(data))
"""

import yaml

__version__ = "0.1.0"

__all__ = [
    "FlowchartBuilder",
    "load_yaml",
    "HEADER",
    "INDENT",
    "ARROW",
    "EXCLUSION_ARROW",
    "EXCLUSION_ARROW_LONG",
]

INDENT = "    "
ARROW = " ---> "
EXCLUSION_ARROW = " --- "
EXCLUSION_ARROW_LONG = " ---- "

HEADER = """---
config:
    theme: base
    themeVariables:
        fontFamily: helvetica
    flowchart:
        rankSpacing: 15
        nodeSpacing: 15
        subGraphTitleMargin:
            top: 10
            bottom: 10
            left: 0
            right: 0
---
flowchart TD
    classDef exclusion fill:#ffdada,stroke-width:1,stroke:black
    classDef step fill:white,stroke-width:1,stroke:black
    classDef sg fill:transparent,stroke-width:1,stroke:black
"""


def load_yaml(path: str) -> dict:
    """
    Load a YAML file and return its contents as a dictionary.

    Args:
        path (str): Path to the YAML file.

    Returns:
        dict: Parsed YAML contents.
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)


class FlowchartBuilder:
    """
    Builds a Mermaid flowchart from a CONSORT-style YAML definition.

    Supports steps, exclusions, and arbitrarily nested subgraphs. Each
    subgraph supports the same internal structure as the outer graph
    (steps, exclusions, further subgraphs) and its direction can be
    specified via the ``direction`` key in the YAML (default ``TD``).
    """

    def __init__(self) -> None:
        """Initialise the builder with empty state."""
        self._step_counter = 0
        self._exclusion_counter = 0
        self._subgraph_counter = 0
        self._step_ids: list[str] = []
        self._exclusion_ids: list[str] = []
        self._subgraph_ids: list[str] = []
        self._body_lines: list[str] = []

    def _next_step_id(self) -> str:
        """Return the next unique step node ID."""
        sid = f"step{self._step_counter}"
        self._step_counter += 1
        return sid

    def _next_exclusion_id(self) -> str:
        """Return the next unique exclusion node ID."""
        eid = f"exclusion{self._exclusion_counter}"
        self._exclusion_counter += 1
        return eid

    def _next_subgraph_id(self) -> str:
        """Return the next unique subgraph ID."""
        sgid = f"sg{self._subgraph_counter}"
        self._subgraph_counter += 1
        return sgid

    @staticmethod
    def _format_node(node_id: str, message: str, n: int) -> str:
        """Format a Mermaid node definition string.

        Args:
            node_id (str): The node identifier.
            message (str): The label text (may contain HTML).
            n (int): The sample count.

        Returns:
            str: A Mermaid node definition string.
        """
        return f'{node_id}["{message}<br>(n={n})"]'

    def _emit_node(
        self, node_id: str, message: str, n: int, indent: int
    ) -> None:
        """
        Append a formatted node line to the body.

        Args:
            node_id (str): The node identifier.
            message (str): The label text.
            n (int): The sample count.
            indent (int): The indentation level.
        """
        self._body_lines.append(
            INDENT * indent + self._format_node(node_id, message, n)
        )

    def _process_exclusions(
        self, exclusions: list[dict], n: int, indent: int
    ) -> tuple[str, int]:
        """
        Process exclusions for a step.

        Args:
            exclusions (list[dict]): List of exclusion dicts with
                ``reason`` (str) and ``n`` (int).
            n (int): Current sample count.
            indent (int): Indentation level.

        Returns:
            tuple[str, int]: A connection suffix string and the
            updated sample count.
        """
        connection = ""
        for i, exclusion in enumerate(exclusions):
            n -= exclusion["n"]
            eid = self._next_exclusion_id()
            self._emit_node(eid, exclusion["reason"], exclusion["n"], indent)
            self._exclusion_ids.append(eid)
            arrow = EXCLUSION_ARROW_LONG if i == 0 else EXCLUSION_ARROW
            connection += arrow + eid
        return connection, n

    def _process_subgraph(
        self, step: dict, n: int, indent: int
    ) -> tuple[str, int]:
        """Process a subgraph block.

        The step's ``name`` becomes the subgraph label. Sub-steps are
        processed recursively, supporting exclusions and nested
        subgraphs.

        Args:
            step (dict): The step definition containing a ``subgraph``
                key.
            n (int): Current sample count.
            indent (int): Indentation level.

        Returns:
            tuple[str, int]: The subgraph ID and the updated sample
            count.
        """
        sg_id = self._next_subgraph_id()
        label = step.get("name", "")
        subgraph_def = step["subgraph"]
        direction = subgraph_def.get("direction", "TD")
        self._subgraph_ids.append(sg_id)

        self._body_lines.append(INDENT * indent + f"subgraph {sg_id} [{label}]")
        self._body_lines.append(
            INDENT * (indent + 1) + f"direction {direction}"
        )

        inner_conn, n = self._process_steps(
            subgraph_def["steps"], n, indent + 1, in_subgraph=True
        )
        if inner_conn:
            self._body_lines.append(INDENT * (indent + 1) + inner_conn)

        self._body_lines.append(INDENT * indent + "end")
        return sg_id, n

    def _process_steps(
        self,
        steps: list[dict],
        n: int,
        indent: int = 1,
        in_subgraph: bool = False,
    ) -> tuple[str, int]:
        """Process a list of steps.

        Each step may contain ``exclusions`` and/or a ``subgraph`` of
        sub-steps. Exclusions are processed first (decrementing ``n``),
        then the step node or subgraph is created with the updated
        ``n``.

        Args:
            steps (list[dict]): List of step definitions.
            n (int): Current sample count.
            indent (int, optional): Indentation level. Defaults to 1.
            in_subgraph (bool, optional): Whether these steps are
                inside a subgraph. Defaults to False.

        Returns:
            tuple[str, int]: A connection string and the updated
            sample count.
        """
        parts: list[str] = []
        default_arrow = " --> " if in_subgraph else ARROW

        for step in steps:
            link = step.get("link", "default")
            parent_n = n
            excl_conn = ""

            if "exclusions" in step:
                excl_conn, n = self._process_exclusions(
                    step["exclusions"], n, indent
                )
                if link != "none":
                    parts.append(excl_conn)

            node_n = n

            if "subgraph" in step:
                sg_id, sub_n = self._process_subgraph(step, node_n, indent)
                n = parent_n if link == "none" else sub_n
                if link != "none":
                    arrow = link if link != "default" else default_arrow
                    parts.append(f" {arrow.strip()} " + sg_id)
                elif excl_conn:
                    standalone = (
                        excl_conn + f" {default_arrow.strip()} " + sg_id
                    ).lstrip(" ->-")
                    self._body_lines.append(INDENT * indent + standalone)
            else:
                step_id = self._next_step_id()
                self._emit_node(step_id, step["name"], node_n, indent)
                self._step_ids.append(step_id)
                n = parent_n if link == "none" else n
                if link != "none":
                    arrow = link if link != "default" else default_arrow
                    parts.append(f" {arrow.strip()} " + step_id)
                elif excl_conn:
                    standalone = (
                        excl_conn + f" {default_arrow.strip()} " + step_id
                    ).lstrip(" ->-")
                    self._body_lines.append(INDENT * indent + standalone)

        connection = "".join(parts).lstrip(" ->-")
        return connection, n

    def build(self, data: dict) -> str:
        """
        Build the complete Mermaid flowchart string.

        Args:
            data (dict): Parsed YAML data with ``n`` (int) and
                ``steps`` (list[dict]) keys.

        Returns:
            str: A complete Mermaid flowchart string.
        """
        n = data["n"]
        connection, _ = self._process_steps(data["steps"], n)

        lines = [HEADER, ""]
        lines.extend(self._body_lines)
        lines.append(INDENT + connection)
        if self._step_ids:
            lines.append(f"{INDENT}class " + ",".join(self._step_ids) + " step")
        if self._exclusion_ids:
            lines.append(
                f"{INDENT}class " + ",".join(self._exclusion_ids) + " exclusion"
            )
        if self._subgraph_ids:
            lines.append(
                f"{INDENT}class " + ",".join(self._subgraph_ids) + " sg"
            )
        return "\n".join(lines)
