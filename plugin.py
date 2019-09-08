# -*- coding: utf-8 -*-
#########################################################
# 고정영역
#########################################################
# python
import os
import sys
import traceback

# third-party
from flask import Blueprint, request, render_template, redirect, jsonify
from flask_login import login_required

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler
from framework.util import Util
            
# 패키지
from logic import Logic
from model import ModelSetting
package_name = __name__.split('.')[0].split('_sjva')[0]
logger = get_logger(package_name)

blueprint = Blueprint(
    package_name, package_name,
    url_prefix='/%s' % package_name,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates')
)


def plugin_load():
    Logic.plugin_load()


def plugin_unload():
    Logic.plugin_unload()


plugin_info = {
    "catogory_name": "tool",
    "version": "0.0.9.1",
    "name": "vnStat",
    "home": "https://github.com/wiserain/vnStat_sjva",
    "more": "https://github.com/wiserain/vnStat_sjva",
    "description": "vnStat 정보를 보여주는 플러그인",
    "developer": "wiserain",
    "zip": "https://github.com/wiserain/vnStat_sjva/archive/master.zip",
    "icon": ""
}
#########################################################


# 메뉴 구성.
menu = {
    'main': [package_name, 'vnStat'],
    'sub': [
        ['setting', '설정'], ['traffic', '트래픽'], ['log', '로그']
    ]
}  


#########################################################
# WEB Menu
#########################################################
@blueprint.route('/')
def home():
    return redirect('/%s/traffic' % package_name)


@blueprint.route('/<sub>')
@login_required
def detail(sub):
    logger.debug('menu %s %s', package_name, sub)
    if sub == 'setting':
        setting_list = db.session.query(ModelSetting).all()
        arg = Util.db_list_to_dict(setting_list)
        arg['scheduler'] = str(scheduler.is_include(package_name))
        arg['is_running'] = str(scheduler.is_running(package_name))
        return render_template('%s_setting.html' % package_name, sub=sub, arg=arg)
    elif sub == 'traffic':
        setting_list = db.session.query(ModelSetting).all()
        arg = Util.db_list_to_dict(setting_list)
        return render_template('%s_traffic.html' % package_name, arg=arg)
    elif sub == 'log':
        return render_template('log.html', package=package_name)
    return render_template('sample.html', title='%s - %s' % (package_name, sub))

#########################################################
# For UI                                                          
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
def ajax(sub):
    logger.debug('AJAX %s %s', package_name, sub)
    # 설정 저장
    if sub == 'setting_save':
        try:
            ret = Logic.setting_save(request)
            return jsonify(ret)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    # 스케쥴링 on / off
    elif sub == 'scheduler':
        try:
            go = request.form['scheduler']
            logger.debug('scheduler :%s', go)
            if go == 'true':
                Logic.scheduler_start()
            else:
                Logic.scheduler_stop()
            return jsonify(go)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return jsonify('fail')
    elif sub == 'install_vnstat':
        try:
            ret = Logic.install_vnstat()
            return jsonify(ret)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    elif sub == 'get_default_interface_id':
        try:
            setting_list = db.session.query(ModelSetting).all()
            arg = Util.db_list_to_dict(setting_list)
            print(arg)
            return jsonify({'default_interface_id': arg['default_interface_id']})
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    elif sub == 'get_vnstat_info':
        try:
            ret = Logic.get_vnstat_info()
            return jsonify(ret)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

#########################################################
# API
#########################################################
@blueprint.route('/api/<sub>', methods=['GET', 'POST'])
def api(sub):
    logger.debug('api %s %s', package_name, sub)
