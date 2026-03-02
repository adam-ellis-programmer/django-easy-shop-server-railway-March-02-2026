from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import Customer


class CustomerInline(admin.StackedInline):
    model = Customer
    can_delete = False
    verbose_name_plural = 'Customer Information----'
    fields = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


class UserAdmin(BaseUserAdmin):
    inlines = (CustomerInline,)
    list_display = ('username', 'email', 'first_name',
                    'last_name', 'is_staff', 'get_customer_created')

    def get_customer_created(self, obj):
        # Checks if this User has an associated Customer
        if hasattr(obj, 'customer'):
            return obj.customer.created_at
        return '-'
    get_customer_created.short_description = 'Customer Since'
    # Enables sorting by specifying the database field
    get_customer_created.admin_order_field = 'customer__created_at'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_fullname', 'user_email',
                    'user_profile_link', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email',
                     'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at', 'user_profile_link')

    # Make the customer name clickable to edit the customer record
    list_display_links = ('user_fullname',)

    # fieldsets: Organizes the edit form into sections with headings
    fieldsets = (
        ('User Account Association', {
            'fields': ('user',),
            'description': 'This controls which user account this customer profile is linked to. Changing this will move the customer profile to a different user.',
        }),
        ('User Profile Actions', {
            'fields': ('user_profile_link',),
            'description': 'Click below to edit the user\'s details like name, email, and password.',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),  # css classes
        }),
    )

    # custom fields
    # used to create a custom "computed" or "derived" field that doesn't exist directly in your model but is calculated or retrieved from related data when displayed in the admin.

    def user_fullname(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}" if obj.user.first_name else obj.user.username
    user_fullname.short_description = 'Customer Name'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def user_profile_link(self, obj):
        url = f"/admin/auth/user/{obj.user.id}/change/"
        return format_html('<a href="{}">Edit User Profile</a>', url)
    user_profile_link.short_description = 'User Profile'


# Unregister the default UserAdmin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
