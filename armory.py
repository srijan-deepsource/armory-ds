"""Custom DeepSource analyzer definition."""
import json
import os
import subprocess
import sys
import tempfile

import tomlkit as toml


CATEGORIES = (
    "bug-risk",
    "doc",
    "style",
    "antipattern",
    "coverage",
    "security",
    "performance",
    "typecheck",
)

WORKSPACE_PATH = os.environ.get("CODE_PATH", "/code")


def prepare_result(issues):
    """Prepare the result for the DeepSource analyzer framework to publish."""
    return {
        "issues": issues,
        "metrics": [],
        "is_passed": True if issues else False,
        "errors": [],
        "extra_data": ""
    }


def publish_results(result):
    """Publish the analysis results."""
    # write results into a json file:
    res_file = tempfile.NamedTemporaryFile().name
    with open(res_file, "w") as fp:
        fp.write(json.dumps(result))

    # publish result via marvin:
    subprocess.run(["/toolbox/marvin", "--publish-report", res_file])

def get_vcs_filepath(filepath):
    """Remove the /code/ prefix."""
    if filepath.startswith("/code/"):
        filepath = filepath[6:]

    return filepath


def get_issue_struct(issue_code, issue_txt, filepath, line, col):
    """Prepare issue structure for the given issue data."""
    filepath = get_vcs_filepath(filepath)
    return {
        "issue_code": issue_code,
        "issue_text": issue_txt,
        "location": {
            "path": filepath,
            "position": {
                "begin": {
                    "line": line,
                    "column": col
                },
                "end": {
                    "line": line,
                    "column": col
                }
            }
        }
    }


def main():
    """Validate the issue toml files."""
    issues_dir = os.path.join(
        WORKSPACE_PATH,
        ".deepsource/analyzer/issues"
    )

    issues = []

    for dir_path, _, filenames in os.walk(issues_dir):
        for filename in filenames:
            filepath = os.path.join(dir_path, filename)
            with open(filepath) as fp:
                try:
                    data = toml.loads(fp.read())
                except Exception as exc:  # skipcq: PYL-W0703
                    # Can not decode toml file. Raise an issue.
                    # Details are in exc.
                    issues.append(
                        get_issue_struct(
                            "ARMORY-003",
                            f"Error decoding toml: {str(exc)}",
                            filepath,
                            1,
                            0
                        )
                    )

                    continue

                # Do not check this file if the issue is archived
                if data.get("archived"):
                    continue

                # Check for issue title:
                title = data.get("title")
                if not title:
                    issues.append(
                        get_issue_struct(
                            "ARMORY-001",
                            f"Missing title for issue.",
                            filepath,
                            1,
                            0
                        )
                    )
                else:
                    if title.endswith("."):
                        issues.append(
                            get_issue_struct(
                                "ARMORY-001",
                                f"Title should not end with a period.",
                                filepath,
                                1,
                                0
                            )
                        )

                # check for category
                category = data.get("category")
                if not category:
                    issues.append(
                        get_issue_struct(
                            "ARMORY-002",
                            f"Missing category field.",
                            filepath,
                            1,
                            0
                        )
                    )

                elif category not in CATEGORIES:
                    issues.append(
                        get_issue_struct(
                            "ARMORY-002",
                            f"Invalid category field",
                            filepath,
                            1,
                            0
                        )
                    )

    result = prepare_result(issues)

    # publish result:
    publish_results(result)

if __name__ == "__main__":
    main()
