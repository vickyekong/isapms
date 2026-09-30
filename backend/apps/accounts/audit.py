def client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def write_audit(actor, action, entity, entity_id="", description="", metadata=None, request=None):
    from apps.accounts.models import AuditLog

    AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id or ""),
        description=description,
        metadata=metadata or {},
        ip_address=client_ip(request),
    )
