from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def root_redirect_view(request):
    """Direct root URL access."""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    return redirect('login')

def custom_login_view(request):
    """Preserves exact /login/ URL with clean modern styling and robust auth."""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                if not request.session.session_key:
                    request.session.save()
                try:
                    from apps.users.models import UserActiveSession
                    UserActiveSession.objects.update_or_create(
                        user=user,
                        defaults={'session_key': request.session.session_key}
                    )
                except Exception:
                    pass
                messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard:index')
            else:
                messages.error(request, "Your account has been deactivated. Please contact HR or Administrator.")
        else:
            messages.error(request, "Invalid username or password. Please verify your credentials.")

    return render(request, 'users/login.html')

def custom_logout_view(request):
    """Secure logout view clearing session and redirecting back to login."""
    if request.user.is_authenticated:
        try:
            from apps.users.models import UserActiveSession
            UserActiveSession.objects.filter(user=request.user, session_key=request.session.session_key).update(session_key=None)
        except Exception:
            pass
        logout(request)
        request.session.flush()
        messages.info(request, "You have been logged out successfully.")
    return redirect('login')

@login_required
def user_profile_view(request):
    """Current logged-in user profile and password change."""
    profile = getattr(request.user, 'employee', None)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == 'POST':
        if 'change_password' in request.POST:
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                new_pwd = password_form.cleaned_data.get('new_password1')
                if not profile:
                    try:
                        from apps.employees.models import Employee
                        profile = Employee.objects.get(user=user)
                    except Exception:
                        profile = None
                if profile and new_pwd:
                    profile.raw_password = new_pwd
                    profile.save(update_fields=['raw_password'])
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was successfully updated!')
                return redirect('users:profile')
            else:
                for err_list in password_form.errors.values():
                    for err in err_list:
                        messages.error(request, err)

        if 'update_document' in request.POST or 'document' in request.FILES or 'profile_picture' in request.FILES:
            is_hr_or_admin = request.user.is_superuser or (profile and profile.role in ('ADMIN', 'HR'))
            if not is_hr_or_admin:
                messages.error(request, 'Permission denied: Employees cannot upload documents or profile pictures. Only HR and Admin are authorized to upload employee documents and profile pictures.')
                return redirect('users:profile')
            doc_file = request.FILES.get('document')
            pic_file = request.FILES.get('profile_picture')
            if not profile:
                try:
                    from apps.employees.models import Employee
                    profile = Employee.objects.get(user=request.user)
                except Exception:
                    profile = None
            if profile:
                updated = False
                if doc_file:
                    profile.document = doc_file
                    updated = True
                if pic_file:
                    profile.profile_picture = pic_file
                    updated = True
                if updated:
                    profile.save()
                    messages.success(request, 'Your document and/or profile picture has been successfully updated and saved!')
                    return redirect('users:profile')
                else:
                    messages.error(request, 'Please select a valid document or image file to upload.')
                    return redirect('users:profile')

    return render(request, 'users/profile.html', {
        'profile': profile,
        'password_form': password_form,
    })

from django.http import JsonResponse

@login_required
def verify_admin_access(request):
    """Verifies administrator credentials before allowing access to Django Admin."""
    is_admin = request.user.is_superuser or request.user.is_staff or (
        getattr(request.user, 'employee', None) and request.user.employee.role == 'ADMIN'
    )
    if not is_admin:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax'):
            return JsonResponse({'success': False, 'error': 'Access denied: Administrator privileges required.'}, status=403)
        messages.error(request, 'Access denied: Administrator privileges required.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        admin_password = request.POST.get('admin_password', '').strip()
        if request.user.check_password(admin_password):
            request.session['admin_panel_verified'] = True
            next_url = request.POST.get('next') or request.GET.get('next') or '/django-admin/'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax'):
                return JsonResponse({'success': True, 'redirect_url': next_url})
            return redirect(next_url)
        else:
            err_msg = 'Invalid administrator password. Access denied.'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax'):
                return JsonResponse({'success': False, 'error': err_msg}, status=400)
            messages.error(request, err_msg)

    next_url = request.GET.get('next', '/django-admin/')
    if request.session.get('admin_panel_verified'):
        return redirect(next_url)

    return render(request, 'users/admin_verify_password.html', {
        'next_url': next_url
    })
