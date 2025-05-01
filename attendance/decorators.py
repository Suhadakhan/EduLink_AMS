from django.shortcuts import redirect
from functools import wraps
from django.contrib import messages
import traceback

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            try:
                print(f"\n=== Role Check Debug Info ===")
                print(f"User: {request.user.username}")
                print(f"User type: {request.user.profile.user_type}")
                print(f"Allowed roles: {allowed_roles}")
                
                if request.user.profile.user_type in allowed_roles:
                    print("Access granted")
                    return view_func(request, *args, **kwargs)
                else:
                    print("Access denied")
                    messages.error(request, "You are not authorized to access this page")
                    return redirect('home-page')
                    
            except Exception as e:
                print(f"Error in role_required decorator: {str(e)}")
                print(f"Error traceback: {traceback.format_exc()}")
                messages.error(request, "Error checking authorization")
                return redirect('home-page')
                
        return _wrapped_view
    return decorator 