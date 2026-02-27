'''
Copyright 2025 Advanced Micro Devices, Inc.
All rights reserved. This notice is intended as a precaution against inadvertent publication and does not imply publication or any waiver of confidentiality.
The year included in the foregoing notice is the year of creation of the work.
All code contained here is Property of Advanced Micro Devices, Inc.
'''

import datetime
import importlib.metadata
import shutil
import sys
import zipfile
from pathlib import Path

import pytest
import pytest_html


# This function is executed by pytest before any tests or hooks are collected/executed,
# after command-line options are parsed but before collection starts.
# Specifically, pytest_configure is called during pytest's setup phase, once per test session.
# The tryfirst=True ensures this hook runs as early as possible among all plugins.
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if config.args:
        suite_name = Path(config.args[0]).stem
    else:
        suite_name = "test"
    config._test_html_dir = f"{suite_name}_html"

# Add all additional cmd line arguments for the script
def pytest_addoption(parser):
    # Check if options already exist (they might be added by cvs core package)
    try:
        parser.addoption(
            "--cluster_file",
            action="store",
            required=True,
            help="Input file with all the details of the cluster, nodes, switches in JSON format",
        )
    except ValueError:
        # Option already exists, skip
        pass

    try:
        parser.addoption(
            "--config_file",
            action="store",
            required=True,
            help="Input file with all configurations and parameters for tests in JSON format",
        )
    except ValueError:
        # Option already exists, skip
        pass


def pytest_metadata(metadata):
    """Add CVS version metadata for both console output and HTML report."""

    # Get CVS version - try package metadata first, fallback to version.txt
    try:
        cvs_version = importlib.metadata.version('cvs')
    except importlib.metadata.PackageNotFoundError:
        # Fallback for development mode (running from cloned repo)
        try:
            version_file = Path(__file__).parent.parent / "version.txt"
            cvs_version = version_file.read_text().strip()
        except Exception as e:
            cvs_version = f"Unknown (Error: {e})"

    # Get command line arguments directly from sys.argv
    cluster_file = "Not specified"
    config_file = "Not specified"

    # Parse command line arguments to get our custom options
    for i, arg in enumerate(sys.argv):
        if arg == "--cluster_file" and i + 1 < len(sys.argv):
            cluster_file = sys.argv[i + 1]
        elif arg == "--config_file" and i + 1 < len(sys.argv):
            config_file = sys.argv[i + 1]

    # Add custom metadata
    metadata['CVS version'] = cvs_version
    metadata['Cluster File'] = cluster_file
    metadata['Config File'] = config_file

# Remove stale test_html directory from a previous run and create a fresh one.
# This hook is executed by pytest at the very start of a test session, before any test collection or execution.
def pytest_sessionstart(session):
    htmlpath = getattr(session.config.option, "htmlpath", None)
    if not htmlpath:
        return

    log_dir = Path(htmlpath).resolve().parent / session.config._test_html_dir
    if log_dir.is_dir():
        try:
            shutil.rmtree(log_dir)
        except Exception:
            pass
    log_dir.mkdir(parents=True, exist_ok=True)


# hook to create a log file link for each test
# The call parameter is required by pytest's hook signature
# noqa: ARG001 comment tells the linter to suppress the "unused argument" warning for this line.
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):  # noqa: ARG001
    outcome = yield
    report = outcome.get_result()

    # Get or initialize the extras list for this report.
    extras = getattr(report, "extras", [])

    # Check if HTML reporting is enabled and this is after the test function runs.
    htmlpath = getattr(item.config.option, "htmlpath", None)
    if report.when == "call" and htmlpath:
        htmlpath = Path(htmlpath)

        # Construct a safe file name for the log based on nodeid, skipping the test module part
        nodeid_parts = report.nodeid.split("::")
        if len(nodeid_parts) > 1:
            # drop first part (the test module), then join back
            reduced_nodeid = "::".join(nodeid_parts[1:])
        else:
            reduced_nodeid = report.nodeid
        safe_name = reduced_nodeid.replace("::", "_").replace("/", "_").replace("\\", "_")

        # Use the designated per-run log directory, next to the HTML report.
        log_dir = htmlpath.parent / item.config._test_html_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{safe_name}.html"

        # Gather the captured sections for this test into HTML snippets.
        log_content = []
        for section_name, section_content in report.sections:
            log_content.append(f"<h3>{section_name}</h3><pre>{section_content}</pre>")

        if log_content:
            # Write a standalone HTML file with all logs for this test.
            log_path.write_text(
                f"<html><body><h1>{report.nodeid}</h1>{''.join(log_content)}</body></html>",
                encoding="utf-8",
            )

            # Add a relative URL link to the HTML report's 'extras', so it appears in the report UI.
            rel_path = log_path.relative_to(htmlpath.parent)
            extras.append(pytest_html.extras.url(str(rel_path), name="Full Log"))

        # Update the report's extras so this is available in the report.
        report.extras = extras

# This function is needed to override the default log display for each test row in the pytest-html results table.
# By default, pytest-html tries to show captured log output and sections directly in the report table cell,
# but in this setup, detailed logs are externalized to per-test HTML files (see pytest_runtest_makereport above).
# This hook customizes the HTML table cell for each test log so it does not redundantly display any log output directly in the table,
# and instead shows a message directing the user to the dedicated log file link (added as an "extra" in pytest_runtest_makereport).
# Without this function, the user experience would be cluttered, since both "Full Log" links AND inline logs would appear together.
def pytest_html_results_table_html(report, data):
    del data[:]  # Remove inline log content that pytest-html would show by default
    if report.failed:
        data.append("<div class='empty log'>See 'Full Log' link for details.</div>")
    else:
        data.append("<div class='empty log'>Log externalized (see link above).</div>")

# Style the HTML report to hide the "show details" and "hide details" functionality
def pytest_html_results_summary(prefix, summary, postfix):
    prefix.extend(["""<style>
        .collapse { display: none !important; }
        .col-result:hover::after { content: none !important; }
        .col-result.collapsed:hover::after { content: none !important; }
        .collapsible td:not(.col-links) { cursor: default !important; }
        .extras-row { display: none !important; }
    </style>"""])


# This pytest hook is called when the test session finishes. It waits until all plugins
# (such as pytest-html) have completed writing reports, then bundles the main HTML report and
# all per-test log files (if any exist) into a timestamped zip archive. The zip file is named
# with the suite name (or report file stem) and a timestamp, and is saved next to the HTML report.
@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    yield  # wait for pytest-html and all other plugins to finish writing the report

    htmlpath = getattr(session.config.option, "htmlpath", None)
    if not htmlpath:
        return

    htmlpath = Path(htmlpath).resolve()
    if not htmlpath.is_file():
        return

    report_dir = htmlpath.parent
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    # Use the suite name and timestamp for the zip file name
    suite_name = getattr(session.config, "invocation_params", None)
    if suite_name and hasattr(suite_name, "args") and suite_name.args:
        suite_name_part = Path(suite_name.args[0]).stem
    else:
        suite_name_part = htmlpath.stem
    zip_path = report_dir / f"{suite_name_part}_{timestamp}.zip"
    test_html_dir = session.config._test_html_dir
    log_dir = report_dir / test_html_dir

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(htmlpath, htmlpath.name)

        if log_dir.is_dir():
            for filepath in sorted(log_dir.iterdir()):
                if filepath.is_file():
                    zf.write(filepath, Path(test_html_dir) / filepath.name)