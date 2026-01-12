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
    
    
def build_nanhe_patrakar_program_info(parent_profile):
    return {
        "parent_id": parent_profile.id,
        "program_id": parent_profile.program.id if parent_profile.program else None,
        "program_name": parent_profile.program.name if parent_profile.program else None,
        "status": parent_profile.status,
        "mobile": parent_profile.mobile,
        "city": parent_profile.city,
        "district": parent_profile.district.name if parent_profile.district else None,

        # Children summary
        "children": get_parent_children_payload(parent_profile),

        # Optional / future-safe fields
        "kyc_status": getattr(parent_profile, 'kyc_status', None),
        "terms_accepted": parent_profile.terms_accepted,
        "terms_accepted_at": parent_profile.terms_accepted_at,
    }
