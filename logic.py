# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
from datetime import datetime
import subprocess
import json

# third-party

# sjva 공용
from framework import db, scheduler, app
from framework.job import Job
from framework.util import Util


# 패키지
from .plugin import package_name, logger
from .model import ModelSetting


class Logic(object):
    # 디폴트 세팅값
    db_default = {
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

            # 기타 자동시작 옵션
            is_installed = Logic.is_installed()
            if not is_installed or not any(x in is_installed for x in plugin_info['supported_vnstat_version']):
                Logic.install()
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
    # 기본 구조 End
    ##################################################################

    @staticmethod
    def is_installed():
        try:
            verstr = subprocess.check_output("vnstat -v", shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
            vernum = verstr.split()[1]
            from plugin import plugin_info
            if not any(vernum in x for x in plugin_info['supported_vnstat_version']):
                vernum += ' - 지원하지 않는 버전'
            return vernum
        except Exception:
            return False

    @staticmethod
    def install():
        try:
            import platform, threading
            if platform.system() == 'Linux' and app.config['config']['running_type'] == 'docker':
                install_sh = os.path.join(os.path.dirname(__file__), 'install.sh')
                def func():
                    import system
                    commands = [
                        ['msg', u'잠시만 기다려주세요.'],
                        ['chmod', '+x', install_sh],
                        [install_sh, '1.18'],
                        ['msg', u'설치가 완료되었습니다.']
                    ]
                    system.SystemLogicCommand.start('설치', commands)
                t = threading.Thread(target=func, args=())
                t.setDaemon(True)
                t.start()
                # finally check vnStat imported
                vernum = Logic.is_installed()
                if vernum:
                    return {'success': True, 'log': 'vnStat v{}'.format(vernum), 'version': vernum}
                else:
                    return {'success': False, 'log': '설치 후 알 수 없는 에러. 개발자에게 보고바람'}
            else:
                return {'succes': False, 'log': '지원하지 않는 시스템입니다.'}
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return {'success': False, 'log': str(e)}

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
