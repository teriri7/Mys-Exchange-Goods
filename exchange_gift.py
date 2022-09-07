'''
米游社商品兑换
'''
import os
import sys
import threading
import time
import requests
from ping3 import ping

from com_tool import check_plat, check_update, get_time, load_config

MI_URL = 'https://api-takumi.mihoyo.com'
CHECK_URL = 'api-takumi.mihoyo.com'


def get_gift_biz(goods_id: int):
    '''
    获取商品所属分区与类型
    '''
    try:
        gift_detail_url = MI_URL + "/mall/v1/web/goods/detail"
        gift_detail_params = {
            "app_id": 1,
            "point_sn": "myb",
            "goods_id": goods_id,
        }
        gift_detail_req = requests.get(gift_detail_url, params=gift_detail_params)
        if gift_detail_req.status_code != 200:
            return False
        gift_detail = gift_detail_req.json()["data"]
        if gift_detail is None:
            return False
        return gift_detail['game_biz']
    except KeyboardInterrupt:
        print("强制退出")
        sys.exit()
    except Exception as err:
        print(err, err.__traceback__.tb_lineno)
        return False


def get_cookie_str(target):
    '''
    获取cookie字符串中相应的数据
    '''
    try:
        location = mi_cookie.find(target)
        return mi_cookie[mi_cookie.find("=", location) + 1:mi_cookie.find(";", location)]
    except KeyboardInterrupt:
        print("强制退出")
        sys.exit()
    except Exception as err:
        print(err, err.__traceback__.tb_lineno)
        return None


def get_action_ticket():
    '''
    获取查询所需 ticket
    '''
    try:
        stoken = get_cookie_str('stoken')
        uid = get_cookie_str('ltuid')
        action_ticket_url = MI_URL + "/auth/api/getActionTicketBySToken"
        action_ticket_headers = {
            #"User-Agent": "okhttp/4.8.0",
            "Cookie": mi_cookie,
            #"DS": get_ds()
        }
        action_ticket_params = {"action_type": "game_role", "stoken": stoken, "uid": uid}
        action_ticket_req = requests.get(action_ticket_url,
                                         headers=action_ticket_headers,
                                         params=action_ticket_params)
        if action_ticket_req.status_code != 200:
            print("ticket请求失败，请检查cookie")
            return False
        if action_ticket_req.json()['data'] is None:
            print(f"ticket获取失败, 原因为{action_ticket_req.json()['message']}")
            return False
        return action_ticket_req.json()['data']['ticket']
    except KeyboardInterrupt:
        print("强制退出")
        sys.exit()
    except Exception as err:
        print(err, err.__traceback__.tb_lineno)
        return False


def check_game_roles(action_ticket, game_biz, uid):
    '''
    检查是否绑定角色
    '''
    try:
        game_roles_url = MI_URL + "/binding/api/getUserGameRoles"
        game_roles_params = {
            "point_sn": "myb",
            "action_ticket": action_ticket,
            "game_biz": game_biz
        }
        game_roles_headers = {"cookie": mi_cookie}
        game_roles_req = requests.get(game_roles_url,
                                      headers=game_roles_headers,
                                      params=game_roles_params)
        if game_roles_req.status_code != 200:
            print("检查角色请求失败，请检查传入参数")
            return False
        game_roles_list = game_roles_req.json()['data']['list']
        if not game_roles_list:
            print('没有绑定任何角色')
            return False
        for game_roles in game_roles_list:
            if game_roles['game_biz'] == game_biz and game_roles['game_uid'] == str(uid):
                return True
        return False
    except KeyboardInterrupt:
        print("强制退出")
        sys.exit()
    except Exception as err:
        print(err, err.__traceback__.tb_lineno)
        return False


def post_exchange_gift(gift_id, biz):
    '''
    兑换礼物
    '''
    try:
        exchange_gift_url = MI_URL + "/mall/v1/web/goods/exchange"
        exchange_gift_json = {
            "app_id": 1,
            "point_sn": "myb",
            "goods_id": str(gift_id),
            "exchange_num": 1,
            "address_id": ini_config.getint('user_info', 'address_id'),
            "uid": ini_config.getint('user_info', 'uid'),
            "region": "cn_gf01",
            "game_biz": biz
        }
        exchange_gift_headers = {
            "Cookie": mi_cookie,
        }
        for _ in range(ini_config.getint('exchange_info', 'retry')):
            exchange_gift_req = requests.post(exchange_gift_url,
                                              headers=exchange_gift_headers,
                                              json=exchange_gift_json)
            if exchange_gift_req.status_code != 429:
                break
            time.sleep(1)
        if exchange_gift_req.status_code != 200:
            print("兑换请求失败")
            return False
        exchange_gift_req_json = exchange_gift_req.json()
        if exchange_gift_req_json['data'] is None:
            print(f"商品{str(gift_id)}兑换失败, 原因是{exchange_gift_req_json['message']}")
            return False
        print(f"商品{str(gift_id)}兑换成功, 订单号{exchange_gift_req_json['data']['order_sn']}")
        print("请手动前往米游社APP查看订单状态")
    except KeyboardInterrupt:
        print("强制退出")
        sys.exit()
    except Exception as err:
        print(err, err.__traceback__.tb_lineno)
        return False


