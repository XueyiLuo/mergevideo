#!/usr/bin/python3

import os
import shutil
import subprocess

HOMEPATH = os.environ['HOME']
VIDEOPATH = HOMEPATH+'/'+'video/'

class M3U8OBJ():
    def __init__(self, path) -> None:
        self.tsDirs = []
        self.m3u8files = []
        self.orginpath = path
        self.basepath = ''
        self.basename = ''
        self.matchdirname = ''
        self.is_m3u = False
        self.is_encryption = False

class M3U8FILES():
    def __init__(self) -> None:
        self.m3uobjs = []
        self.tsDirs = []
        self.m3u8files = []

    def ParsingDirectory(self, path):
        if len(path) == 0:
            print("path is empty.")
            return 

        #获取目录内容
        video_files = os.listdir(path)   
        
        for file in video_files:
            if os.path.isfile(VIDEOPATH+file) and '.m3u8' in file and '.swp' not in file: #文件
                if file not in self.tsDirs:
                    self.m3u8files.append(file)
            elif os.path.isdir(VIDEOPATH+file):  #文件夹
                self.tsDirs.append(file)
        
        # # 解析文件夹
        # for td in self.tsDirs:
        #     if os.path.isdir(VIDEOPATH+td):
        #         files = os.listdir(VIDEOPATH+td)
        #     for file in files:
        #         with open(VIDEOPATH+td+'/'+file,"w+") as f:
        #             first_line = f.readline()
        #         if '#EXTM3U' in first_line: # 是一个m3u文件夹
        # 解析 .m3u8 文件  为每一个m3u8 创建对象
        for mf in self.m3u8files:
            self.m3uobjs.append(M3U8OBJ(VIDEOPATH+mf))
        for mo in self.m3uobjs:
            _is_filepath = False
            mo.basepath = os.path.dirname(mo.orginpath)
            # print(os.path.basename(mo.orginpath))
            # print(os.path.dirname(mo.orginpath))
            if os.path.isfile(mo.orginpath):
                with open(mo.orginpath,"r") as f:
                    for line in f:
                        if 'EXTM3U' not in line:
                            print("Not a valid M3U8 file.")
                            return 
                        else:
                            break
                    for line in f:
                        if '#EXTINF' in line and _is_filepath == False:
                            _is_filepath = True
                            continue
                        if _is_filepath == True: 
                            mo.basename = line.split('/')[-2]
                            _is_filepath = False
                            f.close()
                            break

        # 查找是否存在对应目录
        for mo in self.m3uobjs:
            if os.path.isdir(os.path.join(mo.basepath, mo.basename)):
                mo.is_m3u = True
                mo.matchdirname = os.path.join(mo.basepath, mo.basename)
            for md in os.listdir(mo.matchdirname):
                if '.key' in md:
                    mo.is_encryption = True

        # 查询所有碎片文件
        for mo in self.m3uobjs:
            _is_filepath = False
            if not mo.is_m3u:
                continue
            with open(mo.orginpath,"r") as f:
                for line in f:
                    if '#EXTINF' in line and _is_filepath == False:
                            _is_filepath = True
                            continue
                    if _is_filepath == True: 
                        mo.m3u8files.append(line.split('/')[-1].strip())
                        _is_filepath = False
    
    def StartMerge(self):
        count = 0
        success_count = 0
        failes_count = 0
        if len(self.m3uobjs) == 0:
            print("there is no m3u objs found.")
            return
        for mo in self.m3uobjs:
            count = count + 1
            print("Merging < %d >, m3u8 file: < %s > ..."%(count, mo.orginpath))
            if not mo.is_m3u:
                print("Merging error, file < %s > is not m3u8."%(mo.orginpath))
            else:
                try:
                    # 移动至对应文件夹并统一命名
                    source = mo.orginpath
                    destination = os.path.join(mo.matchdirname, 'index.m3u8')
                    mo.newm3u8 = destination
                    shutil.copy(source,destination)
                except Exception as e:
                    print(e)

            # 修改index.m3u8文件
            self.AlterM3U8Files(mo.matchdirname)

            # 生成file_list
            with open(os.path.join(mo.matchdirname, 'file_list.txt') ,"w+") as f:
                for file in mo.m3u8files:
                    f.write("file '{}'\n".format(file))
            print("Create file_list success.")

            # FFmpeg 库进行合并
            # 无加密：ffmpeg -f concat -i file_list.txt -c copy *.mp4
            # 有加密：ffmpeg -allowed_extensions ALL -i index.m3u8 -c copy *.mp4
            if mo.is_encryption:
                ret = subprocess.call(["ffmpeg","-allowed_extensions","ALL","-i",mo.newm3u8,"-c","copy",os.path.join(mo.basepath, 'mergevideo', mo.basename+'.mp4')])
            else:
                ret = subprocess.call(["ffmpeg","-f","concat","-i",os.path.join(mo.matchdirname, 'file_list.txt'),"-c","copy",os.path.join(mo.basepath, 'mergevideo', mo.basename+'.mp4')])
            if ret == 0:
                success_count += 1
            else:
                failes_count  += 1
            print("Merged < %d >, files: < %s > ..."%(count, mo.orginpath))
        print("Merged finished, total num: %d, Success num :%d, Failed num: %d ."%(count, success_count, failes_count))
        
    def AlterM3U8Files(self,Alterpath):
        m3u8file = os.path.join(Alterpath,'index.m3u8')
        if not os.path.exists(m3u8file):
            return
        key_file = ''
        new_line = ''
        file_date = ''
        uri_line = []
        _is_EXTINF = False
        try:
            with open(m3u8file, "r") as f:
                for line in f:  # 遍历每一行
                    if 'URI="' in line:  # key: URI 
                        uri_line = line.split(',')
                        key_file = line.split('/')[-1]
                        for ul in uri_line:
                            if 'URI="' in ul:
                                if not os.path.join(Alterpath,key_file):
                                    print("key file not exist:%s .",os.path.join(Alterpath,key_file))
                                    return
                                uri_line[uri_line.index(ul)] = 'URI="'+os.path.join(Alterpath,key_file)
                        line = ','.join(uri_line)
                    elif 'EXTINF:' in line:   # key: EXTINF
                        _is_EXTINF = True
                    if _is_EXTINF:
                        if '/' in line:
                            line = os.path.join(Alterpath, line.split('/')[-1]) 
                            _is_EXTINF = False
                    file_date += line
            with open(m3u8file, "w") as f:
                f.write(file_date)
            print("Alter %s success.", m3u8file)
        except Exception as e:
            print(e)
                    

if __name__ == "__main__":
    # video目录存在
    if not os.path.exists(VIDEOPATH):
        print("create dir '%s', dir is empty.",VIDEOPATH)
        try:
            os.makedirs(VIDEOPATH)
        except Exception as e:
            print(e)
    
    m3u8 = M3U8FILES()
    m3u8.ParsingDirectory(VIDEOPATH)
    m3u8.StartMerge()
