import bs4
import json
import re
import requests
import urllib.parse
from typing import Dict, Tuple, NamedTuple, List


class LoginCheckError(Exception):
    pass


class ResourceError(Exception):
    pass


class User(NamedTuple):
    rank: int
    username: str
    frames_rendered: int
    time_rendered: int
    points_earned: int


class Machine(NamedTuple):
    id: int
    nickname: str
    machine: str


class Sheepit:
    __session: requests.Session
    __sheepit_url: str = "https://www.sheepit-renderfarm.com"
    __logged_in: bool = False

    def __init__(self, password_file: str):
        """
        Start sheepit session, logging in using the provided password file

        :param password_file:    login details for sheepit in json format
        """

        self.__session = requests.Session()

        self.login(password_file)

    def __del__(self):
        self.logout()

    def login(self, password_file: str) -> bool:
        if self.is_logged_in():
            return True

        username, password = self.__load_password_file(password_file)

        login_payload = {
            "account_login": "account_login",
            "do_login": "do_login",
            "login": username,
            "password": password
        }

        login_response = self.__session.post(self.__sheepit_url + "/ajax.php", data=login_payload)

        return login_response.content == b"OK"

    def is_logged_in(self) -> bool:
        if self.__logged_in:
            return True
        login_response = self.__sheepit_request("/account.php")
        if login_response.url == self.__sheepit_url + "/account.php?mode=profile":
            self.__logged_in = True
            return True
        elif login_response.url == self.__sheepit_url + "/account.php?mode=login":
            self.__logged_in = False
            return False
        else:
            self.__logged_in = False
            raise LoginCheckError(f"Unknown redirect url during login check: {login_response.url}")

    @staticmethod
    def __load_password_file(password_file: str) -> Tuple[str, str]:
        with open(password_file, 'r') as pf:
            parsed: Dict[str, str] = json.load(pf)
            username = parsed['user']
            password = parsed['pass']

            return username, password

    def logout(self):
        if self.__logged_in:
            self.__sheepit_request("/account.php", params={"mode": "logout"})
            self.__logged_in = False

    def list_users(self) -> List[User]:
        scoreboard_response = self.__sheepit_request("/renderers.php")

        soup = bs4.BeautifulSoup(scoreboard_response.content, "html5lib")

        table_body: bs4.Tag = soup.select("table > tbody")[0]

        user_list: List[User] = []

        for row in table_body.find_all('tr'):  # type: bs4.Tag
            rank_tag, user_tag, frames_tag, time_tag, points_tag = row.find_all('td')  # type: bs4.Tag

            rank: int = self.__parse_user_rank(rank_tag.text.strip())
            user: str = user_tag.find_all('a')[1].text.strip()
            frames: int = self.__parse_user_frame_count(frames_tag.text.strip())
            time: int = self.__parse_user_render_time(time_tag.text.strip())
            points: int = self.__parse_user_points(points_tag.text.strip())

            user_list.append(User(rank, user, frames, time, points))

        return user_list

    @staticmethod
    def __parse_user_rank(rank: str) -> int:
        return int(re.match(r"([\d,]+)\w*", rank).group(1).replace(",", ""))

    @staticmethod
    def __parse_user_frame_count(frames: str) -> int:
        return int(frames.replace(",", ""))

    @staticmethod
    def __parse_user_render_time(time: str) -> int:
        match = re.match(r"(?:([\d]+)y)?(?:([\d]+)d)?(?:([\d]+)h)?", time)

        total_hours = 0

        years = match.group(1)
        days = match.group(2)
        hours = match.group(3)

        if years is not None:
            total_hours += int(years) * 24 * 365
        if days is not None:
            total_hours += int(days) * 24
        if hours is not None:
            total_hours += int(hours)

        return total_hours

    @staticmethod
    def __parse_user_points(points: str) -> int:
        match = re.match("([\\d.]+)(?: (k|M))?", points)

        if match is None:
            return 0

        points = float(match.group(1))
        suffix = match.group(2)

        if suffix is not None:
            if suffix == "k":
                points *= 1000
            elif suffix == "M":
                points *= 1000000

        return int(points)

    def get_user_data(self, user: str):
        userpage_response = self.__sheepit_request("/account.php", params={"mode": "profile", "login": user})

        soup = bs4.BeautifulSoup(userpage_response.content, "html5lib")

        # Check for error
        error_selection = soup.select_one("body > section")
        if error_selection is not None and 'color-one' in error_selection['class']:
            return None

        container: bs4.Tag = soup.find("div", id="masonryWr")

        data_sections: List[bs4.Tag] = container.find_all("div", attrs={"class": ["w-box", "blog-post"]})

        for section in data_sections:
            header: bs4.Tag = section.find("h2")
            if header is not None and re.match(r"(?:\d+ )?Connected Machines?", header.text, flags=re.IGNORECASE):
                pass

    @staticmethod
    def __parse_user_connected_sessions(section: bs4.Tag) -> List[Machine]:
        machines: List[bs4.Tag] = section("a")

        machine_info: List[Machine] = []

        for machine in machines:
            q = urllib.parse.urlparse(machine['href']).query
            id = int(urllib.parse.parse_qs(q)['id'][0])

            name_match = re.match(r"\(([^)]+)\)\s*(.*)", machine.text)
            nickname = name_match.group(1)
            machine = name_match.group(2)

            machine_info.append(Machine(id, nickname, machine))

        return machine_info

    def __sheepit_request(self, url, **kwargs) -> requests.Response:
        response = self.__session.get(self.__sheepit_url + url, **kwargs)

        if response.status_code >= 400:
            raise ResourceError(f"Unknown error on request to {response.url}. Response {response.status_code}.")

        return response
