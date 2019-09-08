# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import traceback
from datetime import datetime, timedelta
import logging
import subprocess
import json

# third-party

# sjva 공용
from framework import db, scheduler, app
from framework.job import Job
from framework.util import Util


# 패키지
from .model import ModelSetting
#########################################################
package_name = __name__.split('.')[0].split('_sjva')[0]
logger = logging.getLogger(package_name)


class Logic(object):
    # 디폴트 세팅값
    db_default = { 
        'auto_start': 'False',
        'interval': '20',
        'default_interface_id': '',
        'default_traffic_view': '2',
        'traffic_unit': '1',
    }

    @staticmethod
    def db_init():
        try:
            for key, value in Logic.db_default.items():
                if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
                    db.session.add(ModelSetting(key, value))
            db.session.commit()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_load():
        try:
            logger.debug('%s plugin_load', package_name)
            # DB 초기화
            Logic.db_init()

            # 편의를 위해 json 파일 생성
            from plugin import plugin_info
            Util.save_from_dict_to_json(plugin_info, os.path.join(os.path.dirname(__file__), 'info.json'))

            # 자동시작 옵션이 있으면 보통 여기서 
            if ModelSetting.query.filter_by(key='auto_start').first().value == 'True':
                Logic.scheduler_start()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_unload():
        try:
            logger.debug('%s plugin_unload', package_name)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def scheduler_start():
        try:
            logger.debug('%s scheduler_start', package_name)
            interval = ModelSetting.query.filter_by(key='interval').first().value
            job = Job(package_name, package_name, interval, Logic.scheduler_function, u"vnStat", False)
            scheduler.add_job_instance(job)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def scheduler_stop():
        try:
            logger.debug('%s scheduler_stop', package_name)
            scheduler.remove_job(package_name)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def setting_save(req):
        try:
            for key, value in req.form.items():
                logger.debug('Key:%s Value:%s', key, value)
                entity = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
                entity.value = value
            db.session.commit()
            return True                  
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def get_setting_value(key):
        try:
            return db.session.query(ModelSetting).filter_by(key=key).first().value
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def scheduler_function():
        try:
            logger.debug('%s scheduler_function', package_name)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    # 기본 구조 End
    ##################################################################

    @staticmethod
    def is_vnstat_installed():
        try:
            return subprocess.check_output("which vnstat", shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
        except:
            return False

    @staticmethod
    def install_vnstat():
        ret = {}
        try:
            if Logic.is_vnstat_installed():
                vnstat_ver = subprocess.check_output("vnstat -v", shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
                ret['ret'] = 'installed'
                ret['log'] = ' '.join(vnstat_ver.split()[:2])
                return ret

            import platform
            os_name, os_dist = platform.system(), platform.dist()[0]
            ret['ret'] = 'Unsupported system and distribution'
            ret['log'] = 'System: %s Distribution: %s' % (os_name, os_dist)
            if os_name == 'Linux':
                if os_dist == 'Ubuntu':
                    ret['ret'] = 'success'
                    ret['command'] = 'apt-get install vnstat -y'
                elif os_dist == '' and app.config['config']['running_type'] == 'docker':
                    ret['ret'] = 'success'
                    ret['command'] = 'apk add --no-cache vnstat'
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['log'] = str(e)
        return ret

    @staticmethod
    def parsing_vnstat_traffic(traffic, data_type):
        labels, rxs, txs, totals = [], [], [], []
        for item in reversed(traffic[data_type]):
            if data_type == 'hours':
                label = "{}시".format(item['id'])
            elif data_type == 'days':
                label = '{}월 {}일'.format(item['date']['month'], item['date']['day'])
            elif data_type == 'months':
                label = '{}년 {}월'.format(item['date']['year'], item['date']['month'])
            elif data_type == 'tops':
                label = '{}-{:02}-{:02}'.format(item['date']['year'], item['date']['month'], item['date']['day'])
            labels.append(label)
            rxs.append(item['rx']*1024)   # 소수점 둘째자리
            txs.append(item['tx']*1024)
            totals.append((item['rx']+item['tx'])*1024)
        if data_type == 'hours':
            nowh = int(datetime.now().strftime('%H')) + 1
            labels = list(reversed(labels[:len(labels) - nowh])) + list(reversed(labels[-nowh:]))
            rxs = list(reversed(rxs[:len(rxs) - nowh])) + list(reversed(rxs[-nowh:]))
            txs = list(reversed(txs[:len(txs) - nowh])) + list(reversed(txs[-nowh:]))
            totals = list(reversed(totals[:len(totals) - nowh])) + list(reversed(totals[-nowh:]))
        return {
            'labels': labels,
            'rxs': rxs,
            'txs': txs,
            'totals': totals,
        }
    
    @staticmethod
    def parsing_vnstat_json(vnstat_json):
        """
        vnStat 1.18에서는 weekly나 begin/end, 5minutes 같은 다양한 통계가 불가능
        현재 버전은 2.4 https://github.com/vergoh/vnstat/blob/master/CHANGES
        기본적으로 json이나 xml로 받으면 KiB = 1024 bytes가 나온다.
        /etc/vnstat.conf의 내용은 콘솔에서 보여주는 것에 관한 것이다.
        """        
        ret = []
        for interface in vnstat_json['interfaces']:
            created = '{}-{:02d}-{:02d}'.format(
                interface['created']['date']['year'],
                interface['created']['date']['month'],
                interface['created']['date']['day'],
            )
            updated = '{}-{:02d}-{:02d} {:02d}:{:02d}'.format(
                interface['updated']['date']['year'],
                interface['updated']['date']['month'],
                interface['updated']['date']['day'],
                interface['updated']['time']['hour'],
                interface['updated']['time']['minutes'],
            )
            traffic = interface['traffic']
            vnstat_interfaces = {
                'id': interface['id'],
                'created': created,
                'updated': updated,
                'hours': Logic.parsing_vnstat_traffic(traffic, 'hours'),
                'days': Logic.parsing_vnstat_traffic(traffic, 'days'),
                'months': Logic.parsing_vnstat_traffic(traffic, 'months'),
                'tops': Logic.parsing_vnstat_traffic(traffic, 'tops'),
            }
            # summary
            labels, rxs, txs, totals = [], [], [], []
            
            labels.append('오늘')
            rxs.append(vnstat_interfaces['days']['rxs'][-1])
            txs.append(vnstat_interfaces['days']['txs'][-1])
            totals.append(vnstat_interfaces['days']['totals'][-1])
            
            labels.append('이번달')
            rxs.append(vnstat_interfaces['months']['rxs'][-1])
            txs.append(vnstat_interfaces['months']['txs'][-1])
            totals.append(vnstat_interfaces['months']['totals'][-1])
            
            labels.append('전체기간')
            rxs.append(traffic['total']['rx']*1024)
            txs.append(traffic['total']['tx']*1024)
            totals.append((traffic['total']['rx']+traffic['total']['tx'])*1024)

            vnstat_interfaces.update({'summary': {
                'labels': labels,
                'rxs': rxs,
                'txs': txs,
                'totals': totals,
            }})

            ret.append(vnstat_interfaces)
            
        logger.debug(ret)
        return ret

    @staticmethod
    def get_vnstat_info():
        try:
            vnstat_stdout = subprocess.check_output("vnstat --json", shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
            vnstat_json = json.loads(vnstat_stdout)
            try:
                vnstat_info = Logic.parsing_vnstat_json(vnstat_json)
                return {'ret': 'success', 'data': vnstat_info}
            except Exception as e:
                logger.info('Exception: %s', e)
                logger.info(traceback.format_exc())
                return {'ret': 'parsing_error', 'log': str(e)}
        except subprocess.CalledProcessError as e:
            # vnStat 바이너리가 없을때
            logger.info('Exception:%s', e)
            logger.info(traceback.format_exc())
            return {'ret': 'no_bin', 'log': e.output.strip()}
        except Exception as e:
            # 그 외의 에러, 대부분 데이터베이스가 없어서 json 값이 들어오지 않는 경우
            logger.info('Exception:%s', e)
            logger.info(traceback.format_exc())
            return {'ret': 'no_json', 'log': vnstat_stdout}
