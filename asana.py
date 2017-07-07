"""
Usage:
    asana
    asana -t
    asana -e <email>
    asana -p <projects>
    asana -s <save_path>
    asana -u <url>

Options:
    -t      Test login
    -e      Set email login, asking for password separately
    -p      Project class IDs, separated by commas
    -s      Save path
    -u      Url for Asana

Arguments:
    email          Email address
    projects       Class IDs of project to be added, separated by commas
    save_path      The path to save your files to
    url            The login url of Asana

"""
from docopt import docopt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import base64
import configparser
import getpass
import os
import requests
import sys
import time
import datetime
# from selenium.webdriver.remote.webdriver import WebDriver as test  # useful: shows all methods
# ensure to include PhantomJS.exe manually

# Asana API:
# https://asana.com/developers/documentation/getting-started/overview
# for OAuth 2.0 use: pip install requests requests_oauthlib


class Asana:
    def __init__(self, settings_file):
        self.settings_file = settings_file
        self.driver = None
        self.wait = None
        self.current_project = ''
        self.email = ''
        self.password = ''
        self.projects = ''
        self.save_path = ''
        self.url = ''
        self.set_properties_from_config_file()

    def set_properties_from_config_file(self):
        """
        Set class properties, return false if unable to set any
        :return: True if all set ok, false otherwise
        """
        config = configparser.ConfigParser()
        try:
            config.read(self.settings_file)
        except FileNotFoundError:
            return False
        try:
            self.email = config.get('SETTINGS', 'email')
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
        try:
            self.password = base64.b64decode(config.get('SETTINGS', 'password').encode()).decode()
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
        try:
            self.projects = config.get('SETTINGS', 'projects').split(',')
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
        try:
            self.save_path = config.get('SETTINGS', 'save_path')
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
        try:
            self.url = config.get('SETTINGS', 'url')
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
        return self.email and self.password and self.projects and self.save_path and self.url

    def _login(self):
        self.driver = webdriver.Chrome()
        # self.driver = webdriver.PhantomJS()
        self.wait = WebDriverWait(self.driver, 60)
        self.driver.maximize_window()
        self.driver.get(self.url)
        self.wait.until(EC.element_to_be_clickable((By.ID, 'email_input')))
        self.driver.find_element_by_id('email_input').send_keys(self.email)
        self.driver.find_element_by_id('password_input').send_keys(self.password)
        self.driver.find_element_by_id('submit_button').click()
        if self.driver.find_elements_by_id('error_message'):
            if self.driver.find_elements_by_id('error_message')[0].text.find('username or password is not correct') != -1:
                raise LoginError
        self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'project-name')))

    def login(self):
        """
        Login - exit completely if settings fail, login fails
        :return: none
        """
        if not self.set_properties_from_config_file():
            print('Please set all settings first.')
            sys.exit(1)
        try:
            self._login()
            print('Login successful.')
        except LoginError:
            print('Can\'t Login. Check username and password.')
            self.driver.quit()
            sys.exit(1)

    def select_project(self, element_id):
        self._class_wait_click(element_id)  # ED Stabilisation
        self.current_project = element_id

    def export_as_image(self):
        self._class_wait_click(' dropdown-toggle')  # Export & Share
        self._class_wait_click('export-image')  # Export as image
        generate_button = '//*[@id="image-export-modal"]/div[2]/div[1]/table/tbody/tr[4]/td[2]/button'
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, generate_button)))  # Generate
        self.driver.find_element_by_xpath(generate_button).click()
        download_button = '//*[@id="image-export-modal"]/div[2]/div[3]/button'
        self.wait.until(EC.element_to_be_clickable((By.XPATH, download_button)))
        img_url = r'https://instagantt.com/projects/' + self.current_project[self.current_project.find('-') + 1:] + \
                  '/image?download=now'
        now = datetime.datetime.now().strftime('%Y-%m-%d %H-%M')
        self.download_content(img_url, os.path.join(self.save_path, 'saved_image ' + now + '.jpg'))
        # self.driver.switch_to.window(window_name=self.driver.window_handles[1])  # Switch to next tab (not needed)
        self.driver.find_element_by_xpath('//*[@id="image-export-modal"]/div[3]/a').click()  # Close button
        time.sleep(1)  # wait for fade to complete

    def export_as_spreadsheet(self):
        self._class_wait_click(' dropdown-toggle')  # Export & Share
        self._class_wait_click('export-spreadsheet')  # Export as spreadsheet
        self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'day-format')))  # Day format
        Select(self.driver.find_element_by_class_name('day-format')).select_by_value('DD/MM/YYYY')
        generate_button = '//*[@id="xls-export-modal"]/div[2]/div[1]/table/tbody/tr[2]/td[2]/button'
        self.driver.find_element_by_xpath(generate_button).click()
        ss_download_xpath = '//*[@id="xls-export-modal"]/div[2]/div[3]/button'  # Download button
        self.wait.until(EC.element_to_be_clickable((By.XPATH, ss_download_xpath)))
        ss_url = r'https://instagantt.com/projects/' + self.current_project[self.current_project.find('-')+1:] + '/xls'
        now = datetime.datetime.now().strftime('%Y-%m-%d %H-%M')
        self.download_content(ss_url, os.path.join(self.save_path, 'saved_spreadsheet ' + now + '.xlsx'))
        self.driver.find_element_by_xpath('//*[@id="xls-export-modal"]/div[3]/a').click()  # Close button
        time.sleep(1)  # wait for fade to complete

    def download_content(self, download_url, save_to):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/44.0.2403.157 Safari/537.36'
        }
        s = requests.session()
        s.headers.update(headers)
        for cookie in self.driver.get_cookies():
            c = {cookie['name']: cookie['value']}
            s.cookies.update(c)
        with open(save_to, 'wb') as handle:
            response = s.get(download_url, stream=True)
            if not response.ok:
                print('Something went wrong')
                print(str(response))
            for block in response.iter_content(1024):
                handle.write(block)

    def _class_wait_click(self, class_name):
        self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, class_name)))
        self.driver.find_element_by_class_name(class_name).click()

    def write_config_file(self, email='', password='', projects='', save_path='', url=''):
        config = configparser.ConfigParser()
        settings_to_write = {'email': email} if email else {'email': self.email} if self.email else {'email': ''}
        settings_to_write['password'] = base64.b64encode(password.encode()).decode() if password else \
            base64.b64encode(self.password.encode()).decode() if self.password else ''
        settings_to_write['projects'] = projects if projects else ','.join(self.projects) if self.projects else ''
        settings_to_write['save_path'] = save_path if save_path else self.save_path if self.save_path else ''
        settings_to_write['url'] = url if url else self.url if self.url else ''
        config['SETTINGS'] = settings_to_write
        fileout = open(self.settings_file, 'w', newline='')
        config.write(fileout)
        fileout.close()
        self.set_properties_from_config_file()


