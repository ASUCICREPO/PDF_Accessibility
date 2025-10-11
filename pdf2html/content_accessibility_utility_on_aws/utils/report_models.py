# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Pydantic models for accessibility audit and remediation reports.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    """Enum for issue severity levels."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class IssueStatus(str, Enum):
    """Enum for audit issue status."""

    REPORTED = "reported"
    COMPLIANT = "compliant"


class RemediationStatus(str, Enum):
    """Enum for remediation status."""

    REMEDIATED = "remediated"
    FAILED = "failed"
    NEEDS_REMEDIATION = "needs_remediation"


class Location(BaseModel):
    """Model for issue location."""

    file_path: Optional[str] = None
    path: Optional[str] = None
    index: Optional[int] = None
    image_src: Optional[str] = None


class BaseIssue(BaseModel):
    """Base model for accessibility issues."""

    id: Optional[str] = None
    type: str
    severity: Union[Severity, str]
    message: str
    selector: Optional[str] = None
    context: Optional[Union[Dict[str, Any], str]] = None
    location: Optional[Location] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        """Configuration for BaseIssue model."""

        arbitrary_types_allowed = True
        use_enum_values = True


class AuditIssue(BaseIssue):
    """Model for audit-specific issue details."""

    status: Optional[Union[IssueStatus, str]] = IssueStatus.REPORTED
    help_text: Optional[str] = None
    standards_reference: Optional[str] = None


class RemediationDetails(BaseModel):
    """Model for remediation details."""

    description: Optional[str] = None
    fix_description: Optional[str] = None
    before_content: Optional[str] = None
    after_content: Optional[str] = None
    failure_reason: Optional[str] = None


class RemediationIssue(BaseIssue):
    """Model for remediation-specific issue details."""

    remediation_status: Union[RemediationStatus, str]
    remediation_details: Optional[RemediationDetails] = Field(
        default_factory=RemediationDetails
    )


class BaseSummary(BaseModel):
    """Base model for report summaries."""

    total_issues: int
    severity_counts: Dict[str, int] = Field(
        default_factory=lambda: {"critical": 0, "major": 0, "minor": 0, "info": 0}
    )
    issue_type_stats: Dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)


class AuditSummary(BaseSummary):
    """Model for audit-specific summary details."""

    needs_remediation: int = 0
    compliant: int = 0


class RemediationSummary(BaseSummary):
    """Model for remediation-specific summary details."""

    issues_processed: int = 0
    remediated_issues: int = 0
    failed_issues: int = 0


class BaseReport(BaseModel):
    """Base model for accessibility reports."""

    html_path: str
    summary: BaseSummary
    issues: List[BaseIssue]

    class Config:
        """Configuration for BaseReport model."""

        arbitrary_types_allowed = True


class AuditReport(BaseReport):
    """Model for audit reports."""

    summary: AuditSummary
    issues: List[AuditIssue]


class RemediationReport(BaseReport):
    """Model for remediation reports."""

    remediated_html_path: str
    summary: RemediationSummary
    issues: List[RemediationIssue]


def create_audit_summary(issues: List[AuditIssue]) -> AuditSummary:
    """
    Create an audit summary from a list of audit issues.

    Args:
        issues: List of AuditIssue objects

    Returns:
        AuditSummary object with calculated statistics
    """
    severity_counts = {"critical": 0, "major": 0, "minor": 0, "info": 0}
    issue_type_stats = {}
    needs_remediation = 0
    compliant = 0

    for issue in issues:
        # Count by severity
        severity = issue.severity
        if severity in severity_counts:
            severity_counts[severity] += 1

        # Count by type
        issue_type = issue.type
        if issue_type not in issue_type_stats:
            issue_type_stats[issue_type] = 0
        issue_type_stats[issue_type] += 1

        # Count by status
        if getattr(
            issue, "status", None
        ) == IssueStatus.COMPLIANT or issue_type.startswith("compliant-"):
            compliant += 1
        else:
            needs_remediation += 1

    return AuditSummary(
        total_issues=len(issues),
        severity_counts=severity_counts,
        issue_type_stats=issue_type_stats,
        needs_remediation=needs_remediation,
        compliant=compliant,
        generated_at=datetime.now(),
    )


