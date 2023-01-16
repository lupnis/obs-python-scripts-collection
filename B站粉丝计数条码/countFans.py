import obspython as obs
from pathlib import Path
import json
import time
import threading
from flask import Flask, render_template_string
from flask_cors import CORS
from gevent import pywsgi as wsgi
import requests


class FansCounterWebServer(object):
    def __init__(self, vmid, refresh=1000):
        self.vmid = vmid
        self.refresh = refresh
        self.thread = None
        self.ctrl = None

    def change_vmid_refresh(self, vmid, refresh=1000):
        self.vmid = vmid
        self.refresh = refresh

    def run(self):
        self.active = True
        self.thread = threading.Thread(target=self._thread)
        self.thread.start()

    def _thread(self):
        self.ctrl = wsgi.WSGIServer(
            ('0.0.0.0', 8192), self.flask_app(), log=None)
        self.ctrl.serve_forever()

    def flask_app(self):
        app = Flask(__name__)
        CORS(app)
        @app.route('/s')
        def splash(): return ''

        @app.route('/', methods=['GET'])
        def fans_card():
            ret_str = '''<html><head><script src="https://code.jquery.com/jquery-3.6.3.min.js"></script><script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/barcodes/JsBarcode.code128.min.js"></script><style>@import url('https://fonts.googleapis.com/css2?family=Odibee+Sans&display=swap');.container{height:220pt;display:flex;align-items:center;}.container .notify{font-family:'Odibee Sans',cursive;position:absolute;font-size:80pt;color:#ff6300;left:350pt;animation:slide 2s ease-in-out forwards;-webkit-text-stroke:3px #000000;}@keyframes slide{0%{padding-bottom:40pt;opacity:0;}80%{padding-bottom:75pt;opacity:1;}100%{padding-bottom:120pt;opacity:0;}}</style></head><body><div class="container" id="container"><svg id="val"></svg><p class="notify" id="plus"></p></div><script type="text/javascript">var uid,refresh_t,fans_count=0;refresh_t='''+str(
                self.refresh)+''';JsBarcode('#val','0000',{width:10,height:100,displayValue:false,background:'transparent'});setInterval(getFans,refresh_t);function getFans(){var new_val='0000';$.ajax({url:'gf',type:'GET',cache:false,success:function(data){new_val=eval(data);},async:false});if(parseInt(new_val)>parseInt(fans_count)){document.getElementById('container').innerHTML='<svg id="val"></svg><p class="notify" id="plus"></p>';document.getElementById('plus').innerText='+'+((parseInt(new_val) - parseInt(fans_count)));}JsBarcode('#val',new_val.toString(),{width:10,height:100,displayValue:false,background:'transparent'});fans_count=new_val;}</script></body></html>'''
            return render_template_string(ret_str)

        @app.route('/gf')
        def get_fans_count():
            try:
                url = f'https://api.bilibili.com/x/relation/stat?vmid={str(self.vmid)}'
                headers = {
                    'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2882.18 Safari/537.36'}
                resp = requests.get(url, headers)
                json_resp = json.loads(resp.text)
                return str(json_resp['data']['follower'])
            except:
                return "0000"

        return app


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


####################################################
# # # load config from file and initialize webserver
configs = ConfigurationHandler('./configurations.json')
configs.load()

fans_counter = FansCounterWebServer(
    configs.get_value('mid', ''),
    configs.get_value('refresh', 1000)
)
fans_counter.run()

####################################################
# callbacks


def button_refreshlist_clicked(props, prop, *args, **kwargs):
    list_bind_browser = obs.obs_properties_get(props, 'list_bind_browser')
    obs.obs_property_list_clear(list_bind_browser)

    sources = obs.obs_enum_sources()
    if sources is not None:
        for source in sources:
            source_id = obs.obs_source_get_unversioned_id(source)
            if source_id.find("browser_source") != -1:
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(
                    list_bind_browser, name, source_id)
        obs.source_list_release(sources)
    return True

####################################################
#  api functions


def script_description():
    return 'B站实时粉丝人数显示小卡片脚本.'


