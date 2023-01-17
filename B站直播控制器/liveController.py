import obspython as obs
from pathlib import Path
import requests
import json
import os
import subprocess


class Utils:
    HEADERS = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "sec-ch-ua": "\"Not?A_Brand\";v=\"8\", \"Chromium\";v=\"108\", \"Google Chrome\";v=\"108\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    }

    def merge_header(base_header, extra_header):
        merged_header = {}
        merged_header.update(base_header)
        merged_header.update(extra_header)
        return merged_header


class ConfigurationHandler(object):
    def __init__(self, path: str, default_config: dict = {}):
        parent_path = Path(__file__).absolute().parent
        self.path = parent_path / \
            path if not Path(path).is_absolute() else path
        self.config = default_config
        self.default_config = default_config

    def load(self):
        try:
            with open(self.path, 'r') as f:
                self.config = json.loads(f.read())
        except:
            self.config = self.default_config

    def save(self, additional_paths: list = []):
        parent_path = Path(__file__).absolute().parent
        config_str = str(json.dumps(self.config, sort_keys=True, indent=4))
        ref_paths = [self.path]
        for path in additional_paths:
            ref_paths.append(
                parent_path / path if not Path(path).is_absolute() else path
            )

        for path in ref_paths:
            with open(path, 'w') as f:
                f.write(config_str)

    def get_value(self, key, default):
        return self.config.get(key, default)

    def set_value(self, key, value):
        self.config[key] = value

    def remove_key(self, key):
        if self.config.get(key) is not None:
            del self.config[str(key)]


