from app.security.application_auditor import ApplicationTelemetryAuditor

application_auditor = ApplicationTelemetryAuditor()


def get_application_auditor() -> ApplicationTelemetryAuditor:
    return application_auditor