def script_properties():
    props = obs.obs_properties_create()

    textbox_mid = obs.obs_properties_add_text(
        props, 'textbox_mid', '账户id:', obs.OBS_TEXT_DEFAULT)
    obs.obs_property_set_long_description(textbox_mid,
                                          '在此输入账户id, 即电脑端打开个人主页时在地址栏显示的数字.\n' +
                                          '例如https://space.bilibili.com/49983947中, 数字49983947即为账户id.')
    textbox_unamesearch = obs.obs_properties_add_list(
        props, 'textbox_unamesearch', '用户名反查(未开发):', obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    numeric_interval = obs.obs_properties_add_float_slider(
        props, 'numeric_interval', '刷新周期(s):', 0.001, 60.0, 0.001)
    obs.obs_property_set_long_description(numeric_interval,
                                          '在此设置获取粉丝数的间隔时间(单位为秒, 1s = 1000ms).\n' +
                                          '建议设置0.5秒以上以防止访问B站服务器过于频繁导致的封禁.')
    font_fans_count = obs.obs_properties_add_font(
        props, 'font_fans_count', '粉丝数字体(未开发):')
    font_fans_add = obs.obs_properties_add_font(
        props, 'font_fans_add', '新增数字体(未开发):')
    check_negative_add = obs.obs_properties_add_bool(
        props, 'check_negative_add', '显示粉丝数负增长(未开发)')
    list_bind_browser = obs.obs_properties_add_list(
        props, 'list_bind_browser', '控件选择:', obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)

    sources = obs.obs_enum_sources()
    if sources is not None:
        for source in sources:
            source_id = obs.obs_source_get_unversioned_id(source)
            if source_id.find("browser_source") != -1:
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(
                    list_bind_browser, name, source_id)

        obs.source_list_release(sources)

    obs.obs_property_set_enabled(textbox_unamesearch, False)
    obs.obs_property_set_enabled(font_fans_count, False)
    obs.obs_property_set_enabled(font_fans_add, False)
    obs.obs_property_set_enabled(check_negative_add, False)
    button_refreshlist = obs.obs_properties_add_button(
        props, 'button_refreshlist', '刷新控件列表', lambda props, prop: ...)

    obs.obs_property_set_modified_callback(
        button_refreshlist, button_refreshlist_clicked)
    return props


def script_load(settings):
    obs.obs_data_set_string(settings, 'textbox_mid',
                            configs.get_value('mid', ''))
    obs.obs_data_set_double(settings, 'numeric_interval',
                            configs.get_value('refresh', 1000)/1000.0)
    obs.obs_data_set_string(settings, 'list_bind_browser',
                            configs.get_value('control', ''))
    fans_counter.change_vmid_refresh(configs.get_value(
        'textbox_mid', ''), int(configs.get_value('refresh', 1000)))


def script_update(settings):
    ctrl_vals = json.loads(obs.obs_data_get_json(settings))
    fans_counter.change_vmid_refresh(ctrl_vals.get('textbox_mid', ''), int(
        ctrl_vals.get('numeric_interval', 1) * 1000.0))
    if ctrl_vals.get('list_bind_browser') is not None:
        source = obs.obs_get_source_by_name(ctrl_vals.get('list_bind_browser'))
        settings = obs.obs_source_get_settings(source)
        obs.obs_data_set_string(
            settings, 'url', f'http://127.0.0.1:8192?_={time.time()}')
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source)

    configs.set_value('mid', ctrl_vals.get('textbox_mid', ''))
    configs.set_value('refresh', int(
        ctrl_vals.get('numeric_interval', 1) * 1000.0))
    configs.set_value('control', ctrl_vals.get('list_bind_browser', ''))
    configs.save()


def script_unload():
    if fans_counter.ctrl is not None:
        fans_counter.ctrl.stop(0)
        fans_counter.ctrl.close()
        fans_counter.ctrl = None

    if fans_counter.thread is not None:
        fans_counter.thread.join(0)
        fans_counter.thread = None


def script_save(settings):
    script_update(settings)
