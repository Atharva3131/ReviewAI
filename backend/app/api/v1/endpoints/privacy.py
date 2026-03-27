"""
Privacy and compliance API endpoints
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.consent_management import ConsentMethod, ConsentType, get_consent_service
from app.core.database import get_db
from app.core.dependencies import get_current_organization, get_current_user
from app.core.gdpr_compliance import GDPRRights, get_gdpr_service
from app.core.privacy_policy import PolicyType, get_privacy_policy_service
from app.models.organization import Organization
from app.models.user import User
from app.schemas.base import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# Privacy Policy Endpoints


@router.get("/privacy-policy", response_class=HTMLResponse)
async def get_privacy_policy(
    org: str = Query(..., description="Organization ID"),
    format: str = Query("html", description="Response format: html or json"),
):
    """Get privacy policy for organization"""
    try:
        privacy_service = get_privacy_policy_service()

        if format == "json":
            policy = privacy_service.get_policy_for_display(
                org, PolicyType.PRIVACY_POLICY, "json"
            )
            if not policy:
                raise HTTPException(status_code=404, detail="Privacy policy not found")
            return policy
        else:
            policy = privacy_service.get_policy_for_display(
                org, PolicyType.PRIVACY_POLICY, "html"
            )
            if not policy:
                raise HTTPException(status_code=404, detail="Privacy policy not found")
            return HTMLResponse(content=policy["content"])

    except Exception as e:
        logger.error(f"Error retrieving privacy policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve privacy policy")


@router.get("/terms-of-service", response_class=HTMLResponse)
async def get_terms_of_service(
    org: str = Query(..., description="Organization ID"),
    format: str = Query("html", description="Response format: html or json"),
):
    """Get terms of service for organization"""
    try:
        privacy_service = get_privacy_policy_service()

        if format == "json":
            policy = privacy_service.get_policy_for_display(
                org, PolicyType.TERMS_OF_SERVICE, "json"
            )
            if not policy:
                raise HTTPException(
                    status_code=404, detail="Terms of service not found"
                )
            return policy
        else:
            policy = privacy_service.get_policy_for_display(
                org, PolicyType.TERMS_OF_SERVICE, "html"
            )
            if not policy:
                raise HTTPException(
                    status_code=404, detail="Terms of service not found"
                )
            return HTMLResponse(content=policy["content"])

    except Exception as e:
        logger.error(f"Error retrieving terms of service: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve terms of service"
        )


@router.get("/cookie-policy", response_class=HTMLResponse)
async def get_cookie_policy(
    org: str = Query(..., description="Organization ID"),
    format: str = Query("html", description="Response format: html or json"),
):
    """Get cookie policy for organization"""
    try:
        privacy_service = get_privacy_policy_service()

        if format == "json":
            policy = privacy_service.get_policy_for_display(
                org, PolicyType.COOKIE_POLICY, "json"
            )
            if not policy:
                raise HTTPException(status_code=404, detail="Cookie policy not found")
            return policy
        else:
            policy = privacy_service.get_policy_for_display(
                org, PolicyType.COOKIE_POLICY, "html"
            )
            if not policy:
                raise HTTPException(status_code=404, detail="Cookie policy not found")
            return HTMLResponse(content=policy["content"])

    except Exception as e:
        logger.error(f"Error retrieving cookie policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cookie policy")


@router.get("/policies/summary")
async def get_policy_summary(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Get summary of all policies for organization"""
    try:
        privacy_service = get_privacy_policy_service()
        summary = privacy_service.generate_policy_summary(str(organization.id))

        return BaseResponse(
            success=True, data=summary, message="Policy summary retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Error retrieving policy summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve policy summary")


# GDPR Compliance Endpoints


