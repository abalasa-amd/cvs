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

def pytest_sessionstart(session):
    """Remove stale test_html directory from a previous run and create a fresh one."""
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


# Add a hook to create a log file link for each test
# The call parameter is required by pytest's hook signature
# noqa: ARG001 comment tells the linter to suppress the "unused argument" warning for this line.
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):  # noqa: ARG001
    outcome = yield
    report = outcome.get_result()
    extras = getattr(report, "extras", [])

    htmlpath = getattr(item.config.option, "htmlpath", None)
    if report.when == "call" and htmlpath:
        htmlpath = Path(htmlpath)
        safe_name = report.nodeid.replace("::", "_").replace("/", "_").replace("\\", "_")
        log_dir = htmlpath.parent / item.config._test_html_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{safe_name}.html"

        # Collect all captured log sections into the external file
        log_content = []
        for section_name, section_content in report.sections:
            log_content.append(f"<h3>{section_name}</h3><pre>{section_content}</pre>")

        if log_content:
            log_path.write_text(
                f"<html><body><h1>{report.nodeid}</h1>{''.join(log_content)}</body></html>",
                encoding="utf-8",
            )

            rel_path = log_path.relative_to(htmlpath.parent)
            extras.append(pytest_html.extras.url(str(rel_path), name="Full Log"))

        report.extras = extras

# Display the log file link in the HTML report
def pytest_html_results_table_html(report, data):
    del data[:]
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


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Bundle the HTML report and per-test log files into a zip archive."""
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