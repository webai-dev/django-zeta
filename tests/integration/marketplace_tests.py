import os
import random
import time

from languages_plus.models import Language
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from django.conf import settings
from django.test import override_settings

from ery_backend.base.testcases import EryChannelsTestCase, create_test_stintdefinition, get_chromedriver
from ery_backend.frontends.models import Frontend
from ery_backend.stint_specifications.factories import StintSpecificationFactory, StintSpecificationAllowedLanguageFrontend
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.stints.models import StintDefinition, Stint
from ery_backend.templates.models import Template
from ery_backend.themes.models import Theme
from ery_backend.users.factories import UserFactory
from ery_backend.widgets.models import Widget

selenium_middleware = settings.MIDDLEWARE
debug_middleware = ['graphiql_debug_toolbar.middleware.DebugToolbarMiddleware']
for middleware in debug_middleware:
    if middleware in selenium_middleware:
        selenium_middleware.remove(middleware)

selenium_apps = settings.INSTALLED_APPS
debug_apps = ['debug_toolbar', 'graphiql_debug_toolbar']
for app in debug_apps:
    if app in selenium_apps:
        selenium_apps.remove(app)


@override_settings(DEBUG=True, INSTALLED_APPS=selenium_apps, INSTALLED_MIDDLEWARE=selenium_middleware)
class TestMarketplaceStint(EryChannelsTestCase):
    """
    Confirm a marketplace stint can be properly navigated by multiple users.
    """

    fixtures = ['roles_privileges', 'languages', 'frontends', 'templates', 'widgets', 'frontendlanguages']

    @staticmethod
    def create_stintdefinition():
        xml_base_address = f'{os.getcwd()}/scripts/lenns_demo_files/lenns_exports'
        lenns_requirements = [
            {
                'cls': Widget,
                'elements': [
                    'Dropdown',
                    'EryInput',
                    'RadioButtons',
                    'WebFloatWidget',
                    'WebIntWidget',
                    'WebTextFieldWidget',
                    'WebButton',
                    'AlphanumericField',
                    'Limit20IntWidget',
                    'Limit120IntWidget',
                    'Limit10IntWidget',
                    'LimitIntWidget',
                    'EryDialog',
                    'EryGrid',
                    'DialogCloser',
                    'Slider',
                    'ErySlider',
                ],
            },
            {'cls': Template, 'elements': ['WebHeaderContentFooter', 'DNMHcfChildForward', 'DNMHcfChildProgression']},
            {'cls': Theme, 'elements': ['Demo']},
            {'cls': StintDefinition, 'elements': ['DescriptiveNormMessaging_v6']},
        ]

        for objs_info in lenns_requirements:
            for element in objs_info['elements']:
                xml_file = open(f'{xml_base_address}/{element}.bxml', 'rb')
                objs_info['cls'].import_instance_from_xml(xml_file)

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)

    def setUp(self):
        # CALF logs in to experiment started by DJTestTwister
        self.dj_man = UserFactory(username='DJTestTwister')
        self.starter_gql_id = self.dj_man.gql_id
        self.web = Frontend.objects.get(name='Web')
        english = Language.objects.get(pk='en')
        self.language_frontend = StintSpecificationAllowedLanguageFrontend.objects.get_or_create(
            frontend=self.web, language=english
        )[0]
        self.web.slug = 'Web-foKmSGxB'
        self.web.save()
        self.create_stintdefinition()
        self.sd = StintDefinition.objects.get(name='DescriptiveNormMessaging')
        self.sd_web_id = f'{self.sd.slug.lower()}'
        ss = StintSpecificationFactory(
            stint_definition=self.sd, where_to_run=StintSpecification.WHERE_TO_RUN_CHOICES.market, late_arrival=True
        )
        ss.allowed_language_frontend_combinations.add(self.language_frontend)
        self.stint = self.sd.realize(ss)
        self.driver_1 = self.get_loggedin_driver('comedic_artsy_fun_accountant', headless=True)

    def test_stint_accessible(self):
        self.stint.start(self.dj_man)
        self.driver_1.get(f'{self.live_server_url}/marketplace/{self.starter_gql_id}')
        WebDriverWait(self.driver_1, 30).until(EC.presence_of_element_located((By.ID, self.sd_web_id)))
        title = self.driver_1.find_element_by_id(self.sd_web_id)
        self.assertIsNotNone(title)

    def test_stint_is_most_recent(self):
        additional_sd_count = random.randint(2, 10)
        additional_stintdefs = [create_test_stintdefinition(frontend=self.web) for _ in range(additional_sd_count)]
        additional_stintspecs = [
            StintSpecificationFactory(
                stint_definition=additional_sd, where_to_run=StintSpecification.WHERE_TO_RUN_CHOICES.market, late_arrival=True
            )
            for _ in range(additional_sd_count)
            for additional_sd in additional_stintdefs
        ]
        for additional_stintspec in additional_stintspecs:
            additional_stintspec.allowed_language_frontend_combinations.add(self.language_frontend)
        additional_stints = [additional_stintdefs[i].realize(additional_stintspecs[i]) for i in range(additional_sd_count)]
        for additional_stint in additional_stints[:-1]:
            additional_stint.start(self.dj_man)
        # Next to last random stint
        self.driver_1.get(f'{self.live_server_url}/marketplace/{self.starter_gql_id}')
        md_slug, md_name = (
            additional_stintdefs[-2]
            .stint_definition_module_definitions.values_list('module_definition__slug', 'module_definition__name')
            .first()
        )
        full_recent_id = f'{md_slug.lower()}-stagedefinition0-questions'
        WebDriverWait(self.driver_1, 30).until(EC.presence_of_element_located((By.ID, full_recent_id)))
        module_definition_block = self.driver_1.find_element_by_id(full_recent_id)
        actual_text = module_definition_block.get_attribute('innerHTML')
        expected_text = f"This is the content for the questions block belonging to StageDefinition0 ({md_name})."
        self.assertEqual(actual_text, expected_text)
        hand = additional_stints[-2].hands.get(user__username='comedic_artsy_fun_accountant')
        hand.set_status(random.choice([status for status, _ in hand.STATUS_CHOICES if status != hand.STATUS_CHOICES.active]))
        hand.stint.set_status(Stint.STATUS_CHOICES.cancelled)

        self.stint.start(self.dj_man)
        # Descriptive Norm
        self.driver_1.get(f'{self.live_server_url}/marketplace/{self.starter_gql_id}')
        WebDriverWait(self.driver_1, 30).until(EC.presence_of_element_located((By.ID, self.sd_web_id)))

        title = self.driver_1.find_element_by_id(self.sd_web_id)
        self.assertIsNotNone(title)
        hand = self.stint.hands.get(user__username='comedic_artsy_fun_accountant')
        hand.set_status(random.choice([status for status, _ in hand.STATUS_CHOICES if status != hand.STATUS_CHOICES.active]))
        hand.stint.set_status(Stint.STATUS_CHOICES.cancelled)

        # Last random stint
        additional_stints[-1].start(self.dj_man)
        self.driver_1.get(f'{self.live_server_url}/marketplace/{self.starter_gql_id}')
        md_slug, md_name = (
            additional_stintdefs[-1]
            .stint_definition_module_definitions.values_list('module_definition__slug', 'module_definition__name')
            .first()
        )
        full_recent_id = f'{md_slug.lower()}-stagedefinition0-questions'
        WebDriverWait(self.driver_1, 30).until(EC.presence_of_element_located((By.ID, full_recent_id)))
        module_definition_block = self.driver_1.find_element_by_id(full_recent_id)
        actual_text = module_definition_block.get_attribute('innerHTML')
        expected_text = f"This is the content for the questions block belonging to StageDefinition0 ({md_name})."
        self.assertEqual(actual_text, expected_text)

    def test_stint_with_one_user(self):
        self.stint.start(self.dj_man)
        # XXX: Can't have more than one dropdown on page?
        self.driver_1.get(f'{self.live_server_url}/marketplace/{self.starter_gql_id}')
        WebDriverWait(self.driver_1, 30).until(EC.presence_of_element_located((By.ID, self.sd_web_id)))
        title = self.driver_1.find_element_by_id(self.sd_web_id)
        wow_name_widget_xpath = "//span[@class='widget']/div/div/div"
        WebDriverWait(self.driver_1, 10).until(EC.presence_of_element_located((By.XPATH, wow_name_widget_xpath)))
        dropdown = self.driver_1.find_element_by_xpath(wow_name_widget_xpath)
        dropdown.click()

        time_interval = 1
        # XXX: Add ids to selects
        select_xpath = "//ul[@class='MuiList-root MuiMenu-list MuiList-padding']/li[2]"
        WebDriverWait(self.driver_1, 10).until(EC.presence_of_element_located((By.XPATH, select_xpath)))
        select = self.driver_1.find_element_by_xpath(select_xpath)
        select.click()
        time.sleep(time_interval)
        radio_buttons_xpath = "//span[@class='widget']/fieldset/div/label[1]/span/span/input"
        district_selection = self.driver_1.find_elements_by_xpath(radio_buttons_xpath)[0]
        district_selection.click()
        time.sleep(time_interval)
        ward_selection = self.driver_1.find_elements_by_xpath(radio_buttons_xpath)[1]
        ward_selection.click()
        time.sleep(time_interval)
        household_id_xpath = "//span[@class='widget']/span[@class='widget']/div/input"
        household_id_widget = self.driver_1.find_element_by_xpath(household_id_xpath)
        household_id_widget.send_keys('alpha')
        title.click()
        time.sleep(time_interval)
        submit_button = Widget.objects.get(name='SubmitButton')
        submit_button_id = f'{submit_button.slug.lower()}'
        submit_button_web = self.driver_1.find_element_by_id(submit_button_id)
        submit_button_web.click()

    def test_single_user_stint_reentry(self):
        self.stint.start(self.dj_man)
        self.driver_1.get(f'{self.live_server_url}/marketplace/{self.starter_gql_id}')
        WebDriverWait(self.driver_1, 30).until(EC.presence_of_element_located((By.ID, self.sd_web_id)))

        title = self.driver_1.find_element_by_id(self.sd_web_id)
        self.assertIsNotNone(title)

        additional_stintdef = create_test_stintdefinition(frontend=self.web)
        additional_stintspec = StintSpecificationFactory(
            stint_definition=additional_stintdef,
            where_to_run=StintSpecification.WHERE_TO_RUN_CHOICES.market,
            late_arrival=True,
        )
        additional_stintspec.allowed_language_frontend_combinations.add(self.language_frontend)
        additional_stint = additional_stintdef.realize(additional_stintspec)
        additional_stint.start(self.dj_man)

        self.driver_1.get(f'{self.live_server_url}/marketplace/{self.starter_gql_id}')
        WebDriverWait(self.driver_1, 10).until(EC.presence_of_element_located((By.ID, self.sd_web_id)))

        title = self.driver_1.find_element_by_id(self.sd_web_id)
        self.assertIsNotNone(title)

    def test_login_redirect(self):
        "If not logged in, user should be redirected based on settings"
        driver = get_chromedriver()
        self.stint.start(self.dj_man)
        driver.get(f'{self.live_server_url}/marketplace/{self.starter_gql_id}')
        WebDriverWait(driver, 10).until(lambda x: 'Behavery 2.0 beta' in driver.title)

    def test_repeated_user(self):
        """Confirm user can take same stint repeatedly after initial completion"""
        self.stint.start(self.dj_man)
        self.driver_1.get(f'{self.live_server_url}/marketplace/{self.starter_gql_id}')
        WebDriverWait(self.driver_1, 30).until(EC.presence_of_element_located((By.ID, self.sd_web_id)))
        hand = self.stint.hands.get(user__username='comedic_artsy_fun_accountant')
        hand.set_status(hand.STATUS_CHOICES.finished)
        for _ in range(3):
            self.driver_1.get(f'{self.live_server_url}/marketplace/{self.starter_gql_id}')
            WebDriverWait(self.driver_1, 30).until(EC.presence_of_element_located((By.ID, self.sd_web_id)))
            hand.set_status(hand.STATUS_CHOICES.finished)