@router.post("/gdpr/request")
async def submit_gdpr_request(request_data: Dict[str, Any], request: Request):
    """Submit GDPR data subject request"""
    try:
        gdpr_service = get_gdpr_service()

        # Extract request details
        email = request_data.get("email")
        organization_id = request_data.get("organization_id")
        request_type = request_data.get("request_type")
        details = request_data.get("details", "")

        if not email or not organization_id or not request_type:
            raise HTTPException(
                status_code=400,
                detail="Email, organization_id, and request_type are required",
            )

        # Validate request type
        try:
            gdpr_right = GDPRRights(request_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request type")

        # Submit request
        request_id = await gdpr_service.submit_gdpr_request(
            data_subject_email=email,
            organization_id=organization_id,
            request_type=gdpr_right,
            request_details=details,
        )

        return BaseResponse(
            success=True,
            data={
                "request_id": request_id,
                "status": "pending_verification",
                "message": "GDPR request submitted successfully. Please check your email for verification.",
            },
            message="GDPR request submitted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting GDPR request: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit GDPR request")


@router.get("/gdpr/request/{request_id}/status")
async def get_gdpr_request_status(request_id: str):
    """Get status of GDPR request"""
    try:
        gdpr_service = get_gdpr_service()
        status = gdpr_service.get_gdpr_request_status(request_id)

        if not status:
            raise HTTPException(status_code=404, detail="GDPR request not found")

        return BaseResponse(
            success=True,
            data=status,
            message="GDPR request status retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving GDPR request status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve request status")


@router.post("/gdpr/request/{request_id}/verify")
async def verify_gdpr_request(request_id: str, verification_data: Dict[str, str]):
    """Verify GDPR request with token"""
    try:
        gdpr_service = get_gdpr_service()
        token = verification_data.get("token", "")

        success = await gdpr_service.verify_gdpr_request(request_id, token)

        if not success:
            raise HTTPException(status_code=400, detail="Invalid verification token")

        return BaseResponse(
            success=True,
            data={"verified": True},
            message="GDPR request verified and processing started",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying GDPR request: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify request")


@router.get("/gdpr/processing-purposes")
async def get_processing_purposes(org: str = Query(..., description="Organization ID")):
    """Get data processing purposes for transparency"""
    try:
        gdpr_service = get_gdpr_service()
        purposes = gdpr_service.get_processing_purposes()

        return BaseResponse(
            success=True,
            data={"organization_id": org, "processing_purposes": purposes},
            message="Processing purposes retrieved successfully",
        )

    except Exception as e:
        logger.error(f"Error retrieving processing purposes: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve processing purposes"
        )


# Consent Management Endpoints


@router.get("/consent/banner-config")
async def get_consent_banner_config(
    org: str = Query(..., description="Organization ID")
):
    """Get consent banner configuration"""
    try:
        consent_service = get_consent_service()
        config = consent_service.get_consent_banner_config(org)

        return BaseResponse(
            success=True,
            data=config,
            message="Consent banner configuration retrieved successfully",
        )

    except Exception as e:
        logger.error(f"Error retrieving consent banner config: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve consent configuration"
        )


@router.post("/consent/record")
async def record_consent(consent_data: Dict[str, Any], request: Request):
    """Record user consent choices"""
    try:
        consent_service = get_consent_service()

        # Extract consent data
        user_id = consent_data.get("user_id")
        organization_id = consent_data.get("organization_id")
        consent_choices = consent_data.get("consent_choices", {})
        method = consent_data.get("method", "cookie_banner")

        if not user_id or not organization_id:
            raise HTTPException(
                status_code=400, detail="user_id and organization_id are required"
            )

        # Get client information
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent")

        # Record consent
        try:
            consent_method = ConsentMethod(method)
        except ValueError:
            consent_method = ConsentMethod.COOKIE_BANNER

        records = await consent_service.bulk_record_consent(
            user_id=user_id,
            organization_id=organization_id,
            consent_choices=consent_choices,
            method=consent_method,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return BaseResponse(
            success=True,
            data={
                "recorded_consents": len(records),
                "consent_records": [record.to_dict() for record in records],
            },
            message="Consent recorded successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording consent: {e}")
        raise HTTPException(status_code=500, detail="Failed to record consent")


@router.post("/consent/withdraw")
async def withdraw_consent(
    withdrawal_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Withdraw user consent"""
    try:
        consent_service = get_consent_service()

        consent_type = withdrawal_data.get("consent_type")
        reason = withdrawal_data.get("reason", "User request")

        if not consent_type:
            raise HTTPException(status_code=400, detail="consent_type is required")

        try:
            consent_type_enum = ConsentType(consent_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid consent type")

        success = await consent_service.withdraw_consent(
            user_id=str(current_user.id),
            organization_id=str(organization.id),
            consent_type=consent_type_enum,
            reason=reason,
        )

        if not success:
            raise HTTPException(
                status_code=400, detail="Cannot withdraw this consent type"
            )

        return BaseResponse(
            success=True,
            data={"withdrawn": True, "consent_type": consent_type},
            message="Consent withdrawn successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error withdrawing consent: {e}")
        raise HTTPException(status_code=500, detail="Failed to withdraw consent")


@router.get("/consent/status")
async def get_consent_status(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Get current consent status for user"""
    try:
        consent_service = get_consent_service()

        current_consent = consent_service.get_user_consent(
            str(current_user.id), str(organization.id)
        )

        consent_status = {}
        for consent_type, record in current_consent.items():
            consent_status[consent_type.value] = record.to_dict()

        return BaseResponse(
            success=True,
            data={
                "user_id": str(current_user.id),
                "organization_id": str(organization.id),
                "consent_status": consent_status,
            },
            message="Consent status retrieved successfully",
        )

    except Exception as e:
        logger.error(f"Error retrieving consent status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve consent status")


@router.get("/consent/history")
async def get_consent_history(
    consent_type: Optional[str] = Query(None, description="Filter by consent type"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Get consent history for user"""
    try:
        consent_service = get_consent_service()

        consent_type_enum = None
        if consent_type:
            try:
                consent_type_enum = ConsentType(consent_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid consent type")

        history = consent_service.get_consent_history(
            str(current_user.id), str(organization.id), consent_type_enum
        )

        return BaseResponse(
            success=True,
            data={
                "user_id": str(current_user.id),
                "organization_id": str(organization.id),
                "consent_history": [record.to_dict() for record in history],
            },
            message="Consent history retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving consent history: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve consent history"
        )


# Compliance Reporting Endpoints


@router.post("/reports/generate")
async def generate_compliance_report(
    report_request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Generate compliance report"""
    try:
        if current_user.role not in ["admin", "compliance_officer"]:
            raise HTTPException(
                status_code=403, detail="Admin or compliance officer access required"
            )

        from app.core.compliance_reporting import (
            ReportType,
            get_compliance_reporting_service,
        )

        reporting_service = get_compliance_reporting_service()

        report_type = report_request.get("report_type", "comprehensive")
        period_start = datetime.fromisoformat(report_request.get("period_start"))
        period_end = datetime.fromisoformat(report_request.get("period_end"))

        try:
            report_type_enum = ReportType(report_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid report type")

        # Generate appropriate report
        if report_type_enum == ReportType.GDPR_COMPLIANCE:
            report = await reporting_service.generate_gdpr_compliance_report(
                str(organization.id), period_start, period_end
            )
        elif report_type_enum == ReportType.CONSENT_MANAGEMENT:
            report = await reporting_service.generate_consent_management_report(
                str(organization.id), period_start, period_end
            )
        elif report_type_enum == ReportType.DATA_RETENTION:
            report = await reporting_service.generate_data_retention_report(
                str(organization.id), period_start, period_end
            )
        else:  # COMPREHENSIVE
            report = await reporting_service.generate_comprehensive_report(
                str(organization.id), period_start, period_end
            )

        return BaseResponse(
            success=True,
            data=report.to_dict(),
            message="Compliance report generated successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate compliance report"
        )


@router.get("/reports")
async def list_compliance_reports(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """List all compliance reports for organization"""
    try:
        if current_user.role not in ["admin", "compliance_officer"]:
            raise HTTPException(
                status_code=403, detail="Admin or compliance officer access required"
            )

        from app.core.compliance_reporting import get_compliance_reporting_service

        reporting_service = get_compliance_reporting_service()
        reports = reporting_service.list_reports(str(organization.id))

        return BaseResponse(
            success=True,
            data={"reports": reports, "total_reports": len(reports)},
            message="Reports retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing compliance reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to list reports")


@router.get("/reports/{report_id}")
async def get_compliance_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Get specific compliance report"""
    try:
        if current_user.role not in ["admin", "compliance_officer"]:
            raise HTTPException(
                status_code=403, detail="Admin or compliance officer access required"
            )

        from app.core.compliance_reporting import get_compliance_reporting_service

        reporting_service = get_compliance_reporting_service()
        report = reporting_service.get_report(report_id)

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if report.organization_id != str(organization.id):
            raise HTTPException(status_code=403, detail="Access denied")

        return BaseResponse(
            success=True, data=report.to_dict(), message="Report retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving compliance report: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve report")


# Admin Endpoints (require admin role)


@router.get("/admin/consent/report")
async def get_consent_report(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Generate consent compliance report (admin only)"""
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        consent_service = get_consent_service()
        report = consent_service.generate_consent_report(str(organization.id))

        return BaseResponse(
            success=True, data=report, message="Consent report generated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating consent report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate consent report")


@router.post("/admin/policies/create")
async def create_policy(
    policy_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Create or update policy (admin only)"""
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        privacy_service = get_privacy_policy_service()

        policy_type = policy_data.get("policy_type")
        content = policy_data.get("content")
        version = policy_data.get("version", "1.0")
        summary_of_changes = policy_data.get("summary_of_changes")

        if not policy_type or not content:
            raise HTTPException(
                status_code=400, detail="policy_type and content are required"
            )

        try:
            policy_type_enum = PolicyType(policy_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid policy type")

        policy_version = privacy_service.create_policy(
            organization_id=str(organization.id),
            policy_type=policy_type_enum,
            version=version,
            custom_content=content,
            summary_of_changes=summary_of_changes,
        )

        return BaseResponse(
            success=True,
            data=policy_version.to_dict(),
            message="Policy created successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to create policy")
