import time
import lxml.html
import requests
from ery_backend.widgets.models import Widget
from ery_backend.frontends.models import Frontend

# There are a few names unintentionally caught by XPATH.
# Ignored during widget creation
EXCLUDES = ['Page Layout Examples', 'Premium Themes']
# These aren't intuitive and need prepending
ADDRESS_ADDITIONS = {'TouchRipple': 'ButtonBase', 'MuiThemeProvider': 'styles'}


def _get_parsed_content():
    url = 'https://material-ui.com'
    doc = requests.get(url)
    return lxml.html.fromstring(doc.content)


def get_chromedriver():
    """
    Returns:
        An instance of Google Chrome webdriver
    """
    import os
    from selenium import webdriver

    return webdriver.Chrome(f'{os.getcwd()}/drivers/chromedriver')


def get_component_names():
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver = get_chromedriver()
    driver.get('https://material-ui.com')
    menu_drawer = driver.find_element_by_xpath("//button[contains(@aria-label, 'Open drawer')]")
    menu_drawer.click()
    component_drawer = driver.find_element_by_xpath("//button/descendant::span[contains(text(), 'Component API')]")
    wait = WebDriverWait(driver, 30)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button/descendant::span")))
    component_drawer.click()
    time.sleep(2)
    elements = [element.get_attribute('innerHTML') for element in driver.find_elements_by_xpath("//li/a/span")]
    return [name for name in elements if name not in EXCLUDES]


def create_widgets():
    """
    Add :class:`~ery_backend.widgets.models.BuiltInWidget` instances for components found on material-ui webpage
    but not in database.
    """
    names = get_component_names()
    for name in names:
        widget_kwargs = {
            'name': f'{name}',
            'comment': 'Wrapper for Material Design Component',
            'frontend': Frontend.objects.get(name='Web'),
            'external': True,
        }
        if name in ADDRESS_ADDITIONS:
            widget_kwargs['address'] = f'material-ui/core/{ADDRESS_ADDITIONS[name]}/{name}'
        else:
            widget_kwargs['address'] = f'material-ui/core/{name}'
        widget = Widget.objects.filter(**widget_kwargs).exists()
        if not widget:
            widget_kwargs.update({'namespace': 'mui'})
            Widget.objects.create(**widget_kwargs)


def check_new_widgets():
    """
    For manual review of new :class:`~ery_backend.widgets.models.BuiltInWidget` instances before addition to Ery db.

    Significant due to the incongruence of names of supported components on the material-ui page and the names of the
    corresponding material design components.
    """
    names = get_component_names()
    new_widgets = list()
    for name in names:
        if not Widget.objects.filter(name=f'MUI.{name}').exists():
            new_widgets.append(name)
    if new_widgets:
        print(f"The following widgets are new and do not exist in the db: {new_widgets}")
    else:
        print("No new  widgets found.")
