"""Tests for the consort_yaml package."""

import pytest

from consort_yaml import FlowchartBuilder


@pytest.fixture
def simple_data():
    """Return a minimal YAML-like dict for testing."""
    return {
        "n": 100,
        "steps": [
            {"name": "Step A"},
            {"name": "Step B"},
        ],
    }


@pytest.fixture
def exclusions_data():
    """Return data with exclusions."""
    return {
        "n": 100,
        "steps": [
            {"name": "Step A"},
            {
                "name": "Step B",
                "exclusions": [
                    {"reason": "Reason 1", "n": 10},
                    {"reason": "Reason 2", "n": 5},
                ],
            },
        ],
    }


@pytest.fixture
def subgraph_data():
    """Return data with a subgraph."""
    return {
        "n": 100,
        "steps": [
            {"name": "Step A"},
            {
                "name": "Subgraph",
                "subgraph": {
                    "direction": "LR",
                    "steps": [
                        {"name": "Sub-step A"},
                        {"name": "Sub-step B"},
                    ],
                },
            },
        ],
    }


@pytest.fixture
def link_none_data():
    """Return data with link: none steps."""
    return {
        "n": 100,
        "steps": [
            {"name": "Step A"},
            {
                "name": "Step B",
                "link": "none",
                "exclusions": [
                    {"reason": "Excluded", "n": 20},
                ],
            },
            {"name": "Step C"},
        ],
    }


class TestFlowchartBuilderBasics:
    """Tests for basic FlowchartBuilder functionality."""

    def test_build_returns_string(self, simple_data):
        """Test that build returns a non-empty string."""
        builder = FlowchartBuilder()
        result = builder.build(simple_data)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_contains_header(self, simple_data):
        """Test that the output contains the Mermaid header."""
        builder = FlowchartBuilder()
        result = builder.build(simple_data)
        assert "flowchart TD" in result
        assert "classDef" in result

    def test_build_contains_step_nodes(self, simple_data):
        """Test that step nodes are present in the output."""
        builder = FlowchartBuilder()
        result = builder.build(simple_data)
        assert "step0" in result
        assert "step1" in result
        assert "Step A" in result
        assert "Step B" in result

    def test_build_contains_n_values(self, simple_data):
        """Test that n values are included in node labels."""
        builder = FlowchartBuilder()
        result = builder.build(simple_data)
        assert "(n=100)" in result

    def test_build_contains_class_assignments(self, simple_data):
        """Test that class assignments are present."""
        builder = FlowchartBuilder()
        result = builder.build(simple_data)
        assert "class step0,step1 step" in result


class TestExclusions:
    """Tests for exclusion handling."""

    def test_exclusion_nodes_present(self, exclusions_data):
        """Test that exclusion nodes are created."""
        builder = FlowchartBuilder()
        result = builder.build(exclusions_data)
        assert "exclusion0" in result
        assert "exclusion1" in result
        assert "Reason 1" in result
        assert "Reason 2" in result

    def test_exclusion_decrements_n(self, exclusions_data):
        """Test that exclusions decrement the sample count."""
        builder = FlowchartBuilder()
        result = builder.build(exclusions_data)
        assert "(n=85)" in result

    def test_exclusion_class_assignment(self, exclusions_data):
        """Test that exclusion nodes get the exclusion class."""
        builder = FlowchartBuilder()
        result = builder.build(exclusions_data)
        assert "class exclusion0,exclusion1 exclusion" in result


class TestSubgraphs:
    """Tests for subgraph handling."""

    def test_subgraph_present(self, subgraph_data):
        """Test that a subgraph is created in the output."""
        builder = FlowchartBuilder()
        result = builder.build(subgraph_data)
        assert "subgraph sg0" in result
        assert "direction LR" in result
        assert "end" in result

    def test_subgraph_class_assignment(self, subgraph_data):
        """Test that subgraphs get the sg class."""
        builder = FlowchartBuilder()
        result = builder.build(subgraph_data)
        assert "class sg0 sg" in result

    def test_subgraph_steps_present(self, subgraph_data):
        """Test that sub-step nodes are created inside the subgraph."""
        builder = FlowchartBuilder()
        result = builder.build(subgraph_data)
        assert "Sub-step A" in result
        assert "Sub-step B" in result


