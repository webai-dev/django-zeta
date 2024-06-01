from multiprocessing import Process
import random
import time

import django  # pylint: disable=unused-import
from django.conf import settings  # pylint: disable=unused-import

from django.utils.crypto import get_random_string

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ery_backend.base.testcases import get_chromedriver
from ery_backend.labs.models import Lab
from ery_backend.stints.models import StintDefinition, Stint
from ery_backend.users.models import User
from ery_backend.widgets.models import Widget


def setup(test_count):
    from scripts.lenns_demo.install_lenns import setup as setup_sd  # pylint: disable=no-name-in-module, import-error

    setup_sd()
    user = User.objects.first()
    lab = Lab.objects.get_or_create(secret='lenns', name='lennslab')[0]
    stint_definition = StintDefinition.objects.get(name='LennsProject')
    stint_specification = stint_definition.specifications.first()
    lab.set_stint(stint_specification.id, user)
    lab.start(test_count, user)


def run_test(counter):
    stint = Stint.objects.get(stint_specification__stint_definition__name='LennsProject')
    driver = get_chromedriver(headless=True)
    hand = stint.hands.get(user__username=f'__lab__:lenns:{counter}')
    toolbar_id = 'djHideToolBarButton'
    cycles = random.randint(1, 2)
    driver.get(f'localhost:8000/lab/lenns/{counter}')
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, toolbar_id)))
    driver.find_element_by_id(toolbar_id).click()
    # stage_1
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, "testmd-lennswelcome")))
    stage_template = hand.stage.stage_definition.stage_templates.get(template__frontend=hand.frontend)
    lenns_child_forward_template = stage_template.template
    next_button_template_widget = lenns_child_forward_template.template_widgets.get(widget__name='NextButton')
    next_button_widget = next_button_template_widget.widget
    next_button_id = (
        f'{lenns_child_forward_template.slug.lower()}-{next_button_widget.slug.lower()}'
        f'-{next_button_template_widget.widget.name}'
    )
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, next_button_id)))
    next_button = driver.find_element_by_id(next_button_id)
    next_button.click()
    # stage_2
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, "testmd-lennsinputs")))
    hand.refresh_from_db()
    stage_template = hand.stage.stage_definition.stage_templates.get(template__frontend=hand.frontend)
    lenns_child_progression_template = stage_template.template
    num_inputs = driver.find_elements_by_xpath("//span[@class='widget']/div/div/input")
    text_input = driver.find_element_by_xpath("//span[@class='widget']/div/div/div/input")
    for _ in range(cycles):
        num_inputs[0].send_keys(get_random_string())
        num_inputs[0].send_keys(str(random.randint(0, 5500)))
    for _ in range(cycles):
        num_inputs[1].send_keys(get_random_string())
        num_inputs[1].send_keys(str(round(random.random(), 10)))
    text_input.send_keys(get_random_string())
    next_button_template_widget = lenns_child_forward_template.template_widgets.get(widget__name='NextButton')
    next_button_widget = next_button_template_widget.widget
    next_button_id = (
        f'{lenns_child_progression_template.slug.lower()}-'
        f'{next_button_widget.slug.lower()}-{next_button_template_widget.widget.name}'
    )
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, next_button_id)))
    next_button = driver.find_element_by_id(next_button_id)
    next_button.click()
    # stage_3
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, "testmd-lennsmultiplechoice")))
    hand.refresh_from_db()
    choice_inputs = driver.find_elements_by_xpath("//span[@class='widget']/fieldset/div/label/span[1]/span[1]/input")
    for _ in range(cycles):
        random.choice(choice_inputs).click()
    next_button_template_widget = lenns_child_forward_template.template_widgets.get(widget__name='NextButton')
    next_button_widget = next_button_template_widget.widget
    next_button_id = (
        f'{lenns_child_progression_template.slug.lower()}-{next_button_widget.slug.lower()}'
        f'-{next_button_template_widget.widget.name}'
    )
    next_button = driver.find_element_by_id(next_button_id)
    next_button.click()
    # stage_4
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, "testmd-lennsdropdown")))
    dropdown = driver.find_element_by_xpath("//span[@class='widget']/div//div[2]/div")
    dropdown.click()
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.XPATH, "//div/div[3]/ul/li")))
    options = driver.find_elements_by_xpath("//div/div[3]/ul/li")
    random.choice(options).click()
    WebDriverWait(driver, 100).until_not(EC.presence_of_element_located((By.XPATH, "//div/div[3]/ul/li")))
    time.sleep(1)
    # def click_choice(choices):
    #     try:
    #         time.sleep(1)
    #         driver.execute_script("arguments[0].click();", random.choice(options))
    #         return True
    #     except Exception:
    #         return False
    # a = False
    # while not a:
    #     a = click_choice(options)
    # print("YES")
    next_button_template_widget = lenns_child_forward_template.template_widgets.get(widget__name='NextButton')
    next_button_widget = next_button_template_widget.widget
    next_button_id = (
        f'{lenns_child_progression_template.slug.lower()}-{next_button_widget.slug.lower()}'
        f'-{next_button_template_widget.widget.name}'
    )
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, next_button_id)))
    next_button = driver.find_element_by_id(next_button_id)
    next_button.click()
    # stage_5
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, "testmd-lennsend")))
    module_definition = hand.current_module.module_definition
    widget = Widget.objects.get(name='WebButton')
    calculate_button_id = f'{module_definition.slug.lower()}-{widget.slug.lower()}' f'-ResponseCalculatorButton'
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, next_button_id)))
    calculate_button = driver.find_element_by_id(calculate_button_id)
    calculate_button.click()
    time.sleep(10)
    driver.close()


def run(counter):
    counter = int(counter)
    setup(counter)
    processes = [Process(target=run_test, args=(i,)) for i in range(1, counter + 1)]
    for process in processes:
        process.start()
    for process in processes:
        process.join()