def create_remediation_summary(
    issues: List[RemediationIssue], report_data: Optional[Dict] = None
) -> RemediationSummary:
    """
    Create a remediation summary from a list of remediation issues.

    Args:
        issues: List of RemediationIssue objects
        report_data: Optional raw report data containing top-level counts

    Returns:
        RemediationSummary object with calculated statistics
    """
    severity_counts = {"critical": 0, "major": 0, "minor": 0, "info": 0}
    issue_type_stats = {}
    remediated_issues = 0
    failed_issues = 0

    # First, count based on actual issues in issues array
    for issue in issues:
        # Count by severity
        severity = issue.severity
        if severity in severity_counts:
            severity_counts[severity] += 1

        # Count by type
        issue_type = issue.type
        if issue_type not in issue_type_stats:
            issue_type_stats[issue_type] = 0
        issue_type_stats[issue_type] += 1

        # Count by remediation status
        if issue.remediation_status == RemediationStatus.REMEDIATED:
            remediated_issues += 1
        else:
            failed_issues += 1

    # If we have file-level data, use that for processed/remediated counts since it's more accurate
    issues_processed = len(issues)
    remediated_count = remediated_issues
    failed_count = failed_issues

    if report_data:
        # Top-level counts from original data
        if "issues_processed" in report_data and report_data["issues_processed"] > 0:
            issues_processed = report_data["issues_processed"]

        # File-level counts from original data (more accurate for multi-page docs)
        file_results = report_data.get("file_results", [])
        if file_results:
            file_remediated = sum(f.get("issues_remediated", 0) for f in file_results)
            file_failed = sum(f.get("issues_failed", 0) for f in file_results)
            file_processed = sum(f.get("issues_processed", 0) for f in file_results)

            if file_processed > 0:
                # Use file-level counts if they exist and are non-zero
                remediated_count = file_remediated
                failed_count = file_failed
                issues_processed = file_processed

        # If top-level counts exist, use them (fallback)
        if remediated_count == 0 and "issues_remediated" in report_data:
            remediated_count = report_data.get("issues_remediated", 0)

        if failed_count == 0 and "issues_failed" in report_data:
            failed_count = report_data.get("issues_failed", 0)

    return RemediationSummary(
        total_issues=issues_processed,
        severity_counts=severity_counts,
        issue_type_stats=issue_type_stats,
        issues_processed=issues_processed,
        remediated_issues=remediated_count,
        failed_issues=failed_count,
        generated_at=datetime.now(),
    )


def dict_to_audit_issue(issue_dict: Dict[str, Any]) -> AuditIssue:
    """
    Convert a dictionary to an AuditIssue object.

    Args:
        issue_dict: Dictionary containing issue data

    Returns:
        AuditIssue object
    """
    # Handle location if it exists
    location = None
    if issue_dict.get("location"):
        location = Location(**issue_dict["location"])

    # Create the issue with all fields that match the model
    return AuditIssue(
        id=issue_dict.get("id"),
        type=issue_dict.get("type", "unknown"),
        severity=issue_dict.get("severity", "minor"),
        message=issue_dict.get("message", ""),
        selector=issue_dict.get("selector"),
        context=issue_dict.get("context"),
        location=location,
        status=issue_dict.get("status", "reported"),
        help_text=issue_dict.get("help_text"),
        standards_reference=issue_dict.get("standards_reference"),
    )


def dict_to_remediation_issue(issue_dict: Dict[str, Any]) -> RemediationIssue:
    """
    Convert a dictionary to a RemediationIssue object.

    Args:
        issue_dict: Dictionary containing issue data

    Returns:
        RemediationIssue object
    """
    # Handle location if it exists
    location = None
    if issue_dict.get("location"):
        location = Location(**issue_dict["location"])

    # Handle remediation details
    remediation_details = None
    if issue_dict.get("remediation_details"):
        remediation_details = RemediationDetails(**issue_dict["remediation_details"])

    # Determine remediation status
    remediation_status = issue_dict.get("remediation_status")
    if not remediation_status:
        # Try to determine from other fields
        if issue_dict.get("remediated") is True or issue_dict.get("success") is True:
            remediation_status = RemediationStatus.REMEDIATED
        elif issue_dict.get("failure_reason") or issue_dict.get("error"):
            remediation_status = RemediationStatus.FAILED
        else:
            remediation_status = RemediationStatus.NEEDS_REMEDIATION

    # Create the issue with all fields that match the model
    return RemediationIssue(
        id=issue_dict.get("id"),
        type=issue_dict.get("type", "unknown"),
        severity=issue_dict.get("severity", "minor"),
        message=issue_dict.get("message", ""),
        selector=issue_dict.get("selector"),
        context=issue_dict.get("context"),
        location=location,
        remediation_status=remediation_status,
        remediation_details=remediation_details,
    )
