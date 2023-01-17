from PyQt5 import uic, QtCore
from PyQt5.QtCore import QThread, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow
from pathlib import Path
import requests
import json
import base64
from urllib.parse import quote_plus


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

    scan_status_text = {
        '0': '<strong style="color:red">二维码失效.</strong>',
        '1': '<strong style="color:orange">二维码未扫描.</strong>',
        '2': '<strong style="color:yellow">二维码待确认.</strong>',
        '3': '<strong style="color:green">二维码已确认.</strong>',
        '4': '<strong style="color:magenta">未知状态.</strong>'}

    login_status_text = {
        'False': '<strong style="color:gray">未登录.</strong>',
        'True': '<strong style="color:green">已登录.</strong>'}

    live_status_text = {
        'False': '<strong style="color:gray">未开播.</strong>',
        'True': '<strong style="color:green">已开播.</strong>'}

    def merge_header(base_header, extra_header):
        merged_header = {}
        merged_header.update(base_header)
        merged_header.update(extra_header)
        return merged_header

    def url_get_params(callback_url):
        params_dict = {}
        if callback_url != '':
            params_str = callback_url.split('/')[-1].split('?')[-1].split('&')
            for item in params_str:
                params_dict[item.split('=')[0]] = item.split('=')[1]
        return params_dict


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

    def passport_generate_qr_code(self):
        qr_key = ''
        qrcode_b64 = '<strong style="color:red">登录二维码加载失败.</strong>'
        req_qrcode_generate = requests.get(
            'https://passport.bilibili.com/x/passport-login/web/qrcode/generate?source=main-web',
            headers=Utils.merge_header(Utils.HEADERS, {"referrer": "https://www.bilibili.com", "origin": "https://www.bilibili.com"}))
        qr_key = json.loads(req_qrcode_generate.content).get(
            'data').get('qrcode_key')
        qr_address = json.loads(
            req_qrcode_generate.content).get('data').get('url')
        req_qrcode_image = requests.get(
            f'https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={quote_plus(qr_address)}',
            Utils.HEADERS)
        qrcode_raw = str(base64.b64encode(
            req_qrcode_image.content).decode())
        qrcode_b64 = f'<img src="data:image/png;base64,{qrcode_raw}"></img>'

        self.appendix['qr_key'] = qr_key
        self.appendix['qr_code'] = qrcode_b64

        return qr_key, qrcode_b64

    def qrcode_check_status(self):
        """
            |id|     desc     |code |
            |0 |   invalid    |86038|
            |1 | not scanned  |86101|
            |2 |not confirmed |86090|
            |3 |   confirmed  |0    |
            |4 |    unknown   |-----|
        """
        code_dict = {'86038': 0, '86101': 1, '86090': 2, '0': 3}
        status = 4
        self.cookies = {}
        try:
            req_qrcode_poll = requests.get(
                f'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={self.appendix["qr_key"]}',
                headers=Utils.merge_header(Utils.HEADERS, {"referrer": "https://www.bilibili.com", "origin": "https://www.bilibili.com"}))
            status_json = json.loads(req_qrcode_poll.content).get('data')
            status = code_dict.get(str(status_json['code']))
            self.cookies = Utils.url_get_params(status_json['url'])
        except:
            ...
        finally:
            return status

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

    def update_liveroom_name(self, new_name='undefined'):
        req_update = requests.post(
            'https://api.live.bilibili.com/room/v1/Room/update',
            headers=Utils.merge_header(Utils.HEADERS, {
                                       "referrer": "https://link.bilibili.com/p/center/index", "origin": "https://link.bilibili.com"}),
            cookies=self.cookies,
            params={'room_id': self.live_id, 'title': new_name, 'csrf': self.csrf, 'csrf_token': self.csrf})
        update_flag = False
        if req_update.status_code == 200:
            update_flag = json.loads(req_update.content).get('code', 405) == 0
        return update_flag

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

    def export_config(self):
        ret = {'cookies': self.cookies,
               'tag_general': self.tag_general, 'tag_sub': self.tag_sub}
        return ret


