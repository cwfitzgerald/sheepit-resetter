import pprint
from typing import Optional, Tuple, List
from getpass import getpass
import json
import os
from sheepit import Sheepit

import bs4
from bs4 import BeautifulSoup
import requests

sheepit_url = "https://www.sheepit-renderfarm.com"


def get_login_file() -> Tuple[str, str]:
    with open("password.json") as f:
        res = json.load(f)
        return res['user'], res['pass']


def get_login() -> Tuple[str, str]:
    username: str = input("Username: ").strip()
    password: str = getpass("Password: ").strip()

    return username, password


def login(sess: requests.Session, username: str, password: str) -> bool:
    login_data = {
        "account_login": "account_login",
        "do_login": "do_login",
        "login": username,
        "password": password
    }

    lr = sess.post(sheepit_url + "/ajax.php", data=login_data)

    if lr.content != b"OK":
        print("Failed Login.")
        print(lr.content)
        return False

    return True


def logout(sess: requests.Session) -> None:
    out_r = sess.get(sheepit_url + "/account.php", params={"mode": "logout"})

    if out_r.status_code != 200:
        print("failed logout")
        exit(1)


def get_project_list(sess: requests.Session) -> List[Tuple[str, str]]:
    result_obj = sess.get(sheepit_url + "/fulladmin.php?show=scene")

    result = result_obj.content
    parsed = BeautifulSoup(result, "html5lib")
    table: bs4.Tag = parsed.find("table").find("tbody")

    projects: List[Tuple[str, str]] = []

    for row in table.find_all("tr"):  # type: bs4.Tag
        project_element: bs4.Tag = row.find_all('td')[1].find('a')

        project_name = project_element.text
        project_url = project_element['href']
        projects.append((project_name, project_url))

    return projects


def get_machine_list(sess: requests.Session, user: str) -> List[Tuple[str, str]]:
    result_obj = sess.get(sheepit_url + f"account.php?mode=profile&login={user}")

    result = result_obj.content
    parsed = BeautifulSoup(result, "html5lib")



def main_old() -> None:
    sess = requests.session()

    logged_in: bool = False

    if os.path.exists("cookies.txt"):
        with open("cookies.txt", 'r') as f:
            sess.cookies = requests.utils.cookiejar_from_dict(json.load(f))
            logged_in = True

    while not logged_in:
        username, password = get_login_file()
        logged_in = login(sess, username, password)

    projects = get_project_list(sess)
    print(f"Found {len(projects)} projects.")

    print(f"Choose the frames to reset. If it's all of one user, leave project and machine blank."
          f"If it's all one project, leave user and machine blank.")

    project = input("Project: ")
    user = input("User: ")
    machine = input("Machine id: ")



    cookie_dict = requests.utils.dict_from_cookiejar(sess.cookies)

    with open("cookies.txt", 'w') as f:
        json.dump(cookie_dict, f)

    # logout

def main():
    s = Sheepit("password.json")

    pprint.pprint(s.get_user_data("sirflankalot"))


if __name__ == '__main__':
    main()
