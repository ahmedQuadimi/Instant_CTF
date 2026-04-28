from django import template

from Organizations.models import OrganizationMembership

register = template.Library()


def _resolve_org_role(user, organization):
    if not user or not getattr(user, "is_authenticated", False) or organization is None:
        return None

    try:
        return OrganizationMembership.objects.get(
            user=user,
            organization=organization,
        ).role
    except OrganizationMembership.DoesNotExist:
        return None


@register.filter
def get_org_role(user, organization):
    return _resolve_org_role(user, organization)


@register.simple_tag(name="get_org_role")
def get_org_role_assignment(user, organization):
    return _resolve_org_role(user, organization)

from Events.models import EventRole

@register.filter
def get_event_role(user, event):
    if not user or not getattr(user, "is_authenticated", False) or event is None:
        return None
    try:
        return EventRole.objects.get(
            user=user, event=event
        ).role
    except EventRole.DoesNotExist:
        return None

@register.simple_tag(name="get_event_role")
def get_event_role_assignment(user, event):
    return get_event_role(user, event)

@register.filter
def time_status(event):
    return event.time_status

@register.filter
def status_badge_class(status):
    return {
        'active': 'badge-active',
        'upcoming': 'badge-upcoming', 
        'ended': 'badge-ended',
    }.get(status, '')
