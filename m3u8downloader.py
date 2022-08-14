import os,shutil,time,requests
from Crypto.Cipher import AES
from fake_useragent import UserAgent
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import argparse

video_download_path = './m3u8Download'
save_mp4_path = './m3u8Download/testVideo'
save_temporary_ts_path = './m3u8Download/temporary_ts'
if not os.path.exists(video_download_path):
    os.makedirs(save_mp4_path)
    os.mkdir(save_temporary_ts_path)

def send_request(url):
    headers = {
        'User-Agent': UserAgent().Chrome,
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    try:
        response = requests.get(url=url,headers=headers)
        if response.status_code == 200:
            return response
        else:
            print(response,'responding error！')
            exit()
    except Exception as e:
        print('m3u8 link request error！！！')
        print(e)

def get_m3u8_response_data():
    m3u8_data = send_request(m3u8_url).text
    return m3u8_data

def parse_m3u8_data():
    m3u8_data = get_m3u8_response_data()
    each_line_list = m3u8_data.strip('\n').split('\n') 
    all_ts_list = []
    video_time = []
    AES_decode_data = None
    if '#EXTM3U' in each_line_list:
        for i in each_line_list:
            if '#EXT-X-KEY' in i: 
                encryption_method,key_url, iv = parse_AES_encryption(i)
                print('encryption method ：',encryption_method)
                key_url = urljoin(m3u8_url,key_url)
                AES_decode_data = AES_decode(key_url,iv)
            if not i.startswith('#') or i.startswith('http') or i.endswith('.ts'):
                each_ts_url = urljoin(m3u8_url, i)
                all_ts_list.append(each_ts_url)
            if i.startswith('#EXTINF'):
                time_ = float(i.strip().split(':')[1][:-1])
                video_time.append(time_)
    print('video length ：{:.2f} mins'.format(sum(video_time) / 60))
    return all_ts_list,AES_decode_data

def get_each_ts_response_data():
    print('start download video……')
    all_ts_list,AES_decode_data = parse_m3u8_data()

    with ThreadPoolExecutor(max_workers=20) as executor:
        for i,ts_url in enumerate(all_ts_list):
            executor.submit(download_ts, i,ts_url,AES_decode_data)
    print('finish download video！')
    return True

def download_ts(i,ts_url,AES_decode_data):
    if AES_decode_data:
        ts_data = send_request(ts_url).content
        ts_data = AES_decode_data.decrypt(ts_data)
    else:
        ts_data = send_request(ts_url).content
    if ts_url.endswith('.png'):
        ts_data=ts_data[8:]
    with open(f'{save_temporary_ts_path}/{i}.ts',mode='wb+') as f:
        f.write(ts_data)
        print(f'{i}.ts finish download！')

def parse_AES_encryption(key_content):
    if 'IV' or 'iv' in key_content:
        parse_result = key_content.split('=')
        encryption_method = parse_result[1].split(',')[0]
        key_url = parse_result[2].split('"')[1]
        iv = parse_result[3]
        iv = iv[2:18].encode()
    else:
        parse_result = key_content.split('=')
        encryption_method = parse_result[1].split(',')[0]
        key_url = parse_result[2].split('"')[1]
        iv = None
    return encryption_method, key_url, iv

def AES_decode(key_url,iv):
    key = send_request(key_url).content
    if iv:
        AES_decode_data = AES.new(key, AES.MODE_CBC, iv)
    else:
        AES_decode_data = AES.new(key, AES.MODE_CBC, b'')
    return AES_decode_data

def merge_all_ts_file():
    print('start merge videos ……')
    ts_file_list = os.listdir(save_temporary_ts_path)
    ts_file_list.sort(key=lambda x: int(x[:-3]))
    with open(save_mp4_path+'/video.mp4', 'wb+') as fw:
        for i in range(len(ts_file_list)):
            fr = open(os.path.join(save_temporary_ts_path, ts_file_list[i]), 'rb')
            fw.write(fr.read())
            fr.close()
    shutil.rmtree(save_temporary_ts_path) 
    print('finish merge videos！')

def begin_processing():
    if get_each_ts_response_data():
        merge_all_ts_file()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", default="",help="m3u8 file uri",required="true")
    start_time = time.time()
    args = parser.parse_args()
    m3u8_url = args.input
    begin_processing()
    end_time = time.time()
    print(f'cost time：{end_time-start_time} seconds')