class TestLinkNone:
    """Tests for link: none behaviour."""

    def test_link_none_preserves_parent_n(self, link_none_data):
        """Test that link: none steps use parent n for the next step."""
        builder = FlowchartBuilder()
        result = builder.build(link_none_data)
        # Step B should show n=80 (100 - 20 exclusion)
        assert "(n=80)" in result
        # Step C should show n=100 (parent n, not decremented)
        assert "(n=100)" in result

    def test_link_none_not_in_main_connection(self, link_none_data):
        """Test that link: none steps are not in the main chain."""
        builder = FlowchartBuilder()
        result = builder.build(link_none_data)
        # The main connection should contain step0 and step2
        # but step1 should not be chained between them
        lines = result.split("\n")
        main_conn = [
            line for line in lines if "step0" in line and "--->" in line
        ]
        assert main_conn
        # step1 should not appear in the main connection line
        assert "step1" not in main_conn[0]

    def test_link_none_exclusions_still_emitted(self, link_none_data):
        """Test that exclusions are still emitted for link: none steps."""
        builder = FlowchartBuilder()
        result = builder.build(link_none_data)
        assert "exclusion0" in result
        assert "Excluded" in result


class TestNestedSubgraphs:
    """Tests for nested subgraphs."""

    def test_nested_subgraph(self):
        """Test that nested subgraphs are rendered correctly."""
        data = {
            "n": 100,
            "steps": [
                {
                    "name": "Outer",
                    "subgraph": {
                        "direction": "LR",
                        "steps": [
                            {
                                "name": "Inner",
                                "subgraph": {
                                    "direction": "TD",
                                    "steps": [
                                        {"name": "Deep step"},
                                    ],
                                },
                            },
                        ],
                    },
                },
            ],
        }
        builder = FlowchartBuilder()
        result = builder.build(data)
        assert "subgraph sg0" in result
        assert "subgraph sg1" in result
        assert "Deep step" in result
        assert "class sg0,sg1 sg" in result


class TestCustomIds:
    """Tests for custom id overrides."""

    def test_custom_step_id(self):
        """Test that a custom step id is used instead of auto-generated."""
        data = {
            "n": 100,
            "steps": [
                {"name": "Step A", "id": "my_custom_id"},
            ],
        }
        builder = FlowchartBuilder()
        result = builder.build(data)
        assert "my_custom_id" in result
        assert "step0" not in result

    def test_custom_exclusion_id(self):
        """Test that a custom exclusion id is used."""
        data = {
            "n": 100,
            "steps": [
                {
                    "name": "Step A",
                    "exclusions": [
                        {
                            "reason": "Reason",
                            "n": 5,
                            "id": "my_excl_id",
                        },
                    ],
                },
            ],
        }
        builder = FlowchartBuilder()
        result = builder.build(data)
        assert "my_excl_id" in result
        assert "exclusion0" not in result

    def test_custom_subgraph_id(self):
        """Test that a custom subgraph id is used."""
        data = {
            "n": 100,
            "steps": [
                {
                    "name": "Subgraph",
                    "id": "my_sg",
                    "subgraph": {
                        "direction": "LR",
                        "steps": [
                            {"name": "Sub-step"},
                        ],
                    },
                },
            ],
        }
        builder = FlowchartBuilder()
        result = builder.build(data)
        assert "subgraph my_sg" in result
        assert "sg0" not in result

    def test_custom_id_in_class_assignment(self):
        """Test that custom ids appear in class assignments."""
        data = {
            "n": 100,
            "steps": [
                {"name": "Step A", "id": "custom_a"},
                {"name": "Step B", "id": "custom_b"},
            ],
        }
        builder = FlowchartBuilder()
        result = builder.build(data)
        assert "class custom_a,custom_b step" in result


class TestAdditionalLinks:
    """Tests for additional_links feature."""

    def test_additional_links_present(self):
        """Test that additional links are appended to the output."""
        data = {
            "n": 100,
            "steps": [
                {"name": "Step A", "id": "node_a"},
                {"name": "Step B", "id": "node_b"},
            ],
            "additional_links": [
                "node_a -.-> node_b",
            ],
        }
        builder = FlowchartBuilder()
        result = builder.build(data)
        assert "node_a -.-> node_b" in result

    def test_no_additional_links(self):
        """Test that output is fine without additional_links."""
        data = {
            "n": 100,
            "steps": [
                {"name": "Step A"},
            ],
        }
        builder = FlowchartBuilder()
        result = builder.build(data)
        assert isinstance(result, str)

    def test_multiple_additional_links(self):
        """Test that multiple additional links are all present."""
        data = {
            "n": 100,
            "steps": [
                {"name": "A", "id": "a"},
                {"name": "B", "id": "b"},
                {"name": "C", "id": "c"},
            ],
            "additional_links": [
                "a -.-> b",
                "b ---> c",
                "a ---> c",
            ],
        }
        builder = FlowchartBuilder()
        result = builder.build(data)
        assert "a -.-> b" in result
        assert "b ---> c" in result
        assert "a ---> c" in result