class CLSWndRefresh(QThread):
    sig_wnd_refresh = QtCore.pyqtSignal(name='sig_wnd_refresh')

    def __init__(self, bililive):
        QThread.__init__(self)
        self.tmr = QTimer(self)
        self.bililive = bililive

    def run(self):
        self.tmr.timeout.connect(self.timeout)
        self.tmr.start(1000)

    def terminate(self):
        self.tmr.killTimer(self.tmr.timerId())
        self.quit()

    def timeout(self):
        tmp_login_status = self.bililive.appendix.get('login_status')
        tmp_live_status = self.bililive.appendix.get('live_status')
        tmp_login_account = self.bililive.appendix.get('login_account')
        try:
            self.bililive.appendix[
                'login_status'] = f'登录状态 : {Utils.login_status_text[str(self.bililive.login_status)]}'
            self.bililive.appendix[
                'live_status'] = f'直播状态 : {Utils.live_status_text[str(self.bililive.get_liveroom_info()[0])]}'
            self.bililive.appendix[
                'login_account'] = '登录账户: <strong style="color:{}">{}</strong>'.format(
                ('green' if self.bililive.login_status else 'gray'),
                ('未知.' if not self.bililive.login_status else str(self.bililive.vmid)))
        finally:
            if (tmp_login_status != self.bililive.appendix.get('login_status') or tmp_live_status != self.bililive.appendix.get('live_status') or tmp_login_account != self.bililive.appendix.get('login_account')):
                self.sig_wnd_refresh.emit()


class CLSQRLogin(QThread):
    sig_qr_login = QtCore.pyqtSignal(name='sig_login')

    def __init__(self, bililive):
        QThread.__init__(self)
        self.tmr = QTimer(self)
        self.bililive = bililive

    def run(self):
        self.tmr.timeout.connect(self.timeout)
        self.tmr.start(500)

    def terminate(self):
        self.tmr.killTimer(self.tmr.timerId())
        self.quit()

    def timeout(self):
        if self.bililive.login_status:
            if self.bililive.appendix.get('qr_code') is not None:
                del self.bililive.appendix['qr_code']
                self.sig_qr_login.emit()
            return
        tmp_qr = self.bililive.appendix.get('qr_code')
        tmp_qr_status = self.bililive.appendix.get('qrcode_status')
        try:
            if self.bililive.appendix.get('qr_code') is None:
                self.bililive.passport_generate_qr_code()
            qr_status = self.bililive.qrcode_check_status()
            if qr_status == 0 or qr_status == 4:
                self.bililive.passport_generate_qr_code()
            self.bililive.appendix[
                'qrcode_status'] = f'二维码状态 : {Utils.scan_status_text[str(qr_status)]}'
            self.bililive.login_check_status()
        finally:
            if (tmp_qr != self.bililive.appendix.get('qr_code') or tmp_qr_status != self.bililive.appendix.get('qrcode_status')):
                self.sig_qr_login.emit()


