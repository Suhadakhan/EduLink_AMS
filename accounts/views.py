from django.shortcuts import render, redirect

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        # handle login form
        pass
    return render(request, 'login.html') 