class BiliLive(object):
    def __init__(self, cookies={}, tag_general='', tag_sub='', auto_start=False):
        self.vmid = ''
        self.live_id = ''
        self.login_status = False
        self.cookies = cookies
        self.csrf = ''
        self.tag_general = tag_general
        self.tag_sub = tag_sub
        self.cate_code = 399
        self.auto_start = auto_start
        self.live_status = False
        self.live_title = ''
        if self.cookies != {}:
            self._load_existing_account()

        self.appendix = {}

    def _load_existing_account(self):
        self.login_check_status()
        if self.login_status:
            self.get_liveroom_info()
        self.cate_code = self.liveroom_set_tag(self.get_liveroom_tags())

    @property
    def is_login_required(self):
        return not self.login_status

    def login_check_status(self):
        login_status = False
        user_id = ''
        try:
            req_nav = requests.get(
                'https://api.bilibili.com/x/web-interface/nav',
                headers=Utils.merge_header(Utils.HEADERS, {
                                           "referrer": "https://www.bilibili.com", "origin": "https://www.bilibili.com"}),
                cookies=self.cookies)
            login_status = json.loads(
                req_nav.content).get('data').get('isLogin')
            user_id = self.cookies.get('DedeUserID')
            csrf = self.cookies.get('bili_jct')
            login_status = login_status and (
                user_id is not None) and (csrf is not None)
            self.login_status, self.vmid, self.csrf = login_status, user_id, csrf
        except:
            ...
        finally:
            ...

    def get_liveroom_info(self):
        req_liveroom = requests.get(
            f'https://api.bilibili.com/x/space/wbi/acc/info?mid={self.vmid}',
            headers=Utils.merge_header(Utils.HEADERS, {
                                       "referrer": "https://www.bilibili.com", "origin": "https://www.bilibili.com"}),
            cookies=self.cookies)
        live_room_raw = json.loads(req_liveroom.content).get(
            'data', {}).get('live_room', {})
        live_status = live_room_raw.get('liveStatus', 0) == 1
        live_title = live_room_raw.get('title', '')
        live_roomid = live_room_raw.get('roomid', 0)
        self.live_status, self.live_title, self.live_id = live_status, live_title, live_roomid
        return live_status, live_title, live_roomid

    def logout(self):
        if not self.login_status:
            return
        if self.live_status:
            self.stop_stream()
        req_logout = requests.post(
            'https://passport.bilibili.com/login/exit/v2',
            params={'biliCSRF': self.csrf},
            cookies=self.cookies,
            headers=Utils.merge_header(Utils.HEADERS, {"referrer": "https://www.bilibili.com", "origin": "https://www.bilibili.com"}))
        self.vmid = ''
        self.live_id = ''
        self.login_status = False
        self.cookies = {}
        self.live_status = False
        self.live_title = ''

    def get_liveroom_tags(self):
        req_tags = requests.get(
            'https://api.live.bilibili.com/xlive/web-interface/v1/index/getWebAreaList?source_id=2',
            headers=Utils.merge_header(Utils.HEADERS, {"referrer": "https://link.bilibili.com/p/center/index"}))
        ret_cate_list = {}
        if req_tags.status_code == 200:
            tags_raw = json.loads(req_tags.content).get(
                'data', {}).get('data', {})
            ret_cate_list = {item['name']: (
                item['id'], {li['name']: li['id'] for li in item['list']}) for item in tags_raw}
        return ret_cate_list

    def liveroom_set_tag(self, categories):
        tag_general = categories.get(self.tag_general, (1, {'日常': '399'}))
        self.cate_code = tag_general[1].get(self.tag_sub, 399)

    def get_stream_address(self):
        req_stream_address = requests.post(
            'https://api.live.bilibili.com/xlive/app-blink/v1/live/FetchWebUpStreamAddr',
            headers=Utils.merge_header(Utils.HEADERS, {
                                       "referrer": "https://link.bilibili.com/p/center/index", "origin": "https://link.bilibili.com"}),
            cookies=self.cookies,
            params={'platform': 'pc', 'csrf': self.csrf, 'csrf_token': self.csrf})
        req_stream_idcode = requests.post(
            'https://api.live.bilibili.com/xlive/open-platform/v1/common/operationOnBroadcastCode',
            headers=Utils.merge_header(Utils.HEADERS, {
                                       "referrer": "https://link.bilibili.com/p/center/index", "origin": "https://link.bilibili.com"}),
            cookies=self.cookies,
            params={'action': 1, 'csrf': self.csrf, 'csrf_token': self.csrf})
        result, message, rtmp_addr, rtmp_code, idcode = False, '', '', '', ''
        if req_stream_address.status_code == 200 and req_stream_idcode.status_code == 200:
            stream_address_raw = json.loads(req_stream_address.content)
            stream_idcode_raw = json.loads(req_stream_idcode.content)
            result = stream_address_raw.get(
                'code', 1) == 0 and stream_idcode_raw.get('code', 1) == 0
            message = stream_address_raw.get('message', '')
            if result:
                rtmp_raw = stream_address_raw.get('data', {}).get('addr', {})
                rtmp_addr = rtmp_raw.get('addr', '')
                rtmp_code = rtmp_raw.get('code', '')
                idcode = stream_idcode_raw.get('data', {}).get('code', {})
        return result, message, rtmp_addr, rtmp_code, idcode

    def start_stream(self):
        req_start = requests.post(
            'https://api.live.bilibili.com/room/v1/Room/startLive',
            headers=Utils.merge_header(Utils.HEADERS, {
                                       "referrer": "https://link.bilibili.com/p/center/index", "origin": "https://link.bilibili.com"}),
            cookies=self.cookies,
            params={'room_id': self.live_id, 'platform': 'pc',
                    'area_v2': self.cate_code, 'csrf': self.csrf, 'csrf_token': self.csrf}
        )
        req_report = requests.post(
            'https://api.live.bilibili.com/xlive/app-blink/v1/report/ReportData',
            headers=Utils.merge_header(Utils.HEADERS, {
                                       "referrer": "https://link.bilibili.com/p/center/index", "origin": "https://link.bilibili.com"}),
            cookies=self.cookies,
            params={'type_status': 1, 'platform': 'web', 'is_obs': 1,
                    'csrf': self.csrf, 'csrf_token': self.csrf}
        )
        stream_flag, change_flag, message, status = False, False, '', ''
        if req_start.status_code == 200 and req_report.status_code == 200:
            stream_raw = json.loads(req_start.content)
            stream_flag = stream_raw.get('code', 1) == 0
            message = stream_raw.get('msg', '')
            if stream_flag:
                change_raw = stream_raw.get('data', {})
                change_flag = change_raw.get('change', 0) == 1
                status = change_raw.get('status', '')
        self.live_status = self.get_liveroom_info()[0]
        return stream_flag, change_flag, message, status

    def stop_stream(self):
        req_stop = requests.post(
            'https://api.live.bilibili.com/room/v1/Room/stopLive',
            headers=Utils.merge_header(Utils.HEADERS, {
                                       "referrer": "https://link.bilibili.com/p/center/index", "origin": "https://link.bilibili.com"}),
            cookies=self.cookies,
            params={'room_id': self.live_id, 'platform': 'pc',
                    'csrf': self.csrf, 'csrf_token': self.csrf}
        )
        req_report = requests.post(
            'https://api.live.bilibili.com/xlive/app-blink/v1/report/ReportData',
            headers=Utils.merge_header(Utils.HEADERS, {
                                       "referrer": "https://link.bilibili.com/p/center/index", "origin": "https://link.bilibili.com"}),
            cookies=self.cookies,
            params={'type_status': 2, 'platform': 'web',
                    'csrf': self.csrf, 'csrf_token': self.csrf}
        )
        stop_flag, change_flag, message, status = False, False,  '', ''
        if req_stop.status_code == 200 and req_report.status_code == 200:
            stop_raw = json.loads(req_stop.content)
            stop_flag = stop_raw.get('code', 1) == 0
            message = stop_raw.get('msg', '')
            if stop_flag:
                change_raw = stop_raw.get('data', {})
                change_flag = change_raw.get('change', 0) == 1
                status = change_raw.get('status', '')
        self.live_status = self.get_liveroom_info()[0]
        return stop_flag, change_flag, message, status


proc = None
shown = False
configs = ConfigurationHandler('./src/configurations.json')
configs.load()
bililive = BiliLive(configs.get_value('cookies', {}),
                    configs.get_value('tag_general', ''),
                    configs.get_value('tag_sub', ''),
                    configs.get_value('auto_start', False))


def run_window():
    global proc
    if proc is not None:
        proc.kill()
    path_parent = Path(__file__).absolute().parent
    path_sub = path_parent / './src/wnd.exe'
    if os.path.exists(path_sub):
        proc = subprocess.Popen([path_sub])


def clicked(props, prop):
    run_window()


def script_unload():
    global proc
    if proc is not None:
        proc.kill()
    bililive.stop_stream()


def script_load(settings):
    if bililive.is_login_required == True or bililive.auto_start == False:
        run_window()
    else:
        bililive.liveroom_set_tag(bililive.get_liveroom_tags())
        bililive.start_stream()


def script_properties():
    props = obs.obs_properties_create()
    btn = obs.obs_properties_add_button(
        props, 'btn_show_wnd', '显示控制面板', clicked)
    return props
    ...


def script_description():
    return 'B站自动开播控制脚本.'