class ConfWindow(QMainWindow):
    def __init__(self, bililive, configs):
        self.bililive = bililive
        self.configs = configs
        QMainWindow.__init__(self)
        uic.loadUi(f'{Path(__file__).absolute().parent}/conf.ui', self)
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint |
                            QtCore.Qt.WindowMinimizeButtonHint)
        self.setWindowTitle('直播插件控制面板')
        self.setFixedSize(self.size())
        
        self.btn_logout.clicked.connect(self.btn_logout_clicked)
        self.btn_switch_live_status.clicked.connect(
            self.btn_switch_live_status_clicked)
        self.btn_apply_changes.clicked.connect(self.btn_apply_changes_clicked)

        self.list_tags_general.currentTextChanged.connect(
            self.list_tags_general_text_changed)

        self.cls_wnd_refresh = CLSWndRefresh(self.bililive)
        self.thd_wnd_refresh = QThread(self)
        self.cls_wnd_refresh.moveToThread(self.thd_wnd_refresh)
        self.thd_wnd_refresh.started.connect(self.cls_wnd_refresh.run)
        self.cls_wnd_refresh.sig_wnd_refresh.connect(self.wnd_refresh)

        self.cls_qr_login = CLSQRLogin(self.bililive)
        self.thd_qr_login = QThread(self)
        self.cls_qr_login.moveToThread(self.thd_qr_login)
        self.thd_qr_login.started.connect(self.cls_qr_login.run)
        self.cls_qr_login.sig_qr_login.connect(self.qr_login)

        self.thd_wnd_refresh.start()
        self.thd_qr_login.start()

    def wnd_refresh(self):
        self.label_login_status.setText(self.bililive.appendix.get(
            'login_status',
            '登录状态 : <strong style="color:gray">未登录.</strong>'))

        self.label_live_status.setText(self.bililive.appendix.get(
            'live_status',
            '直播状态 : <strong style="color:gray">未开播.</strong>'))

        self.label_login_uid.setText(self.bililive.appendix.get(
            'login_account',
            '登录账户: <strong style="color:gray">未知.</strong>'))

    def qr_login(self):
        self.bililive.get_liveroom_info()
        self.text_title.setText(self.bililive.live_title)
        self.label_qrcode.setText(self.bililive.appendix.get(
            'qr_code',
            '<strong style="color:gray">未生成二维码或已登录.</strong>'))
        self.label_qrcode_status.setText(self.bililive.appendix.get(
            'qrcode_status',
            '二维码状态 : <strong style="color:gray">未生成二维码.</strong>'))

    def btn_logout_clicked(self, e):
        self.bililive.logout()
        self.thd_qr_login.start()
        self.text_title.setText(self.bililive.live_title)

    def btn_switch_live_status_clicked(self, e):
        self.bililive.tag_general = self.list_tags_general.currentText()
        self.bililive.tag_sub = self.list_tags_sub.currentText()
        self.bililive.liveroom_set_tag(self.bililive.get_liveroom_tags())

        if self.bililive.live_status:
            self.bililive.stop_stream()

        else:
            self.bililive.start_stream()

    def btn_apply_changes_clicked(self, e):
        self.bililive.tag_general = self.list_tags_general.currentText()
        self.bililive.tag_sub = self.list_tags_sub.currentText()
        self.bililive.liveroom_set_tag(self.bililive.get_liveroom_tags())
        self.bililive.update_liveroom_name(self.text_title.text())
        self.bililive.auto_start = self.checkbox_auto_live.checkState()

        self.configs.set_value('cookies', self.bililive.cookies),
        self.configs.set_value('tag_general', self.bililive.tag_general),
        self.configs.set_value('tag_sub', self.bililive.tag_sub),
        self.configs.set_value('auto_start', self.bililive.auto_start)
        self.configs.save()

    def list_tags_general_text_changed(self, e):
        self.list_tags_sub.clear()
        cates = self.bililive.get_liveroom_tags()
        tags_sub = list(cates.get(str(e), (1, {'日常': '399'}))[1].keys())
        self.list_tags_sub.addItems(tags_sub)

    def showEvent(self, e):
        self.list_tags_general.clear()
        cates = self.bililive.get_liveroom_tags()
        tag_general = list(cates.keys())
        self.list_tags_general.addItems(tag_general)
        if self.bililive.tag_general != '':
            self.list_tags_general.setCurrentText(self.bililive.tag_general)
        if self.bililive.tag_sub != '':
            self.list_tags_sub.setCurrentText(self.bililive.tag_sub)
        self.checkbox_auto_live.setCheckState(self.bililive.auto_start)
        self.text_title.setText(self.bililive.live_title)

    def closeEvent(self, e):
        self.bililive.stop_stream()
        self.btn_apply_changes_clicked(None)
        # self.cls_wnd_refresh.terminate()
        # self.cls_qr_login.terminate()
        self.thd_qr_login.terminate()
        self.thd_wnd_refresh.terminate()
        e.accept()


configs = ConfigurationHandler('./configurations.json')
configs.load()
bililive = BiliLive(configs.get_value('cookies', {}),
                    configs.get_value('tag_general', ''),
                    configs.get_value('tag_sub', ''),
                    configs.get_value('auto_start', False))
if bililive.auto_start:
    bililive.liveroom_set_tag(bililive.get_liveroom_tags())
    bililive.start_stream()


QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QApplication.setQuitOnLastWindowClosed(True)
app = QApplication([])
wnd = ConfWindow(bililive, configs)
wnd.show()
app.exec_()
