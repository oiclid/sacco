from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import User
from django.urls import reverse_lazy

class SuperAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superadmin()

class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = "users/user_list.html"
    context_object_name = "users"

    def get_queryset(self):
        # Admins cannot see superadmins
        qs = super().get_queryset()
        if self.request.user.is_admin() and not self.request.user.is_superadmin():
            return qs.exclude(role="superadmin")
        return qs

class UserCreateView(LoginRequiredMixin, SuperAdminRequiredMixin, CreateView):
    model = User
    fields = ["username", "email", "role", "password"]
    template_name = "users/user_form.html"
    success_url = reverse_lazy("user-list")

class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    fields = ["username", "email", "role"]
    template_name = "users/user_form.html"
    success_url = reverse_lazy("user-list")

    def test_func(self):
        # Admin cannot edit superadmins
        if self.get_object().role == "superadmin" and not self.request.user.is_superadmin():
            return False
        return self.request.user.is_admin() or self.request.user.is_superadmin()
