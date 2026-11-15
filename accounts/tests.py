from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import CustomUser


def _make_test_image_bytes() -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", (24, 24), color=(197, 223, 160))
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class RegistrationTests(TestCase):
    def setUp(self):
        self.valid_payload = {
            "username": "brinekeeper",
            "first_name": "Vaughn",
            "last_name": "Patalinjug",
            "email": "vaughn@fermentlog.test",
            "contact_number": "+63 917 555 0142",
            "preferred_ferment": "Kimchi",
            "role": CustomUser.Role.FERMENTER,
            "password1": "BrineBatch!2026",
            "password2": "BrineBatch!2026",
        }

    def test_valid_signup_hashes_password_and_redirects_with_message(self):
        response = self.client.post(reverse("signup"), self.valid_payload)
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)

        user = CustomUser.objects.get(username="brinekeeper")
        self.assertNotEqual(user.password, "BrineBatch!2026")
        self.assertTrue(user.check_password("BrineBatch!2026"))
        self.assertEqual(user.email, "vaughn@fermentlog.test")
        self.assertEqual(user.role, CustomUser.Role.FERMENTER)

        login_page = self.client.get(reverse("login"))
        self.assertContains(login_page, "Your FermentLog account is ready.")

    def test_signup_requires_mandatory_fields(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "",
                "first_name": "",
                "last_name": "",
                "email": "",
                "role": CustomUser.Role.FERMENTER,
                "password1": "",
                "password2": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        for field_name in ("username", "first_name", "last_name", "email", "password1", "password2"):
            self.assertIn(field_name, form.errors)

    def test_signup_rejects_invalid_email_format(self):
        payload = {**self.valid_payload, "email": "not-an-email"}
        response = self.client.post(reverse("signup"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)

    def test_signup_rejects_duplicate_username_and_case_insensitive_email(self):
        CustomUser.objects.create_user(
            username="brinekeeper",
            email="vaughn@fermentlog.test",
            password="BrineBatch!2026",
            first_name="Vaughn",
            last_name="Patalinjug",
        )

        dup_username = self.client.post(
            reverse("signup"),
            {**self.valid_payload, "email": "other@fermentlog.test"},
        )
        self.assertEqual(dup_username.status_code, 200)
        self.assertIn("username", dup_username.context["form"].errors)

        dup_email = self.client.post(
            reverse("signup"),
            {**self.valid_payload, "username": "anotheruser", "email": "VAUGHN@FermentLog.test"},
        )
        self.assertEqual(dup_email.status_code, 200)
        self.assertIn("email", dup_email.context["form"].errors)

    def test_signup_rejects_mismatched_passwords(self):
        payload = {**self.valid_payload, "password2": "DifferentPass!2026"}
        response = self.client.post(reverse("signup"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)

    def test_signup_rejects_invalid_contact_number(self):
        payload = {**self.valid_payload, "contact_number": "abc-12"}
        response = self.client.post(reverse("signup"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("contact_number", response.context["form"].errors)


class AuthenticationTests(TestCase):
    def setUp(self):
        self.password = "BrineBatch!2026"
        self.fermenter = CustomUser.objects.create_user(
            username="fermenter1",
            email="fermenter1@fermentlog.test",
            password=self.password,
            first_name="Mina",
            last_name="Reyes",
            role=CustomUser.Role.FERMENTER,
        )

    def test_login_invalid_credentials_shows_error_message(self):
        response = self.client.post(
            reverse("login"),
            {"username": "fermenter1", "password": "WrongPassword123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_and_logout_lifecycle(self):
        login_response = self.client.post(
            reverse("login"),
            {"username": "fermenter1", "password": self.password},
        )
        self.assertRedirects(
            login_response,
            reverse("fermenter_dashboard"),
            fetch_redirect_response=False,
        )
        self.assertIn("_auth_user_id", self.client.session)

        logout_response = self.client.post(reverse("logout"))
        self.assertRedirects(logout_response, reverse("login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

        protected = self.client.get(reverse("profile"))
        self.assertRedirects(protected, f"{reverse('login')}?next={reverse('profile')}")

    def test_authenticated_user_redirected_away_from_auth_pages(self):
        self.client.force_login(self.fermenter)
        self.assertRedirects(
            self.client.get(reverse("login")),
            reverse("fermenter_dashboard"),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            self.client.get(reverse("signup")),
            reverse("fermenter_dashboard"),
            fetch_redirect_response=False,
        )


class ProfileTests(TestCase):
    def setUp(self):
        self.password = "BrineBatch!2026"
        self.user = CustomUser.objects.create_user(
            username="jarowner",
            email="owner@fermentlog.test",
            password=self.password,
            first_name="Jar",
            last_name="Owner",
            role=CustomUser.Role.FERMENTER,
        )
        self.other_user = CustomUser.objects.create_user(
            username="otherjar",
            email="other@fermentlog.test",
            password=self.password,
            first_name="Other",
            last_name="User",
            role=CustomUser.Role.FERMENTER,
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile')}")

        detail_url = reverse("profile_detail", kwargs={"pk": self.other_user.pk})
        detail_response = self.client.get(detail_url)
        self.assertRedirects(detail_response, f"{reverse('login')}?next={detail_url}")

    def test_profile_updates_only_signed_in_user_including_photo(self):
        self.client.force_login(self.user)
        photo = SimpleUploadedFile(
            "avatar.png",
            _make_test_image_bytes(),
            content_type="image/png",
        )
        with TemporaryDirectory() as tmp_media:
            with override_settings(MEDIA_ROOT=tmp_media):
                response = self.client.post(
                    reverse("profile"),
                    {
                        "first_name": "Elena",
                        "last_name": "Cruz",
                        "email": "elena@fermentlog.test",
                        "contact_number": "+63 918 222 0199",
                        "preferred_ferment": "Sauerkraut",
                        "bio": "Two-liter crock batches every Sunday.",
                        "profile_photo": photo,
                    },
                )
                self.assertRedirects(response, reverse("profile"))

                self.user.refresh_from_db()
                self.other_user.refresh_from_db()
                self.assertEqual(self.user.first_name, "Elena")
                self.assertEqual(self.user.email, "elena@fermentlog.test")
                self.assertEqual(self.user.contact_number, "+63 918 222 0199")
                self.assertEqual(self.user.preferred_ferment, "Sauerkraut")
                self.assertTrue(bool(self.user.profile_photo))
                self.assertEqual(self.other_user.first_name, "Other")

                profile_page = self.client.get(reverse("profile"))
                self.assertEqual(profile_page.status_code, 200)
                self.assertContains(profile_page, "elena@fermentlog.test")

    def test_profile_rejects_duplicate_email_from_another_user(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Jar",
                "last_name": "Owner",
                "email": "OTHER@fermentlog.test",
                "contact_number": "",
                "preferred_ferment": "",
                "bio": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)

    def test_profile_blocks_viewing_another_users_profile_id(self):
        self.client.force_login(self.user)
        own_response = self.client.get(reverse("profile_detail", kwargs={"pk": self.user.pk}))
        self.assertRedirects(own_response, reverse("profile"))

        other_response = self.client.get(reverse("profile_detail", kwargs={"pk": self.other_user.pk}))
        self.assertEqual(other_response.status_code, 403)