def init_task():
    '''
    初始化任务
    '''
    try:
        gift_list = ini_config.get('exchange_info', 'good_id').split(',')
        task_thread = ini_config.getint('exchange_info', 'thread')
        task_list = []
        for good_id in gift_list:
            game_biz = get_gift_biz(good_id)
            if not game_biz:
                print("获取game_biz失败")
                continue
            action_ticket = get_action_ticket()
            if not action_ticket:
                print("获取ticket失败")
                continue
            if not check_game_roles(action_ticket, game_biz, ini_config.get('user_info', 'uid')):
                print("查询绑定角色失败")
                continue
            for _ in range(task_thread):
                task_list.append(
                    threading.Thread(target=post_exchange_gift, args=(good_id, game_biz)))
        return task_list
    except KeyboardInterrupt:
        print("强制退出")
        sys.exit()
    except Exception as err:
        print(err, err.__traceback__.tb_lineno)
        return False


def run_task(task_list):
    '''
    运行任务
    '''
    try:
        start_timestamp = ini_config.get('exchange_info', 'time')
        start_time = time.mktime(time.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S"))
        ntp_enable = ini_config.getboolean('ntp', 'enable')
        ntp_server = ini_config.get('ntp', 'ntp_server')
        temp_time = 0
        check_network_enable = ini_config.getboolean('check_network', 'enable')
        check_network_interval_time = ini_config.getint('check_network', 'interval_time')
        check_network_stop_time = ini_config.getint('check_network', 'stop_time')
        network_delay = 0
        check_last_time = 0
        truth_start_time = start_time
        while True:
            now_time = get_time(ntp_enable, ntp_server)
            if now_time >= truth_start_time:
                os.system(CLEAR_TYPE)
                print("开始执行兑换任务")
                for task in task_list:
                    task.start()
                for task in task_list:
                    task.join()
                print("兑换任务执行完毕")
                sys.exit()
            elif now_time != temp_time:
                os.system(CLEAR_TYPE)
                if not check_network_enable:
                    print("网络检查未开启")
                elif truth_start_time - now_time <= check_network_stop_time:
                    print("网络检查已停止")
                elif now_time - check_last_time >= check_network_interval_time:
                    network_delay = ping(CHECK_URL, unit='ms')
                    if not network_delay or network_delay is None:
                        print("本次网络检查异常")
                    else:
                        check_last_time = now_time
                if network_delay and network_delay is not None:
                    print(f"网络延迟为 {round(network_delay, 2)} ms")
                    if network_delay >= 1000:
                        print("网络延迟过高, 请检查网络")
                        delay_time = int(network_delay / 1000)
                        print(f"程序将任务开始时间提前 {delay_time} 秒")
                        truth_start_time = start_time - delay_time
                    else:
                        truth_start_time = start_time
                print(f"当前时间 {time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(now_time))}")
                time_t = truth_start_time - now_time
                print(
                    f"距离兑换开始还有 {int(time_t / 3600)} 小时 {int(time_t % 3600 / 60)} 分钟 {int(time_t % 60)} 秒"
                )
                temp_time = now_time
    except KeyboardInterrupt:
        print("强制退出")
        sys.exit()
    except Exception as err:
        print(err, err.__traceback__.tb_lineno)
        return False


def start():
    '''
    开始任务
    '''
    try:
        if not mi_cookie:
            print("请填写cookie")
            sys.exit()
        task_list = init_task()
        if not task_list:
            print("没有任务, 程序退出")
            sys.exit()
        run_task(task_list)
        print("程序运行完毕, 即将退出")
        return True
    except KeyboardInterrupt:
        print("强制退出")
        sys.exit()
    except Exception as err:
        print(err, err.__traceback__.tb_lineno)
        return False


if __name__ == '__main__':
    try:
        CLEAR_TYPE = check_plat()
        ini_config = load_config()
        check_update(ini_config)
        mi_cookie = ini_config.get('user_info', 'cookie')
        start()
    except KeyboardInterrupt:
        print("强制退出")
        sys.exit()
    except Exception as main_err:
        print(main_err)
        input("按回车键继续")
        sys.exit()
