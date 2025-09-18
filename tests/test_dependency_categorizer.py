import pytest

from dependency_scanner_tool.categorization import DependencyCategorizer


def test_category_without_dependencies_is_preserved():
    config = {
        "categories": {
            "OnlyAPI": {
                "api_patterns": ["https://example.com/*"],
                "status": "allowed",
            }
        }
    }

    categorizer = DependencyCategorizer(config)

    assert "OnlyAPI" in categorizer.categories
    assert categorizer.categories["OnlyAPI"] == []
