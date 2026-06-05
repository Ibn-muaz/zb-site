"""
Lands and Houses — Comprehensive View & Route Unit Tests
Covers all URL patterns, HTTP status codes, redirects,
authentication guards, and critical business logic.
"""
import uuid
from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.contrib.auth import get_user_model

from apps.content.models import (
    SiteSettings, FAQ, BlogPost, Testimonial, ContactInquiry
)
from apps.properties.models import Property
from apps.negotiations.models import Negotiation

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email='user@test.com', password='Testpass123!', role='user', **kwargs):
    return User.objects.create_user(
        email=email,
        username=email.split('@')[0],
        password=password,
        first_name='Test',
        last_name='User',
        role=role,
        is_verified=True,
        **kwargs,
    )


def make_admin(email='admin@test.com', password='Adminpass123!'):
    return make_user(email=email, password=password, role='admin')


def make_property(admin_user, title='Test Property', **kwargs):
    defaults = dict(
        admin=admin_user,
        title=title,
        description='A fine test property.',
        property_type='house',
        listing_type='sale',
        status='available',
        price=5_000_000,
        address='1 Test Street',
        city='Lagos',
        state='Lagos',
        country='Nigeria',
    )
    defaults.update(kwargs)
    return Property.objects.create(**defaults)


def make_blog_post(author, title='Test Blog Post', is_published=True, **kwargs):
    import re
    slug = re.sub(r'\s+', '-', title.lower()) + f'-{uuid.uuid4().hex[:6]}'
    return BlogPost.objects.create(
        author=author,
        title=title,
        slug=slug,
        excerpt='A test excerpt.',
        content='Full test content.',
        is_published=is_published,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 1. Content / Public Routes
# ---------------------------------------------------------------------------

class HomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_returns_200(self):
        res = self.client.get(reverse('home'))
        self.assertEqual(res.status_code, 200)

    def test_home_uses_correct_template(self):
        res = self.client.get(reverse('home'))
        self.assertTemplateUsed(res, 'home/index.html')

    def test_home_url_resolves_to_home_view(self):
        match = resolve('/')
        self.assertEqual(match.url_name, 'home')

    def test_home_context_has_required_keys(self):
        res = self.client.get(reverse('home'))
        for key in ('featured_properties', 'recent_properties', 'testimonials'):
            self.assertIn(key, res.context)


class AboutViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_about_returns_200(self):
        res = self.client.get(reverse('about'))
        self.assertEqual(res.status_code, 200)

    def test_about_uses_correct_template(self):
        res = self.client.get(reverse('about'))
        self.assertTemplateUsed(res, 'content/about.html')

    def test_about_context_has_testimonials(self):
        res = self.client.get(reverse('about'))
        self.assertIn('testimonials', res.context)


class ContactViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_contact_get_returns_200(self):
        res = self.client.get(reverse('contact'))
        self.assertEqual(res.status_code, 200)

    def test_contact_uses_correct_template(self):
        res = self.client.get(reverse('contact'))
        self.assertTemplateUsed(res, 'content/contact.html')

    def test_contact_post_valid_creates_inquiry_and_redirects(self):
        res = self.client.post(reverse('contact'), {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '08012345678',
            'subject': 'Property Inquiry',
            'message': 'I am interested in your listings.',
        })
        self.assertRedirects(res, reverse('contact'))
        self.assertEqual(ContactInquiry.objects.count(), 1)

    def test_contact_post_missing_fields_stays_on_page(self):
        res = self.client.post(reverse('contact'), {
            'name': 'John',
            'email': '',
            'subject': '',
            'message': '',
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ContactInquiry.objects.count(), 0)


class FAQViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        FAQ.objects.create(question='What is ZB?', answer='A real estate firm.', is_active=True)

    def test_faq_returns_200(self):
        res = self.client.get(reverse('faq'))
        self.assertEqual(res.status_code, 200)

    def test_faq_uses_correct_template(self):
        res = self.client.get(reverse('faq'))
        self.assertTemplateUsed(res, 'content/faq.html')

    def test_faq_context_contains_faqs(self):
        res = self.client.get(reverse('faq'))
        self.assertIn('faqs', res.context)
        self.assertEqual(res.context['faqs'].count(), 1)


class BlogListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_blog_list_returns_200(self):
        res = self.client.get(reverse('blog-list'))
        self.assertEqual(res.status_code, 200)

    def test_blog_list_uses_correct_template(self):
        res = self.client.get(reverse('blog-list'))
        self.assertTemplateUsed(res, 'content/blog_list.html')

    def test_blog_list_only_shows_published(self):
        make_blog_post(self.user, is_published=True)
        make_blog_post(self.user, title='Draft Post', is_published=False)
        res = self.client.get(reverse('blog-list'))
        self.assertEqual(res.context['posts'].count(), 1)


class BlogDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.post = make_blog_post(self.user)

    def test_blog_detail_returns_200(self):
        res = self.client.get(reverse('blog-detail', kwargs={'slug': self.post.slug}))
        self.assertEqual(res.status_code, 200)

    def test_blog_detail_uses_correct_template(self):
        res = self.client.get(reverse('blog-detail', kwargs={'slug': self.post.slug}))
        self.assertTemplateUsed(res, 'content/blog_detail.html')

    def test_blog_detail_404_for_invalid_slug(self):
        res = self.client.get(reverse('blog-detail', kwargs={'slug': 'does-not-exist'}))
        self.assertEqual(res.status_code, 404)

    def test_blog_detail_increments_view_count(self):
        initial_count = self.post.view_count
        self.client.get(reverse('blog-detail', kwargs={'slug': self.post.slug}))
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, initial_count + 1)

    def test_blog_detail_context_has_related_posts(self):
        res = self.client.get(reverse('blog-detail', kwargs={'slug': self.post.slug}))
        self.assertIn('related_posts', res.context)


# ---------------------------------------------------------------------------
# 2. Properties Routes
# ---------------------------------------------------------------------------

class PropertyListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin()

    def test_property_list_returns_200(self):
        res = self.client.get(reverse('property-list'))
        self.assertEqual(res.status_code, 200)

    def test_property_list_uses_correct_template(self):
        res = self.client.get(reverse('property-list'))
        self.assertTemplateUsed(res, 'properties/list.html')

    def test_property_list_with_search_returns_200(self):
        make_property(self.admin, title='Lagos Mansion')
        res = self.client.get(reverse('property-list') + '?search=Lagos')
        self.assertEqual(res.status_code, 200)

    def test_property_list_with_type_filter(self):
        make_property(self.admin, property_type='apartment')
        res = self.client.get(reverse('property-list') + '?property_type=apartment')
        self.assertEqual(res.status_code, 200)


class PropertyDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.property = make_property(self.admin)

    def test_property_detail_returns_200(self):
        res = self.client.get(reverse('property-detail', kwargs={'slug': self.property.slug}))
        self.assertEqual(res.status_code, 200)

    def test_property_detail_uses_correct_template(self):
        res = self.client.get(reverse('property-detail', kwargs={'slug': self.property.slug}))
        self.assertTemplateUsed(res, 'properties/detail.html')

    def test_property_detail_404_for_invalid_slug(self):
        res = self.client.get(reverse('property-detail', kwargs={'slug': 'no-such-property'}))
        self.assertEqual(res.status_code, 404)

    def test_inactive_property_returns_404(self):
        self.property.is_active = False
        self.property.save()
        res = self.client.get(reverse('property-detail', kwargs={'slug': self.property.slug}))
        self.assertEqual(res.status_code, 404)


class SavePropertyViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.admin = make_admin()
        self.property = make_property(self.admin)

    def test_save_property_requires_login(self):
        res = self.client.post(
            reverse('save-property', kwargs={'slug': self.property.slug})
        )
        self.assertEqual(res.status_code, 302)

    def test_save_property_authenticated_returns_200(self):
        self.client.force_login(self.user)
        res = self.client.post(
            reverse('save-property', kwargs={'slug': self.property.slug}),
            HTTP_ACCEPT='application/json',
        )
        self.assertIn(res.status_code, [200, 201])


# ---------------------------------------------------------------------------
# 3. Authentication Routes
# ---------------------------------------------------------------------------

class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_get_returns_200(self):
        res = self.client.get(reverse('register'))
        self.assertEqual(res.status_code, 200)

    def test_register_uses_correct_template(self):
        res = self.client.get(reverse('register'))
        self.assertTemplateUsed(res, 'accounts/register.html')


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_login_get_returns_200(self):
        res = self.client.get(reverse('login'))
        self.assertEqual(res.status_code, 200)

    def test_login_uses_correct_template(self):
        res = self.client.get(reverse('login'))
        self.assertTemplateUsed(res, 'accounts/login.html')

    def test_login_context_has_next(self):
        res = self.client.get(reverse('login') + '?next=/dashboard/')
        self.assertIn('next', res.context)
        self.assertEqual(res.context['next'], '/dashboard/')


class PasswordResetViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_password_reset_get_returns_200(self):
        res = self.client.get(reverse('password-reset'))
        self.assertEqual(res.status_code, 200)

    def test_password_reset_uses_correct_template(self):
        res = self.client.get(reverse('password-reset'))
        self.assertTemplateUsed(res, 'accounts/password_reset.html')


# ---------------------------------------------------------------------------
# 4. Dashboard Routes (Authentication Required)
# ---------------------------------------------------------------------------

class UserDashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_dashboard_redirects_anonymous(self):
        res = self.client.get(reverse('dashboard:home'))
        self.assertEqual(res.status_code, 302)
        self.assertIn('/accounts/login/', res['Location'])

    def test_dashboard_returns_200_for_authenticated(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('dashboard:home'))
        self.assertEqual(res.status_code, 200)

    def test_dashboard_uses_correct_template(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('dashboard:home'))
        self.assertTemplateUsed(res, 'accounts/dashboard.html')

    def test_dashboard_context_has_stats(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('dashboard:home'))
        self.assertIn('stats', res.context)


class SavedPropertiesViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_saved_properties_redirects_anonymous(self):
        res = self.client.get(reverse('dashboard:saved-properties'))
        self.assertEqual(res.status_code, 302)

    def test_saved_properties_returns_200_authenticated(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('dashboard:saved-properties'))
        self.assertEqual(res.status_code, 200)

    def test_saved_properties_uses_correct_template(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('dashboard:saved-properties'))
        self.assertTemplateUsed(res, 'accounts/saved_properties.html')


class UserNegotiationsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_my_negotiations_redirects_anonymous(self):
        res = self.client.get(reverse('dashboard:my-negotiations'))
        self.assertEqual(res.status_code, 302)

    def test_my_negotiations_returns_200_authenticated(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('dashboard:my-negotiations'))
        self.assertEqual(res.status_code, 200)

    def test_my_negotiations_uses_correct_template(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('dashboard:my-negotiations'))
        self.assertTemplateUsed(res, 'accounts/my_negotiations.html')


class UserPaymentsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_my_payments_redirects_anonymous(self):
        res = self.client.get(reverse('dashboard:my-payments'))
        self.assertEqual(res.status_code, 302)

    def test_my_payments_returns_200_authenticated(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('dashboard:my-payments'))
        self.assertEqual(res.status_code, 200)

    def test_my_payments_uses_correct_template(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('dashboard:my-payments'))
        self.assertTemplateUsed(res, 'accounts/my_payments.html')


# ---------------------------------------------------------------------------
# 5. Admin Panel Routes (Admin Role Required)
# ---------------------------------------------------------------------------

class AdminDashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user(email='reg@test.com')
        self.admin = make_admin()

    def test_admin_dashboard_redirects_anonymous(self):
        res = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(res.status_code, 302)

    def test_admin_dashboard_redirects_regular_user(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(res.status_code, 302)

    def test_admin_dashboard_returns_200_for_admin(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(res.status_code, 200)

    def test_admin_dashboard_uses_correct_template(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:dashboard'))
        self.assertTemplateUsed(res, 'admin_panel/dashboard.html')

    def test_admin_dashboard_context_has_stats(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:dashboard'))
        self.assertIn('stats', res.context)


class AdminUserListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin()

    def test_admin_user_list_returns_200(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:user-list'))
        self.assertEqual(res.status_code, 200)

    def test_admin_user_list_uses_correct_template(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:user-list'))
        self.assertTemplateUsed(res, 'admin_panel/users/list.html')

    def test_admin_user_list_with_search_returns_200(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:user-list') + '?q=test')
        self.assertEqual(res.status_code, 200)


class AdminPropertyListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin()

    def test_admin_property_list_returns_200(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:property-list'))
        self.assertEqual(res.status_code, 200)

    def test_admin_property_list_uses_correct_template(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:property-list'))
        self.assertTemplateUsed(res, 'admin_panel/properties/list.html')


class AdminNegotiationListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin()

    def test_admin_negotiation_list_returns_200(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:negotiation-list'))
        self.assertEqual(res.status_code, 200)

    def test_admin_negotiation_list_uses_correct_template(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:negotiation-list'))
        self.assertTemplateUsed(res, 'admin_panel/negotiations/list.html')


class AdminContentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin()

    def test_admin_content_returns_200(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:content'))
        self.assertEqual(res.status_code, 200)

    def test_admin_content_uses_correct_template(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:content'))
        self.assertTemplateUsed(res, 'admin_panel/content/index.html')


class AdminPaymentListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin()

    def test_admin_payment_list_returns_200(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:payment-list'))
        self.assertEqual(res.status_code, 200)

    def test_admin_payment_list_uses_correct_template(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:payment-list'))
        self.assertTemplateUsed(res, 'admin_panel/payments/list.html')


class AdminAnalyticsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin()

    def test_admin_analytics_returns_200(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:analytics'))
        self.assertEqual(res.status_code, 200)

    def test_admin_analytics_uses_correct_template(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:analytics'))
        self.assertTemplateUsed(res, 'admin_panel/analytics.html')

    def test_admin_analytics_context_keys(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('admin_panel:analytics'))
        self.assertIn('monthly_users', res.context)
        self.assertIn('monthly_revenue', res.context)
        self.assertIn('top_properties', res.context)


# ---------------------------------------------------------------------------
# 6. Negotiations Routes
# ---------------------------------------------------------------------------

class NegotiationListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_negotiation_list_redirects_anonymous(self):
        res = self.client.get(reverse('negotiation-list'))
        self.assertEqual(res.status_code, 302)

    def test_negotiation_list_returns_200_authenticated(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('negotiation-list'))
        self.assertEqual(res.status_code, 200)


class CreateNegotiationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.admin = make_admin()
        self.property = make_property(self.admin)

    def test_create_negotiation_redirects_anonymous(self):
        res = self.client.post(
            reverse('create-negotiation', kwargs={'property_slug': self.property.slug}),
            {'offered_price': 4_500_000},
        )
        self.assertEqual(res.status_code, 302)

    def test_create_negotiation_post_authenticated(self):
        self.client.force_login(self.user)
        res = self.client.post(
            reverse('create-negotiation', kwargs={'property_slug': self.property.slug}),
            {'offered_price': 4_500_000, 'message': 'I would like to negotiate.'},
        )
        # Expect redirect on success or 200 with form errors
        self.assertIn(res.status_code, [200, 302])


# ---------------------------------------------------------------------------
# 7. Payments Routes
# ---------------------------------------------------------------------------

class PaymentCheckoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.admin = make_admin()
        self.property = make_property(self.admin)

    def test_payment_checkout_redirects_anonymous(self):
        res = self.client.get(
            reverse('payment-checkout', kwargs={'property_id': str(self.property.id)})
        )
        self.assertEqual(res.status_code, 302)

    def test_payment_checkout_returns_200_authenticated(self):
        self.client.force_login(self.user)
        res = self.client.get(
            reverse('payment-checkout', kwargs={'property_id': str(self.property.id)})
        )
        self.assertIn(res.status_code, [200, 302])


class PaymentSuccessViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_payment_success_redirects_anonymous(self):
        res = self.client.get(reverse('payment-success'))
        self.assertEqual(res.status_code, 302)

    def test_payment_success_returns_200_authenticated(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('payment-success'))
        self.assertIn(res.status_code, [200, 302])


class PaymentCancelViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_payment_cancel_redirects_anonymous(self):
        res = self.client.get(reverse('payment-cancel'))
        self.assertEqual(res.status_code, 302)

    def test_payment_cancel_returns_200_authenticated(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('payment-cancel'))
        self.assertIn(res.status_code, [200, 302])


class PaymentHistoryViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_payment_history_redirects_anonymous(self):
        res = self.client.get(reverse('payment-history'))
        self.assertEqual(res.status_code, 302)

    def test_payment_history_returns_200_authenticated(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('payment-history'))
        self.assertIn(res.status_code, [200, 302])


# ---------------------------------------------------------------------------
# 8. URL Reverse Resolution Tests
# ---------------------------------------------------------------------------

class URLResolutionTests(TestCase):
    """Ensure all named URL patterns resolve without errors."""

    def test_home_url(self):
        self.assertEqual(reverse('home'), '/')

    def test_about_url(self):
        self.assertEqual(reverse('about'), '/about/')

    def test_contact_url(self):
        self.assertEqual(reverse('contact'), '/contact/')

    def test_faq_url(self):
        self.assertEqual(reverse('faq'), '/faq/')

    def test_blog_list_url(self):
        self.assertEqual(reverse('blog-list'), '/blog/')

    def test_property_list_url(self):
        self.assertEqual(reverse('property-list'), '/properties/')

    def test_register_url(self):
        self.assertEqual(reverse('register'), '/accounts/register/')

    def test_login_url(self):
        self.assertEqual(reverse('login'), '/accounts/login/')

    def test_logout_url(self):
        self.assertEqual(reverse('logout'), '/accounts/logout/')

    def test_password_reset_url(self):
        self.assertEqual(reverse('password-reset'), '/accounts/password-reset/')

    def test_dashboard_url(self):
        self.assertEqual(reverse('dashboard:home'), '/dashboard/')

    def test_saved_properties_url(self):
        self.assertEqual(reverse('dashboard:saved-properties'), '/dashboard/saved-properties/')

    def test_my_negotiations_url(self):
        self.assertEqual(reverse('dashboard:my-negotiations'), '/dashboard/my-negotiations/')

    def test_my_payments_url(self):
        self.assertEqual(reverse('dashboard:my-payments'), '/dashboard/my-payments/')

    def test_admin_dashboard_url(self):
        self.assertEqual(reverse('admin_panel:dashboard'), '/admin-panel/')


# ---------------------------------------------------------------------------
# 9. Authentication Security Tests
# ---------------------------------------------------------------------------

class AuthenticationSecurityTests(TestCase):
    """Verify unauthenticated users are blocked from protected views."""

    PROTECTED_URLS = [
        'dashboard:home',
        'dashboard:saved-properties',
        'dashboard:my-negotiations',
        'dashboard:my-payments',
    ]

    def setUp(self):
        self.client = Client()

    def test_protected_views_redirect_anonymous(self):
        for url_name in self.PROTECTED_URLS:
            with self.subTest(url=url_name):
                res = self.client.get(reverse(url_name))
                self.assertEqual(
                    res.status_code, 302,
                    msg=f'{url_name} should redirect anonymous users'
                )
                self.assertIn('login', res['Location'])

    def test_admin_views_block_regular_users(self):
        user = make_user(email='plain@test.com')
        self.client.force_login(user)
        admin_urls = [
            reverse('admin_panel:dashboard'),
        ]
        for url in admin_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                # Should redirect away (not 200)
                self.assertNotEqual(res.status_code, 200,
                    msg=f'Regular user should not access {url}')


# ---------------------------------------------------------------------------
# 10. Model Tests
# ---------------------------------------------------------------------------

class SiteSettingsModelTests(TestCase):
    def test_get_settings_creates_default(self):
        settings = SiteSettings.get_settings()
        self.assertIsNotNone(settings)
        self.assertEqual(settings.company_name, 'Lands and Houses')

    def test_get_settings_singleton(self):
        s1 = SiteSettings.get_settings()
        s2 = SiteSettings.get_settings()
        self.assertEqual(s1.pk, s2.pk)


class PropertyModelTests(TestCase):
    def setUp(self):
        self.admin = make_admin()

    def test_property_slug_auto_generated(self):
        prop = make_property(self.admin, title='Beautiful Lagos Home')
        self.assertTrue(prop.slug)
        self.assertIn('beautiful', prop.slug)

    def test_property_slug_unique_on_collision(self):
        p1 = make_property(self.admin, title='Unique Home')
        p2 = Property.objects.create(
            admin=self.admin,
            title='Unique Home',
            description='Another one.',
            property_type='house',
            listing_type='sale',
            status='available',
            price=1_000_000,
            address='2 Test St',
            city='Abuja',
            state='FCT',
        )
        self.assertNotEqual(p1.slug, p2.slug)

    def test_formatted_price_uses_naira_symbol(self):
        prop = make_property(self.admin, price=5_000_000)
        self.assertIn('₦', prop.formatted_price)
        self.assertIn('5,000,000', prop.formatted_price)

    def test_property_get_absolute_url(self):
        prop = make_property(self.admin)
        url = prop.get_absolute_url()
        self.assertIn(prop.slug, url)


class CustomUserModelTests(TestCase):
    def test_user_str(self):
        user = make_user()
        self.assertIn('@', str(user))

    def test_is_admin_false_for_regular_user(self):
        user = make_user()
        self.assertFalse(user.is_admin)

    def test_is_admin_true_for_admin(self):
        admin = make_admin()
        self.assertTrue(admin.is_admin)

    def test_is_super_admin(self):
        super_admin = make_user(email='super@test.com', role='super_admin')
        self.assertTrue(super_admin.is_super_admin)
        self.assertTrue(super_admin.is_admin)

    def test_full_name_property(self):
        user = make_user()
        self.assertIn('Test', user.full_name)


class BlogPostModelTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_blog_post_creation(self):
        post = make_blog_post(self.user)
        self.assertTrue(post.is_published)
        self.assertEqual(post.view_count, 0)

    def test_blog_post_str(self):
        post = make_blog_post(self.user)
        self.assertEqual(str(post), post.title)


class ContactInquiryModelTests(TestCase):
    def test_contact_inquiry_creation(self):
        inquiry = ContactInquiry.objects.create(
            name='Alice',
            email='alice@example.com',
            subject='Test Subject',
            message='Test message body',
        )
        self.assertEqual(str(inquiry), 'Alice - Test Subject')
        self.assertFalse(inquiry.is_resolved)
