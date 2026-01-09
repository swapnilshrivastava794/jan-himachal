def success_response(data, message=None):
    """Standard success response format"""
    return {"status": True, "data": data, "message": message}


def error_response(message):
    """Standard error response format"""
    return {"status": False, "message": message}