class LoginError(Exception):
    pass

if __name__ == '__main__':
    args = docopt(__doc__)
    if hasattr(sys, 'frozen'):
        this_module_path = os.path.dirname(sys.executable)
    else:
        this_module_path = os.path.dirname(os.path.realpath(__file__))
    settings_path = os.path.join(this_module_path, 'asana_settings.txt')
    a = Asana(settings_path)

    if args['-t']:  # Test Login
        a.login()
        print('Login test: successful')
        a.driver.quit()
    elif args['-e']:  # Email and Password
        arg_email = args['<email>']
        arg_password = getpass.getpass('Password: ')
        a.write_config_file(arg_email, arg_password)
    elif args['-p']:  # Projects: ED Stabilisation = project-57067c807eae7bc01a000013
        a.write_config_file(projects=args['<projects>'])
    elif args['-s']:  # Save path: '/Users/si/Downloads'
        if not os.path.isdir(args['<save_path>']):
            print('Path isn\'t valid.')
            sys.exit(1)
        a.write_config_file(save_path=args['<save_path>'])
    elif args['-u']:  # Url: 'https://instagantt.com/asana/connect'
        a.write_config_file(url=args['<url>'])
    else:
        a.login()
        for project in a.projects:
            a.select_project(project)
            print('Getting image')
            a.export_as_image()
            print('Getting spreadsheet')
            a.export_as_spreadsheet()
            a.driver.quit()

# Compilation:
# from custom_modules.compile_helper import CompileHelp
# c = CompileHelp(r'C:\simon_files_compilation_zone\asana')
# # c.create_env('docopt selenium requests')
# c.freeze(r'K:\Coding\Python\nbt work\asana.spec',
#          [r'K:\Coding\Python\nbt work\asana_settings.txt'])