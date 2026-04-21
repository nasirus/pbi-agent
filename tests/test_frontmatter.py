from __future__ import annotations

import pytest

from pbi_agent.frontmatter import FrontmatterParseError, parse_simple_frontmatter


def test_literal_block_scalars_strip_shared_indent() -> None:
    metadata = parse_simple_frontmatter(
        "description: |\n  line1\n  line2\nname: compress\n",
        block_scalar_keys=frozenset({"description"}),
    )

    assert metadata["description"] == "line1\nline2"


def test_block_scalars_are_rejected_for_disallowed_keys() -> None:
    with pytest.raises(
        FrontmatterParseError,
        match="unsupported block scalar for key 'name'",
    ):
        parse_simple_frontmatter(
            "name: >\n  foo\n  bar\ndescription: ok\n",
            block_scalar_keys=frozenset({"description"}),
        )
