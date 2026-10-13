"""Compose metadata for memory matching; no installation or restart actions."""
import re


def memory_components_from_inventory(result):
    """Do not choose the first frontend when inventory is ambiguous."""
    if not isinstance(result, dict) or result.get('status') != 'ok':
        return {}
    versions = set()
    for container in result.get('containers') or []:
        if not isinstance(container, dict):
            return {}
        image = str(container.get('image') or '')
        if 'frontend' not in (str(container.get('name') or '') + ' ' + image.rsplit('/',1)[-1]).casefold():
            continue
        tail = image.split('@',1)[0].rsplit('/',1)[-1]
        tag = tail.rsplit(':',1)[-1] if ':' in tail else ''
        if not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?',tag):
            return {}
        versions.add(tag)
    return {'frontend':next(iter(versions))} if len(versions)==1 else {}


def detect_memory_identity(stand, detector, component_reader):
    identity = dict(detector(stand))
    identity.update(frontend_status='unknown',frontend_version=None,frontend_version_source='container_image_tag')
    try:
        versions = component_reader(stand)
        frontend = versions.get('frontend') if isinstance(versions,dict) else None
        if isinstance(frontend,str) and re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?',frontend):
            identity.update(frontend_status='ok',frontend_version=frontend)
    except Exception:
        pass  # Do not expose SSH errors, secrets, or silently reuse an old tag.
    return identity
