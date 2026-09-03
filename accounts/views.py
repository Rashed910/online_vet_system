from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages

User = get_user_model()


def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = None
        if '@' in identifier:
            try:
                user_obj = User.objects.get(email=identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        else:
            user = authenticate(request, username=identifier, password=password)

        if user is not None:
            login(request, user)
            if user.role == 'DOCTOR':
                return redirect('vet_dashboard')
            elif user.role == 'ADMIN':
                return redirect('/admin/')
            else:
                return redirect('patient_dashboard')
        else:
            messages.error(request, 'Invalid username/email or password.')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        if not full_name or not email or not password:
            messages.error(request, 'All fields are required.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
        else:
            parts = full_name.split()
            username = email.split('@')[0]
            username_base = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{username_base}{counter}'
                counter += 1

            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=parts[0] if parts else '',
                last_name=' '.join(parts[1:]) if len(parts) > 1 else '',
                role='PATIENT',
            )
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('login')

    return render(request, 'register.html')
