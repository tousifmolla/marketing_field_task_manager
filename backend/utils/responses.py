from flask import jsonify

def success(data=None, message="Success", status=200): return jsonify(success=True, message=message, data=data if data is not None else {}), status
def error(message="Request failed", status=400, errors=None): return jsonify(success=False, message=message, data={"errors": errors} if errors else {}), status
