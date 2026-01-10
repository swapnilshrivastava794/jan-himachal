def success_response(data, message=None):
    """Standard success response format"""
    return {"status": True, "data": data, "message": message}


def error_response(message):
    """Standard error response format"""
    return {"status": False, "message": message}

def get_parent_children_payload(parent_profile):
    return [
        {
            "id": child.id,
            "name": child.name
        }
        for child in parent_profile.children.filter(is_active=True)
    ]