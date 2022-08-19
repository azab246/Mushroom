# main.py
#
# Copyright 2022 Abdalrahman Azab
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import GObject, Gtk, Adw, Pango, Gdk, Gio, GLib
from pytube import YouTube, Playlist
from re import sub, search, findall
from sqlite3 import connect
from threading import Thread
from time import sleep, time_ns
from datetime import datetime as d
from html import escape
from urllib import request as DRequest
import os
import subprocess
from tarfile import open as openTAR
from shutil import rmtree, move

global APPID
APPID = 'com.github.azab246.mushroom'


@Gtk.Template(resource_path='/com/github/azab246/mushroom/gtk/window.ui')
class MushroomWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'MushroomWindow'


    MainBuffer = Gtk.Template.Child()
    MainEntry = Gtk.Template.Child()
    ListSuggestionRevealer = Gtk.Template.Child()
    SubmitButton = Gtk.Template.Child()
    H_D_Revealer = Gtk.Template.Child()
    ######################################################
    LoadingPage = Gtk.Template.Child()
    ListPage = Gtk.Template.Child()
    MainPage = Gtk.Template.Child()
    VidPage = Gtk.Template.Child()
    DonePage = Gtk.Template.Child()
    FailPage = Gtk.Template.Child()
    ########################################################
    H_D_Button = Gtk.Template.Child()
    Playlist_Content_Group = Gtk.Template.Child()
    MainLeaflet = Gtk.Template.Child()
    ListNameLabel = Gtk.Template.Child()
    VidDetails = Gtk.Template.Child()
    VidTypeBox = Gtk.Template.Child()
    VidResBox = Gtk.Template.Child()
    VidResLabel = Gtk.Template.Child()
    ListTypeBox = Gtk.Template.Child()
    ListResBox = Gtk.Template.Child()
    ListResLabel = Gtk.Template.Child()
    VidSizeLabel = Gtk.Template.Child()
    SuggestionCheck = Gtk.Template.Child()
    Error_Label = Gtk.Template.Child()
    LoadingProgressBar = Gtk.Template.Child()
    MainToastOverlay = Gtk.Template.Child()
    TaskManagerPage = Gtk.Template.Child()
    GlobalRevealer = Gtk.Template.Child()
    Fail_Button = Gtk.Template.Child()
    ListGlobalSwitch = Gtk.Template.Child()
    H_D_Leaflet = Gtk.Template.Child()
    DownloadsPage = Gtk.Template.Child()
    HistoryPage = Gtk.Template.Child()
    History_List = Gtk.Template.Child()
    Downloads_List = Gtk.Template.Child()
    Nothing_H_Revealer = Gtk.Template.Child()
    Nothing_D_Revealer = Gtk.Template.Child()
    ClearHistory_Revealer = Gtk.Template.Child()
    ClearHistory_Button = Gtk.Template.Child()
    Download_Rows = {}
    History_Rows = {}

    VidRequest = 0
    ListRequest = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        global DefaultLocPATH
        global DefaultVContainer
        global DefaultAContainer
        global VCOPT
        global ACOPT
        global ConfigFileDir
        global cache_dir
        global data_dir
        global DownloadCacheDir
        global ffmpeg
        global ffmpegexec
        VCOPT = {'mp4' : 0, 'mkv' : 1, 'webm' : 2, 'mov' : 3, 'flv' : 4}
        ACOPT = {'mp3' : 0, 'aac' : 1, 'ogg' : 2, 'wav' : 3, 'flac' : 4}
        self.isactivetoast = False
        cache_dir = GLib.get_user_cache_dir()
        data_dir = GLib.get_user_data_dir()
        ConfigFileDir = GLib.get_user_cache_dir() + "/tmp/config"
        ffmpeg = f'{data_dir}/ffmpeg'
        ffmpegexec = ffmpeg + " -hide_banner -loglevel error"
        DownloadCacheDir = cache_dir + '/DownloadsCache/'
        # Database + DLoc File
        conn = connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
        db = conn.cursor()
        db.execute('''
          CREATE TABLE IF NOT EXISTS Downloads
          ([url] TEXT, [res] TEXT, [type] TEXT, [location] TEXT, [added_on] TEXT, [size] TEXT, [name] TEXT, [ext] TEXT, [id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, [VF] BIGINT DEFAULT -1, [AF] BIGINT DEFAULT -1)
          ''')
        db.execute('''
          CREATE TABLE IF NOT EXISTS History
          ([res] TEXT, [type] TEXT, [location] TEXT, [Finished_on] TEXT, [name] TEXT, [id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, [size] TEXT, [ext] TEXT, [url] TEXT, [status] TEXT)
          ''')
        conn.commit()
        conn.close()
        try:
            with open(ConfigFileDir, 'r') as f:
                conf = f.read().splitlines()
                DefaultLocPATH = conf[0]
                DefaultVContainer = conf[1]
                DefaultAContainer = conf[2]
            f.close
        except FileNotFoundError:
            with open(ConfigFileDir, 'w') as f:
                f.write(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)+ '/\n' + list(VCOPT.keys())[0] + '\n' + list(ACOPT.keys())[0] +'\n')
                DefaultLocPATH = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) + '/'
                DefaultVContainer = list(VCOPT.keys())[0]
                DefaultAContainer = list(ACOPT.keys())[0]
                f.close()
        self.MainBuffer.connect("inserted_text", self.islistq, self, True)
        self.MainBuffer.connect("deleted_text", self.islistq, self, True)
        Thread(target = self.AppData_Initialization, daemon = True).start()
        Thread(target = self.UpdateDownloads, daemon = True).start()
        Thread(target = self.UpdateHistory, daemon = True).start()
        
        print("All New Downloads Will Be Exported At : " + DefaultLocPATH)
        print("New Video Files Will Be Exported As : " + DefaultVContainer)
        print("New Audio Files Will Be Exported As : " + DefaultAContainer)
        


    def AppData_Initialization(self, *args):
        # Download cache Folder on /chache
        if not os.path.isdir(cache_dir + '/DownloadsCache'):
            os.mkdir(cache_dir + '/DownloadsCache')

        # FFMPEG arch check and Download on /data
        if not os.path.isfile(ffmpeg):
            NoneToast = Adw.Toast.new("Downloading ffmpeg ~41MB, You Will Be Able To Use The App oOnce We Finish This")
            self.MainEntry.set_sensitive(False)
            NoneToast.set_timeout(5)
            self.MainToastOverlay.add_toast(NoneToast)
            print("Cant Find ffmpeg, Trying To Download it from https://johnvansickle.com/ffmpeg/builds/")
            co = subprocess.check_output('uname -m', shell=True).decode('utf-8')
            if "x86_64" in co :
                print('x86_64 arch found')
                URL = "https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz"
            elif 'i686' in co :
                print('i686 arch found')
                URL = "https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-i686-static.tar.xz"
            elif 'aarch64' in co :
                print('aarch64 arch found')
                URL = "https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-arm64-static.tar.xz"
            else:
                print('Unsupported arch')
                self.Fail_Button.set_visible(False)
                self.Fail_Button.set_sensitive(False)
                self.Fail("Sorry, Your Device is not Supported for ffmpeg, only x86_64, i686, aarch64 are supported")
                print("Your CPU arch is not Supported for ffmpeg, only x86_64, i686, aarch64 are supported")
                return
            print("Downloading ffmpeg ~41MB, This Should be Done At The First Time of Running The App")
            DRequest.urlretrieve(URL, f"{data_dir}/ffmpeg.download")
            os.rename(f"{data_dir}/ffmpeg.download", f"{data_dir}/ffmpeg.tar.xz")  
            downloaded = openTAR(f"{data_dir}/ffmpeg.tar.xz")
            downloaded.extractall(f"{data_dir}/ffmpegdir")
            co = subprocess.check_output(f'ls {data_dir}/ffmpegdir/', shell=True).decode('utf-8')
            os.remove(f"{data_dir}/ffmpeg.tar.xz")
            os.rename(f"{data_dir}/ffmpegdir/{co[0:-1]}/ffmpeg", f'{data_dir}/ffmpeg')
            rmtree(f"{data_dir}/ffmpegdir")
            NoneToast = Adw.Toast.new("ffmpeg Downloaded Successfully!")
            self.MainEntry.set_sensitive(True)
            NoneToast.set_timeout(5)
            self.MainToastOverlay.add_toast(NoneToast)
        return


    def time_format(self, sec):
        if sec >= 60 and sec < 3600:
            result = f"{float(sec / 60):.2f}" + " min"
        elif sec >= 3600:
            result = f"{float(sec / 60 / 60):.2f}" + " hrs"
        else:
            result = f"{int(sec)}" + " sec"
        return result



    def size_format(self, size):
            tags = ["bytes", "Kb", "Mb", "Gb", "Tb"]
            if bool(search('[a-zA-Z]', str(size))):
                return size
            i = 0
            double_bytes = size
            while (i < len(tags) and  size >= 1024):
                    double_bytes = size / 1024.0
                    i = i + 1
                    size = size / 1024
            return str(round(double_bytes, 2)) + " " + tags[i]



    def AddToTasksDB(self, url, res, dtype, size, name):
        if dtype == 'Video':
            Ext = DefaultVContainer
        else:
            Ext = DefaultAContainer
        #print(DefaultLocPATH)
        fsize = self.size_format(size)
        dt = d.now().strftime("%d/%m/%Y %H:%M")
        conn = connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
        self.db = conn.cursor()
        self.db.execute('''CREATE TABLE IF NOT EXISTS Downloads ([url] TEXT, [res] TEXT, [type] TEXT, [location] TEXT, [added_on] TEXT, [size] TEXT, [name] TEXT, [ext] TEXT, [id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, [VF] BIGINT DEFAULT -1, [AF] BIGINT DEFAULT -1)''')
        self.db.execute('''INSERT INTO Downloads (url, res, type, location, added_on, size, name, ext) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (url, str(res), dtype, DefaultLocPATH, dt, fsize, name, Ext))
        conn.commit()
        conn.close()


    def AddToHistoryDB(self, UID, status):
        dt = d.now().strftime("%d/%m/%Y %H:%M")
        conn = connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
        db = conn.cursor()
        x = list(db.execute(f'''SELECT * FROM Downloads WHERE id = {UID}'''))
        x = x[0]
        conn.commit()
        db.execute('''
          CREATE TABLE IF NOT EXISTS History
          ([res] TEXT, [type] TEXT, [location] TEXT, [Finished_on] TEXT, [name] TEXT, [id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, [size] TEXT, [ext] TEXT, [url] TEXT, [status] TEXT)
          ''')
        db.execute('''
          INSERT INTO History 
          (res, type, location, Finished_on, name, size, ext, url, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
          ''', (x[1], x[2], x[3], dt, x[6], x[5], x[7], x[0], status))
        conn.commit()
        db.execute(f'''DELETE FROM Downloads WHERE id = {UID}''')
        conn.commit()
        conn.close()


    def UpdateDownloads(self, *args):
        if os.path.isfile(ffmpeg):
            conn = connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
            db = conn.cursor()
            queue = db.execute("SELECT * FROM Downloads")
            for video in queue:
                if str(video[8]) not in list(self.Download_Rows.keys()):
                    print("Adding To Downloads List : " + video[6] + f"  ( {video[2]} )")
                    self.Download_Rows[str(video[8])] = DownloadsRow(video[0], video[1], video[2], video[3], video[4], video[5], video[6], video[7], video[8], video[9], video[10])
                    self.Downloads_List.prepend(self.Download_Rows[str(video[8])])
                    self.TaskManagerPage.set_needs_attention(True)
            if len(list(self.Download_Rows.keys())) == 0:
                for file in os.scandir(cache_dir + '/DownloadsCache'):
                    os.remove(file.path)
                self.Nothing_D_Revealer.set_reveal_child(True)
                self.TaskManagerPage.set_needs_attention(False)
            else:
                self.Nothing_D_Revealer.set_reveal_child(False)
            conn.close()

    
    def UpdateHistory(self, *args):
        if os.path.isfile(ffmpeg):
            conn = connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
            db = conn.cursor()
            queue = db.execute("SELECT * FROM History")
            for video in queue:
                if video[5] not in list(self.History_Rows.keys()):
                    print("Adding To History List : " + video[4] + f"  ( {video[1]} )")
                    self.History_Rows[video[5]] = HistoryRow(video[5], video[0], video[1], video[2], video[3], video[4], video[6], video[7], video[8], video[9])
                    self.History_List.prepend(self.History_Rows[video[5]])
                #print(video[5])
            if len(list(self.History_Rows.keys())) == 0:
                self.ClearHistory_Button.set_sensitive(False)
                self.Nothing_H_Revealer.set_reveal_child(True)
            else:
                self.ClearHistory_Button.set_sensitive(True)
                self.Nothing_H_Revealer.set_reveal_child(False)
        return


    def Video_Data(self, *args):
        if self.connect_func() == False:
                return
        try:
            print('Starting...')
            self.VidRequest = 1
            self.VidVidRes = Gtk.ListStore(str)
            self.VidAuidRes = Gtk.ListStore(str)
            self.VidTypeList = Gtk.ListStore(str)
            # setting lables
            self.link = self.MainBuffer.get_text()
            self.vid = YouTube(self.link)
            self.VidDetails.set_title(escape(self.vid.title))
            self.VidName = self.vid.title
            self.VidDetails.set_description(f"Channel: {escape(self.vid.author)}  Length: " + f"{self.time_format(self.vid.length)}" + "   Views: " + f"{self.vid.views:,}")
            # setting combo boxes data
            self.SizesA = []
            self.SizesV = []
            self.ResV = []
            self.ResA = []
            print('Getting Data...')
            for stream in self.vid.streams.filter(progressive = False, only_video = True, type = "video", file_extension='mp4'):
                if f"{stream.resolution}" not in self.ResV:
                    self.VidVidRes.append([f"{stream.resolution}"])
                    self.ResV.append(f"{stream.resolution}")
                    self.SizesV.append(stream.filesize + self.vid.streams.filter(progressive = False, only_audio = True, file_extension='webm').last().filesize)
                    #print(stream.resolution)
            for stream in self.vid.streams.filter(type = "audio", file_extension='webm'):
                #print(stream.bitrate)
                if f"{stream.abr}" not in self.ResA:
                    self.VidAuidRes.append([f"{stream.abr}"])
                    self.ResA.append(f"{stream.abr}")
                    self.SizesA.append(stream.filesize)
                    #print(stream.abr)
            self.VidTypeList.append(['Video'])
            self.VidTypeList.append(['Audio'])
            print('Setting Up UI...')
            # cell R
            # type
            self.VidTypeBox.set_model(self.VidTypeList)
            renderer_text = Gtk.CellRendererText.new()
            self.VidTypeBox.pack_start(renderer_text, True)
            self.VidTypeBox.add_attribute(renderer_text, "text", 0)
            self.VidTypeBox.set_active(0)
            # res
            self.VidResBox.set_model(self.VidVidRes)
            renderer_textv = Gtk.CellRendererText.new()
            self.VidResBox.pack_start(renderer_textv, True)
            self.VidResBox.add_attribute(renderer_textv, "text", 0)
            self.VidResBox.set_active(0)
            self.size_label_handler()
            # finishing loading process
            self.loading = 0
            self.VidURL = self.link
            print("Successfully Loaded The Video Data")
            return
        except Exception as err:
            if err:
                self.loading = 0
                self.Fail(err)
                print("Failed To Get Video Data")
                return



    def Playlist_Data(self, *args):
        global rows
        if self.connect_func() == False:
            return
        try:
            print("Starting...")
            self.ListRequest = 1
            #func
            self.ListVidRes = Gtk.ListStore(str)
            self.ListAuidRes = Gtk.ListStore(str)
            self.ListTypeList = Gtk.ListStore(str)
            self.link = self.MainBuffer.get_text()
            self.plist = Playlist(self.link)
            videos = self.plist.videos
            self.l = len(videos)
            rows = [0]*self.l
            self.LResV = []
            self.LResA = []
            self.ListResV = [0 for j in range(self.l)]
            self.ListResA = [0 for j in range(self.l)]
            if self.l == 0:
                self.loading = 0
                self.Fail('Empty List') 
                return
            print("List Initialization Is Done, Downloading Data...")
            print("----------------------------------")
            i = 0
            for video in videos:
                vl = {}
                al = {}
                print(f'Video {i}')
                for stream in video.streams.filter(progressive = False, only_video = True, type = "video", file_extension='mp4'):
                    if stream.resolution not in list(vl.keys()):
                        vl[stream.resolution] = 0
                self.ListResV[i] = vl
                print(f"Avilable Video Resolutions: {list(self.ListResV[i].keys())}")
                for stream in video.streams.filter(type = "audio", file_extension='webm'):
                    if stream.abr not in list(al.keys()):
                        al[stream.abr] = 0
                self.ListResA[i] = al
                print(f"Avilable Audio Bitrates: {list(self.ListResA[i].keys())}")
                print("----------------------------------")
                rows[i] = ListRow(self.plist.video_urls[i] , video.title, video.author, self.time_format(video.length),
                                 video.views, self.Playlist_Content_Group, self.ListResV[i], self.ListResA[i])
                i += 1
            for i in range(len(list(self.ListResV[0].keys()))):
                x = 0
                for y in range(self.l):
                    if list(self.ListResV[0].keys())[i] in list(self.ListResV[y].keys()):
                        x += 1
                    else:
                        break
                if x == self.l:
                    self.LResV.append(list(self.ListResV[0].keys())[i])
                    self.ListVidRes.append([f"{list(self.ListResV[0].keys())[i]}"])
            print(f'Common Video Resolutions (Being Used As A Global Options): {self.LResV}')
            for i in range(len(list(self.ListResA[0].keys()))):
                x = 0
                for y in range(self.l):
                    if list(self.ListResA[0].keys())[i] in list(self.ListResA[y].keys()):
                        x += 1
                    else:
                        break
                if x == self.l:
                    self.LResA.append(list(self.ListResA[0].keys())[i])
                    self.ListAuidRes.append([f"{list(self.ListResA[0].keys())[i]}"])
            print(f'Common Audio Bitrates(Being Used As A Global Options): {self.LResA}') 
            self.ListNameLabel.set_label(self.plist.title)
            # setting combo boxes data
            self.ListTypeList.append(['Video'])
            self.ListTypeList.append(['Audio'])
            print("Setting Up UI")
            # cell R
            # type
            self.ListTypeBox.set_model(self.ListTypeList)
            renderer_text = Gtk.CellRendererText.new()
            self.ListTypeBox.pack_start(renderer_text, True)
            self.ListTypeBox.add_attribute(renderer_text, "text", 0)
            self.ListTypeBox.set_active(0)
            # res
            self.ListResBox.set_model(self.ListVidRes)
            renderer_textv = Gtk.CellRendererText.new()
            self.ListResBox.pack_start(renderer_textv, True)
            self.ListResBox.add_attribute(renderer_textv, "text", 0)
            self.ListResBox.set_active(0)
            # finishing loading process
            self.loading = 0
            print("Done!")
            return
        except Exception as err:
            if err:
                self.loading = 0
                self.Fail(err)
                return 

    
    def loading_func(self, Target):
        self.MainLeaflet.set_visible_child(self.LoadingPage)

        self.loading = 1

        while self.loading == 1:
            self.LoadingProgressBar.pulse()
            sleep(0.25)

        self.MainLeaflet.set_visible_child(Target)



    def connect_func(self):
        try:
            host='http://google.com'
            DRequest.urlopen(host)
            print("Connection Has Been Established")
            return True
        except:
            print("Connection Failed")
            self.Fail("Failed Due To Connection Error")
            return False



    def islistq(self, printT, *args):
        if os.path.isfile(ffmpeg):
            # if a vid related to a list
            if findall(".*youtube\.com/watch\?v\=.{11}&list\=.{34}.*", self.MainBuffer.get_text()) or findall(".*youtu\.be/.{11}\?list\=.{34}.*", self.MainBuffer.get_text()):
                self.SubmitButton.set_label("Download Video")
                self.ListSuggestionRevealer.set_reveal_child(True)
                self.SubmitButton.set_sensitive(True)
                if printT:
                    print("URL Type: ( List Related Video )")
                return 0
            # if a playlist
            elif findall(".*youtube\.com/playlist\?list\=.{34}.*", self.MainBuffer.get_text()):
                self.SubmitButton.set_label("Download Playlist")
                self.ListSuggestionRevealer.set_reveal_child(False)
                self.SubmitButton.set_sensitive(True)
                if printT:
                    print("URL Type: ( Playlist )")
                return 1
            # if a plain vid
            elif findall(".*youtube\.com/watch\?v\=.{11}.*", self.MainBuffer.get_text()) or findall(".*youtu\.be\/.{11}.*", self.MainBuffer.get_text()) and not (findall(".*youtube\.com/watch\?v\=.{11}&list\=.{34}.*", self.MainBuffer.get_text()) or findall(".*youtu.be/.{11}\?list\=.{34}.*", self.MainBuffer.get_text())):
                self.ListSuggestionRevealer.set_reveal_child(False)
                self.SubmitButton.set_sensitive(True)
                self.SubmitButton.set_label("Download Video")
                if printT:
                    print("URL Type: ( Video )")
                return 2
            else:
                self.ListSuggestionRevealer.set_reveal_child(False)
                self.SubmitButton.set_sensitive(False)
                if printT:
                    print("URL Type: ( Invalid URL )")
                return 3




    def Fail(self, errno):
        if 'Errno -3' in str(errno):
            self.Error_Label.set_label("Error: Conection Error")
        else:
            self.Error_Label.set_label("Error: "+ str(errno))
        self.SubmitButton.set_sensitive(False)
        self.SuggestionCheck.set_active(False)
        self.MainLeaflet.set_visible_child(self.FailPage)



    def Toast_Handler(self, Toast):
        if self.isactivetoast == False:
            self.isactivetoast = True
            self.MainToastOverlay.add_toast(Toast)
            sleep(3)
            self.isactivetoast = False



    def On_Vid_DownloadFunc(self, button):
        button.set_sensitive(False)
        try:
            print("Adding A Task")
            if self.VidTypeBox.get_active() == 0:
                VidRes = self.ResV[self.VidResBox.get_active()]
                VidType = "Video"
                VidSize = self.SizesV[self.VidResBox.get_active()]
            else:
                VidRes = self.ResA[self.VidResBox.get_active()]
                VidType = "Audio"
                VidSize = self.SizesA[self.VidResBox.get_active()]
            self.AddToTasksDB(self.VidURL, VidRes, VidType, VidSize, self.VidName)
            self.UpdateDownloads()
            self.MainLeaflet.set_visible_child(self.DonePage)
        except Exception as err:
            if err:
                self.loading = 0
                self.Fail(err)
        button.set_sensitive(True)


    def On_List_DownloadFunc(self, button, *args): # <----------- Waiting For Test
        button.set_sensitive(False)
        try:
            # Some Checks
            unselected = 0
            for row in rows:
                if row.check.get_active() == False:
                    unselected += 1
            if unselected == len(rows):
                NoneToast = Adw.Toast.new("Nothing Have Been Selected!")
                NoneToast.set_timeout(3)
                self.Toast_Handler(NoneToast)
                button.set_sensitive(True)
                return
            if self.connect_func() == False:
                self.Fail("Connection Error")
                button.set_sensitive(True)
                return
            # Setting Loading 
            self.loading = 1
            Thread(target = self.loading_func, args = [self.DonePage], daemon = True).start()
            # Getting Download Type
            if self.ListTypeBox.get_active() == 0:
                ListRes = self.LResV[self.ListResBox.get_active()]
                ListType = "Video"
            else:
                ListRes = self.LResA[self.ListResBox.get_active()]
                ListType = "Audio"
            print("Selected: " + str(ListRes) + " " + ListType)
            # Getting Request Data 
            i = 0
            for video in self.plist.videos:
                if rows[i].check.get_active() == True:
                    if ListType == "Video":
                        if self.ListGlobalSwitch.get_state() == True:
                            ListRes = self.LResV[self.ListResBox.get_active()]  
                        else:
                            ListRes = list(rows[i].RListV.keys())[rows[i].CellRBox.get_active()]
                        Size = video.streams.filter(progressive = False, only_video = True, type = "video", res = ListRes, file_extension='mp4').first().filesize + video.streams.filter(progressive = False, only_audio = True, file_extension='webm').last().filesize
                    else:
                        if self.ListGlobalSwitch.get_state() == True:
                            ListRes = self.LResA[self.ListResBox.get_active()]
                        else:
                            ListRes = list(rows[i].RListA.keys())[rows[i].CellRBox.get_active()]
                        Size = video.streams.filter(type = "audio", abr = ListRes , file_extension = "webm").first().filesize
                    self.AddToTasksDB(rows[i].URL, ListRes, ListType, Size, rows[i].Title)
                i += 1
            self.UpdateDownloads()
            self.loading = 0
        except Exception as err:
            if err:
                self.loading = 0
                self.Fail(err)
        button.set_sensitive(True)

    @Gtk.Template.Callback()
    def Submit_Func(self, button):
        button.set_sensitive(False)
        x = self.islistq(printT = False)
        if os.path.isfile(ffmpeg):
            if x == 1:
                Thread(target = self.loading_func, args = [self.ListPage], daemon = True).start()
                Thread(target = self.Playlist_Data, daemon = True).start()
                print("Submitted A Playlist Downloading Request")
            elif x == 2:
                Thread(target = self.loading_func, args = [self.VidPage], daemon=True).start()
                Thread(target = self.Video_Data, daemon=True).start()
                print("Submitted A Video Downloading Request")
            elif x == 3:
                return
            elif x == 0:
                if self.SuggestionCheck.get_active():
                    Thread(target = self.loading_func, args = [self.ListPage], daemon = True).start()
                    Thread(target = self.Playlist_Data, daemon = True).start()
                    print("Submitted A Playlist Downloading Request")
                    self.ListSuggestionRevealer.set_reveal_child(False)
                    self.SuggestionCheck.set_active(False)
                else:
                    Thread(target = self.loading_func, args = [self.VidPage], daemon=True).start()
                    Thread(target = self.Video_Data, daemon=True).start()
                    print("Submitted A Video Downloading Request")
                    self.ListSuggestionRevealer.set_reveal_child(False)
        button.set_sensitive(True)


    @Gtk.Template.Callback()
    def on_vid_type_change(self, combo):
        if self.VidTypeBox.get_active() == 0:
            self.VidResBox.set_model(self.VidVidRes)
            self.VidResLabel.set_label("Resouloution :")
            self.VidResBox.set_active(0)
        else:
            self.VidResBox.set_model(self.VidAuidRes)
            self.VidResLabel.set_label("Bitrate :")
            self.VidResBox.set_active(0)


    @Gtk.Template.Callback()
    def on_list_type_change(self, combo):
        if self.ListTypeBox.get_active() == 0:
            self.ListResBox.set_model(self.ListVidRes)
            for i in range(len(rows)):
                rows[i].CellRBox.set_model(rows[i].VidResStore)
                rows[i].CellRBox.set_active(0)
            self.ListResBox.set_active(0)
        else:
            self.ListResBox.set_model(self.ListAuidRes)
            for i in range(len(rows)):
                rows[i].CellRBox.set_model(rows[i].AudResStore)
                rows[i].CellRBox.set_active(0)
            self.ListResBox.set_active(0)


    @Gtk.Template.Callback()
    def size_label_handler(self, *args):
        if self.VidTypeBox.get_active() == 0:
            self.VidSizeLabel.set_label(f" Size : {self.size_format(self.SizesV[self.VidResBox.get_active()])}")
        else:
            self.VidSizeLabel.set_label(f" Size : {self.size_format(self.SizesA[self.VidResBox.get_active()])}")


    @Gtk.Template.Callback()
    def On_Go_Back(self, button):
        button.set_sensitive(False)
        print("Cleaning...")
        if self.VidRequest == 1:
            self.VidVidRes.clear()
            self.VidAuidRes.clear()
            self.VidTypeList.clear()
            self.VidResBox.clear()
            self.VidTypeBox.clear()
            self.VidRequest = 0

        if self.ListRequest == 1:
            self.ListVidRes.clear()
            self.ListAuidRes.clear()
            self.ListTypeList.clear()
            self.ListResBox.clear()
            self.ListTypeBox.clear()
            
            for i in range(len(rows)):
                try:
                    rows[i].destroy_row(self.Playlist_Content_Group)
                except AttributeError as e:
                    print("Rows Has Not Been Finished Yet, Skipping")
                    break
                except Exception as err:
                    if err:
                        print("Something Un Expected Happened :/")
                        self.loading = 0
                        self.Fail(err)
                        return

            self.ListRequest = 0
        self.VidSizeLabel.set_label("")
        self.MainEntry.set_text("")
        loading = 0
        self.SubmitButton.set_sensitive(False)
        self.SuggestionCheck.set_active(False)
        self.ListSuggestionRevealer.set_reveal_child(False)
        self.MainLeaflet.set_visible_child(self.MainPage)
        print("Done")
        button.set_sensitive(True)


    @Gtk.Template.Callback()
    def On_Whole_List_Check_Label_Change(self, button):
        if button.get_active():
            self.SubmitButton.set_label("Download Playlist")
        else:
            self.SubmitButton.set_label("Download Video")

    
    @Gtk.Template.Callback()
    def On_Vid_Download(self, button):
        Thread(target = self.On_Vid_DownloadFunc, args = [button], daemon = True).start()


    @Gtk.Template.Callback()
    def On_List_Download(self, button):
        Thread(target = self.On_List_DownloadFunc, args = [button], daemon = True).start()


    @Gtk.Template.Callback()
    def on_list_global_switch(self, switch, *args):
        if switch.get_active() == True:
            self.GlobalRevealer.set_reveal_child(True)
            for i in range(len(rows)):
                rows[i].CellRBox.set_sensitive(False)
        else:
            self.GlobalRevealer.set_reveal_child(False)
            for i in range(len(rows)):
                rows[i].CellRBox.set_sensitive(True)
                rows[i].CellRBox.set_active(rows[i].RListV[self.LResV[self.ListResBox.get_active()]]
                                            if self.ListTypeBox.get_active() == 0 else 
                                            rows[i].RListA[self.LResA[self.ListResBox.get_active()]])             


    @Gtk.Template.Callback()
    def On_H_D_Button_Clicked(self, button):
        if button.get_icon_name() == 'preferences-system-time-symbolic':
            button.set_icon_name('document-save-symbolic')
            button.set_tooltip_text("View Downloads")
            self.H_D_Leaflet.set_visible_child(self.HistoryPage)
            self.ClearHistory_Revealer.set_reveal_child(True)
        else:
            button.set_icon_name('preferences-system-time-symbolic')
            button.set_tooltip_text("View History")
            self.H_D_Leaflet.set_visible_child(self.DownloadsPage)
            self.ClearHistory_Revealer.set_reveal_child(False)


    @Gtk.Template.Callback()
    def Clear_History(self, button, *args):
        button.set_sensitive(False)
        if self.History_Rows:
            for row in self.History_Rows.values():
                row.Remove()
        return

    @Gtk.Template.Callback()
    def ShowHDSwitch(self, source, *args):
        if source.get_mapped():
            self.H_D_Revealer.set_reveal_child(True)
            if self.H_D_Button.get_tooltip_text() == 'View Downloads':
                self.ClearHistory_Revealer.set_reveal_child(True)
        else: 
            self.H_D_Revealer.set_reveal_child(False)
            self.ClearHistory_Revealer.set_reveal_child(False)

class ListRow(Adw.ActionRow):
    def __init__(self, url , title, author, lengthf, views, Playlist_Content_Group, ListV, ListA):
        super().__init__()
        self.RListV = ListV
        self.RListA = ListA
        self.URL = url
        self.Title = title
        self.Author = author
        self.VidResStore = Gtk.ListStore(str)
        self.AudResStore = Gtk.ListStore(str)

        for i in range(len(list(self.RListV.keys()))):
            self.VidResStore.append([list(self.RListV.keys())[i]])
            self.RListV[list(self.RListV.keys())[i]] = i
        for i in range(len(list(self.RListA.keys()))):
            self.AudResStore.append([list(self.RListA.keys())[i]])
            self.RListA[list(self.RListA.keys())[i]] = i
        
        # the structure of the row
        self.CellRBox = Gtk.ComboBox.new_with_model(self.VidResStore)
        self.CellRBox.set_margin_top(10)
        self.CellRBox.set_margin_bottom(10)
        self.CellRBox.set_margin_end(10)
        renderer_text = Gtk.CellRendererText.new()
        self.CellRBox.pack_start(renderer_text, True)
        self.CellRBox.add_attribute(renderer_text, "text", 0)
        self.CellRBox.set_active(0)

        self.set_title_lines(1)
        self.set_subtitle_lines(1)
        self.check = Gtk.CheckButton()
        self.check.connect('toggled', self.on_list_row_selection)
        self.check.set_active(True)
        self.check.add_css_class("selection-mode")
        self.add_prefix(self.check)
        self.add_suffix(self.CellRBox)
        name = escape(title)
        if len(name) > 60:
            name = name[:60]+"..."
        self.set_title(name)
        self.set_subtitle(f"Channel: {escape(author)} Length: " + lengthf + " Views: " + f"{views:,}")
        Playlist_Content_Group.add(self)


    def destroy_row(self, Playlist_Content_Group):
        self.VidResStore.clear()
        self.AudResStore.clear()
        try:
            self.remove(self.CellRBox)
            self.CellRBox.run_dispose()
        except Exception as e:
            print(str(e))
            pass
        try:
            self.remove(self.check)
            self.check.run_dispose()
        except Exception as e:
            print(str(e))
            pass
        try:
            Playlist_Content_Group.remove(self)
            self.run_dispose()
        except Exception as e:
            print(str(e))
            pass
        self.URL = None
        self.Title = None
        self.Author = None
        self.RListV = None
        self.RListA = None


    def on_list_row_selection(self, SB, *args):
        if SB.get_active() == False:
            self.CellRBox.set_sensitive(False)
            self.set_css_classes(['dim-label'])
        else:
            if not self.check.get_active():
                self.CellRBox.set_sensitive(True)
            self.set_css_classes([])


class DownloadsRow(Adw.ActionRow):
    def __init__(self, DURL, DRes , DType, DLoc, DAddedOn, DSize, DName, DEXT, DID, VF, AF):
        super().__init__()
        # setting Some Values
        self.VFP = int(VF)
        self.AFP = int(AF)
        self.ext = DEXT
        #print(self.ext)
        self.add_css_class("card")
        self.Name = DName
        self.URL = DURL
        self.ID = DID
        self.Type = DType
        self.Loc = DLoc
        self.Res = DRes
        self.ispulse = False
        self.is_paused = False
        self.is_cancelled = False
        self.fkilled = False
        # Setting MainBox
        self.MainRevealer = Gtk.Revealer()
        self.MainRevealer.set_reveal_child(True)
        self.MainRevealer.set_transition_duration(150)
        self.MainRevealer.set_transition_type(1)
        self.MainBox = Gtk.Box()
        self.MainBox.set_hexpand(True)
        self.MainBox.set_margin_bottom(20)
        self.MainBox.set_margin_start(20)
        self.MainBox.set_margin_end(20)
        self.MainBox.set_margin_top(20)
        self.ffmpegRun = False
        # setting MainIcon Defaults
        if DType == "Video":
            self.MainIcon = Gtk.Image.new_from_icon_name("emblem-videos-symbolic")
        else:
            self.MainIcon = Gtk.Image.new_from_icon_name("emblem-music-symbolic")
        self.MainIcon.set_margin_end(20)
        self.MainIcon.set_pixel_size(50)
        # setting InnerBox1
        self.InnerBox1 = Gtk.Box.new(orientation = 1, spacing = 10)
        self.InnerBox1.set_hexpand(True)
        # setting InnerBox2
        self.InnerBox2 = Gtk.Box()
        self.InnerBox2.set_hexpand(True)
        # setting InnerBox3
        self.InnerBox3 = Gtk.Box.new(orientation = 1, spacing = 0)
        self.InnerBox3.set_hexpand(True)
        # setting ProgressBox
        self.ProgressBox = Gtk.Box.new(orientation = 0, spacing = 0)
        self.ProgressBox.set_hexpand(True)
        # setting Title
        if len(self.Name) > 35:
            Namex = self.Name[0:34] + '...'
            self.Title = Gtk.Label.new(Namex + f' ( {self.ext.upper()} )')
        else:
            self.Title = Gtk.Label.new(self.Name + f' ( {self.ext.upper()} )')
        self.Title.set_ellipsize(3)
        self.Title.set_max_width_chars(30)
        self.Title.set_xalign(0)
        self.Title.add_css_class("heading")
        # setting Subtitle
        if DType == "Video":
            self.Subtitle = Gtk.Label.new("Added On : " + DAddedOn + "   Resouloution : " + DRes + "   Size : " + DSize)
        else:
            self.Subtitle = Gtk.Label.new("Added On : " + DAddedOn + "   Bitrate : " + DRes + "   Size : " + DSize)
        self.Subtitle.set_ellipsize(3)
        self.Subtitle.set_max_width_chars(25)
        self.Subtitle.set_xalign(0)
        self.Subtitle.set_sensitive(False)
        self.Subtitle.set_margin_top(5)
        # setting Buttons
        self.ButtonBox = Gtk.Box.new(orientation = 0, spacing = 10)
        self.ButtonBox.set_margin_top(2)
        self.ButtonBox.set_margin_bottom(2)
        self.StopButton = Gtk.Button.new_from_icon_name("media-playback-stop-symbolic")
        self.StopButton.set_css_classes(["Cancel-Button"])
        self.StopButton.connect("clicked", self.Cancel)
        self.PauseButton = Gtk.Button.new_from_icon_name("media-playback-pause-symbolic")
        self.PauseButton.set_sensitive(True)
        self.PauseButton.set_css_classes(["Pause-Button"])
        self.PauseButton.connect("clicked", self.Pause)
        self.ButtonBox.append(self.StopButton)
        self.ButtonBox.append(self.PauseButton)
        # setting ProgressBar
        self.ProgressBar = Gtk.ProgressBar.new()
        self.ProgressBar.set_hexpand(True)
        self.ProgressBar.set_valign(3)
        self.ProgressBar.set_pulse_step(0.5)
        # setting ProgressLabel
        self.ProgressLabel = Gtk.Label.new("Connecting")
        self.ProgressLabel.set_css_classes(["dim-label", "caption"])
        self.ProgressLabel.set_width_chars(12)
        self.ProgressLabel.set_yalign(0.25)
        # structuring them
        self.MainBox.append(self.MainIcon)
        self.MainBox.append(self.InnerBox1)
        self.InnerBox1.append(self.InnerBox2)
        self.InnerBox2.append(self.InnerBox3)
        self.InnerBox2.append(self.ButtonBox)
        self.InnerBox3.append(self.Title)
        self.InnerBox3.append(self.Subtitle)
        self.ProgressBox.append(self.ProgressBar)
        self.ProgressBox.append(self.ProgressLabel)
        self.InnerBox1.append(self.ProgressBox)
        self.MainRevealer.set_child(self.MainBox)
        self.set_child(self.MainRevealer)
        Thread(target = self.Download_Handler, daemon = True).start()

    # TODO: Finalize The Controlling Buttons Stuff And Add Some UI Tweaks
    # TODO: Make Da qieuing Stuff For Both Of FFMPEG and Downloading Processes
    # TODO: Make Da History

    def Download_Handler(self, *args): # <------- Need Some Final Touches
        try:
            if os.path.isfile(data_dir + '/ffmpeg'):
                self.Name = sub('[^0-9a-zA-Z]+', '_', self.Name)
                yt = YouTube(self.URL)
                NIR = f'{self.Name}_{self.ID}_{self.Res}'
                if self.Type == "Video":
                    stream = yt.streams.filter(progressive = False, only_video = True, type = "video", file_extension='mp4', res= self.Res).first()
                    sa = yt.streams.filter(only_audio = True, file_extension = "webm").last().filesize
                    size = stream.filesize + sa
                    CHUNK = 1024*500
                    self.downloaded = self.AFP + self.VFP
                    if self.VFP+1 < stream.filesize:
                        self.chunk_handler(size, CHUNK, True, stream.url, f'{DownloadCacheDir}{NIR}_VF.download', stream.filesize, "VF")
                    if self.is_cancelled:
                        if os.path.isfile(f'{DownloadCacheDir}{NIR}_VF.download'):
                            os.remove(f'{DownloadCacheDir}{NIR}_VF.download')
                        self.ProgressLabel.set_label("Canceled")
                    else:
                        stream = yt.streams.filter(only_audio = True, file_extension = "webm").last()
                        #print(self.AFP)
                        #print(stream.filesize)
                        if self.AFP+1 < stream.filesize:
                            self.chunk_handler(size, CHUNK, False, stream.url, f'{DownloadCacheDir}{NIR}_AF.download', stream.filesize, "AF")
                        if self.is_cancelled:
                            if os.path.isfile(f'{DownloadCacheDir}{NIR}_AF.download'):
                                os.remove(f'{DownloadCacheDir}{NIR}_AF.download')
                            self.ProgressLabel.set_label("Canceled")
                        else:
                            self.ProgressLabel.set_label("Almost Done")
                            Thread(target = self.Progressbar_pulse_handler, daemon = True).start()
                            AFname = f"{DownloadCacheDir}{NIR}_AF.webm"
                            VFname = f"{DownloadCacheDir}{NIR}_VF.mp4"
                            if os.path.isfile(f"{DownloadCacheDir}{NIR}_AF.download") and os.path.isfile(f"{DownloadCacheDir}{NIR}_VF.download"):
                                os.rename(f"{DownloadCacheDir}{NIR}_AF.download", AFname)
                                os.rename(f"{DownloadCacheDir}{NIR}_VF.download", VFname)
                            self.Fname = f"{DownloadCacheDir}{NIR}.{self.ext}"
                            cmd = f'{ffmpegexec} -i {VFname} -i {AFname} -c:v copy -c:a aac {self.Fname} -y'
                            ####################################################################
                            #print(f"#{self.ID}: Running ffmpeg...")
                            self.ffmpegRun = True
                            self.ffmpegProcess = subprocess.Popen(cmd, shell = True)
                            self.ffmpegProcess.wait()
                            self.ffmpegRun = False
                            #######################################
                            if self.fkilled:
                                return
                            os.remove(AFname)
                            os.remove(VFname)
                            if not self.is_cancelled:
                                move(self.Fname, f"{self.Loc}{NIR}.{self.ext}")
                                self.ProgressLabel.set_label("Done")
                            else:
                                os.remove(self.Fname)
                                self.ProgressLabel.set_label("Canceled")
                            self.ispulse = False
                            self.ProgressBar.set_fraction(1)
                            self.Done()
                            ##################################################################
                else:
                    stream = yt.streams.filter(type = "audio", abr = self.Res, file_extension = "webm").first()
                    size = stream.filesize
                    CHUNK = 1024*500
                    self.downloaded = self.AFP + self.VFP
                    if self.AFP+1 < stream.filesize:
                        self.chunk_handler(size, CHUNK, True, stream.url, f'{DownloadCacheDir}{NIR}.download', size, "AF")
                    if self.is_cancelled:
                        if os.path.isfile(f'{DownloadCacheDir}{NIR}.download'):
                            os.remove(f'{DownloadCacheDir}{NIR}.download')
                        self.ProgressLabel.set_label("Canceled")
                    else:
                        self.ProgressLabel.set_label("Almost Done")
                        Thread(target = self.Progressbar_pulse_handler, daemon = True).start()
                        self.Fname = f'{DownloadCacheDir}{NIR}.webm'
                        if os.path.isfile(f'{DownloadCacheDir}{NIR}.download'):
                            os.rename(f'{DownloadCacheDir}{NIR}.download', self.Fname)
                        cmd = f'{ffmpegexec} -i {self.Fname} -ab {self.Res[0:-3]} -f {self.ext} {self.Fname[0 : -4]}{self.ext} -y'
                        #########################################################################################
                        print(f"#{self.ID}: Running ffmpeg...")
                        self.ffmpegRun = True
                        self.ffmpegProcess = subprocess.Popen(cmd, shell = True)
                        self.ffmpegProcess.wait()
                        self.ffmpegRun = False
                        ##########################################################
                        if self.fkilled:
                            return
                        os.remove(self.Fname)
                        if not self.is_cancelled:
                            move(f'{self.Fname[0 : -4]}{self.ext}', f'{self.Loc}{NIR}.{self.ext}')
                            self.ProgressLabel.set_label("Done")
                        else:
                            os.remove(f'{self.Fname[0 : -4]}{self.ext}')
                            self.ProgressLabel.set_label("Canceled")
                        self.ispulse = False
                        self.ProgressBar.set_fraction(1)
                        self.Done()
                if not self.is_cancelled:
                    print(f'Task #{self.ID}: Done')
                else:
                    print(f'Task #{self.ID}: Canceled')
                ##############################################################################################################
                return
            else:
                self.ProgressLabel.set_label("  Unable to find ffmpeg")
                sleep(5)
                Thread(target = self.Download_Handler, daemon = True).start()
                return
        except Exception as e:
            print(e)
            self.ProgressLabel.set_label("Failed")
            self.Fail()
            #handle moving to history and call cancel function
        # changing states


    def Progressbar_pulse_handler(self, *args):
        self.ispulse = True
        while self.ispulse == True:
            self.ProgressBar.pulse()
            sleep(0.25)


    def chunk_handler(self, size, CHUNK, zero, StreamUrl, Name, fsize, ftype):
        # writing chunk and checking if we can use larger 
        # chunk size based on the connection speed
        f = open(Name, 'ab')
        if zero:
            self.ProgressLabel.set_label(f"%0.00")
            self.ProgressBar.set_fraction(0)
        conn = connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
        self.db = conn.cursor()
        #print(fsize)
        if ftype == "VF":
            self.downloadedOF = self.VFP
        else:
            self.downloadedOF = self.AFP
        while self.downloadedOF+1 < fsize:
            if self.is_cancelled:
                self.ProgressLabel.set_label("Canceled")
                break
            elif not self.is_paused:
                range_header = f"bytes={self.downloadedOF+1}-{min(self.downloadedOF + CHUNK, fsize)}"
                #print(range_header)
                headers = {"User-Agent": "Mozilla/5.0", "accept-language": "en-US,en", "Range": range_header}
                request = DRequest.Request(StreamUrl, headers=headers, method="GET")
                response = DRequest.urlopen(request) # get a part of the stream as a response
                # time measurment
                start = (time_ns() + 500000) // 1000000
                chunk = response.read(CHUNK) # write the response chunk
                end = (time_ns() + 500000) // 1000000
                if chunk:
                    f.write(chunk)
                    self.downloaded += len(chunk)
                    self.downloadedOF += len(chunk)
                    self.db.execute(f'''UPDATE Downloads SET {ftype} = {self.downloadedOF} WHERE id = {self.ID}''')
                    conn.commit()
                    self.ProgressLabel.set_label(f"%{(self.downloaded / (size))*100:.2f}")
                    self.ProgressBar.set_fraction(self.downloaded / (size))
                    # time for da cool chunk calculations
                    CHUNKTIME = (end - start) / 300
                    if CHUNKTIME == 0:
                        CHUNKTIME = 1
                    if CHUNK == 0:
                        CHUNK = 1024*500
                    if int(CHUNK / CHUNKTIME) > 20*1024*1024:
                        CHUNK = 20*1024*1024
                    else:
                        CHUNK = int((CHUNK / CHUNKTIME)/1) # TODO: change it to the number of S Downloads
                    #print(str(CHUNK) + " " + str(CHUNKTIME))
                else:
                    # no more data
                    break
            else:
                sleep(0.3)
        conn.close()
        f.close()


    def Pause(self, button, *args):
        if button.get_icon_name() == "media-playback-pause-symbolic":
            button.set_icon_name("media-playback-start-symbolic")
            button.set_css_classes(["Download-Button"])
            self.is_paused = True
            if self.ffmpegRun:
                self.ffmpegProcess.send_signal(subprocess.signal.SIGSTOP)
            print(f"Task #{self.ID}: {self.Name} --Paused")
        else:
            button.set_icon_name("media-playback-pause-symbolic")
            button.set_css_classes(["Pause-Button"])
            self.is_paused = False
            if self.ffmpegRun:
                self.ffmpegProcess.send_signal(subprocess.signal.SIGCONT)
            print(f"Task #{self.ID}: {self.Name} --Resumed")
        return


    def Cancel(self, button, *args):
        # run Destroy as Canceled
        button.set_sensitive(False)
        self.is_cancelled = True
        Thread(target = self.Destroy, args=["Canceled"], daemon = True).start()
        return


    def Fail(self, *args):
        # run Destroy as Failed
        self.is_cancelled = True
        self.StopButton.set_sensitive(False)
        self.PauseButton.set_sensitive(False)
        Thread(target = self.Destroy, args=["Failed"], daemon = True).start()
        return


    def Done(self, *args):
        # run Destroy as Done
        Thread(target = self.Destroy, args=["Done"], daemon = True).start()
        return


    def Dispose(self, *args):
        self.MainRevealer.set_reveal_child(False)
        self.ispulse = False
        self.ProgressBar.unparent()
        self.ProgressLabel.unparent()
        self.ProgressLabel.run_dispose()
        self.ProgressBar.run_dispose()
        self.ProgressBox.unparent()
        self.ProgressBox.run_dispose()
        self.PauseButton.unparent()
        self.StopButton.unparent()
        self.PauseButton.run_dispose()
        self.StopButton.run_dispose()
        self.ButtonBox.unparent()
        self.ButtonBox.run_dispose()
        self.Title.unparent()
        self.Subtitle.unparent()
        self.Title.run_dispose()
        self.Subtitle.run_dispose()
        self.InnerBox3.unparent()
        self.InnerBox3.run_dispose()
        self.InnerBox2.unparent()
        self.InnerBox2.run_dispose()
        self.InnerBox1.unparent()
        self.InnerBox1.run_dispose()
        self.MainIcon.unparent()
        self.MainIcon.run_dispose()
        self.MainBox.unparent()
        self.MainBox.run_dispose()
        self.MainRevealer.unparent()
        self.MainRevealer.run_dispose()
        self.unparent()
        self.run_dispose()
        return


    def Destroy(self, status):
        # Remove From Downloads Db And Add To History DB
        # then Update History
        win.AddToHistoryDB(self.ID, status)
        win.UpdateHistory(win)
        win.Download_Rows.pop(str(self.ID))
        if len(list(win.Download_Rows.keys())) == 0:
            win.Nothing_D_Revealer.set_reveal_child(True)
            win.TaskManagerPage.set_needs_attention(False)
        self.killffmpeg()
        self.Dispose()
        return

    def killffmpeg(self):
        if self.ffmpegRun:
            self.fkilled = True
            self.ffmpegProcess.kill()


class HistoryRow(Adw.ActionRow):
    def __init__(self, id, res, type, loc, Finished_on, name, size, ext, url, status):
        super().__init__()
        self.status = status
        self.id = id
        self.res = res
        self.type = type
        self.loc = loc
        self.name = name
        self.size = size
        self.ext = ext
        self.url = url
        # setting Self
        self.set_css_classes(['card'])
        self.set_hexpand(True)
        # setting Main Box
        self.MainRevealer = Gtk.Revealer()
        self.MainRevealer.set_reveal_child(True)
        self.MainRevealer.set_transition_duration(150)
        self.MainRevealer.set_transition_type(1)
        self.MainBox = Gtk.Box()
        self.MainBox.set_margin_top(20)
        self.MainBox.set_margin_bottom(20)
        self.MainBox.set_margin_start(5)
        self.MainBox.set_margin_end(10)
        self.MainBox.set_hexpand(True)
        # setting Main Icon
        if type == "Video":
            self.MainIcon = Gtk.Image.new_from_icon_name("emblem-videos-symbolic")
        else:
            self.MainIcon = Gtk.Image.new_from_icon_name("emblem-music-symbolic")
        self.MainIcon.set_margin_end(20)
        self.MainIcon.set_margin_start(20)
        self.MainIcon.set_pixel_size(50)
        self.MainBox.append(self.MainIcon)
        # setting Inner Box 1
        self.InnerBox1 = Gtk.Box()
        self.InnerBox1.set_hexpand(True)
        self.MainBox.append(self.InnerBox1)
        # setting Inner Box 2
        self.InnerBox2 = Gtk.Box()
        self.InnerBox2.set_hexpand(True)
        self.InnerBox2.set_orientation(1)
        self.InnerBox2.set_margin_end(20)
        # setting Title
        if len(name) > 35:
            Namex = name[0:34] + '...'
            self.Title = Gtk.Label.new(Namex + f' ( {ext.upper()} )')
        else:
            self.Title = Gtk.Label.new(name + f' ( {ext.upper()} )')
        self.Title.set_ellipsize(3)
        self.Title.set_max_width_chars(40)
        self.Title.set_xalign(0)
        self.Title.add_css_class("heading")
        self.Title.set_margin_top(5)
        self.InnerBox2.append(self.Title)
        # setting Subtitle
        if type == "Video":
            self.Subtitle = Gtk.Label.new("Finished On : " + Finished_on + "   Resouloution : " + res + "   Status : " + status)
        else:
            self.Subtitle = Gtk.Label.new("Finished On : " + Finished_on + "   Bitrate : " + res + "   Status : " + status)
        self.Subtitle.set_ellipsize(3)
        self.Subtitle.set_max_width_chars(25)
        self.Subtitle.set_xalign(0)
        self.Title.add_css_class("dim-label")
        self.Subtitle.set_margin_top(5)
        self.InnerBox2.append(self.Subtitle)
        self.InnerBox1.append(self.InnerBox2)
        # setting Status Based Button
        if status == "Failed" or status == "Canceled":
            self.RetryButton = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
            self.RetryButton.set_valign(3)
            self.RetryButton.set_margin_end(10)
            self.RetryButton.set_tooltip_text("Retry")
            self.RetryButton.set_css_classes(["osd", "circular"])
            self.RetryButton.connect("clicked", self.Retry)
            self.InnerBox1.append(self.RetryButton)
        else:
            self.OpenLocButton = Gtk.Button.new_from_icon_name("folder-symbolic")
            self.OpenLocButton.set_valign(3)
            self.OpenLocButton.set_margin_end(10)
            self.OpenLocButton.set_tooltip_text("Open Location")
            self.OpenLocButton.set_css_classes(["osd", "circular"])
            self.OpenLocButton.connect("clicked", self.OpenLoc)
            self.InnerBox1.append(self.OpenLocButton)
        # setting Remove Button
        self.RemoveButton = Gtk.Button.new_from_icon_name("action-unavailable-symbolic")
        self.RemoveButton.set_valign(3)
        self.RemoveButton.set_margin_end(15)
        self.RemoveButton.set_tooltip_text("Remove From History")
        self.RemoveButton.set_css_classes(["osd", "circular"])
        self.RemoveButton.connect("clicked", self.Remove)
        self.InnerBox1.append(self.RemoveButton)
        self.MainRevealer.set_child(self.MainBox)
        self.set_child(self.MainRevealer)


    def Dispose(self, *args):
        self.MainRevealer.set_reveal_child(False)
        self.RemoveButton.set_sensitive(False)
        if self.status == "Failed" or self.status == "Canceled":
            self.RetryButton.unparent()
            self.RetryButton.run_dispose()
        else:
            self.OpenLocButton.unparent()
            self.OpenLocButton.run_dispose()
        self.RemoveButton.unparent()
        self.RemoveButton.run_dispose()
        self.Title.unparent()
        self.Title.run_dispose()
        self.Subtitle.unparent()
        self.Subtitle.run_dispose()
        self.InnerBox2.unparent()
        self.InnerBox2.run_dispose()
        self.InnerBox1.unparent()
        self.InnerBox1.run_dispose()
        self.MainIcon.unparent()
        self.MainIcon.run_dispose()
        self.MainBox.unparent()
        self.MainBox.run_dispose()
        self.MainRevealer.unparent()
        self.MainRevealer.run_dispose()
        self.unparent()
        self.run_dispose()
        return

    def DB_remove(self, *args):
        conn = connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
        self.db = conn.cursor()
        self.db.execute(f'''DELETE FROM History WHERE id = {self.id}''')
        conn.commit()
        conn.close()
        win.History_Rows.pop(self.id)
        if len(list(win.History_Rows.keys())) == 0:
            win.ClearHistory_Button.set_sensitive(False)
            win.Nothing_H_Revealer.set_reveal_child(True)
        else:
            win.ClearHistory_Button.set_sensitive(True)
            win.Nothing_H_Revealer.set_reveal_child(False)

    def Remove(self, *args):
        Thread(target = self.Dispose, daemon = True).start()
        Thread(target = self.DB_remove, daemon = True).start()
        return

    def OpenLoc(self, *args):
        subprocess.call(["xdg-open", self.loc])
        return

    def RetryF(self, *args):
        self.RetryButton.set_sensitive(False)
        win.AddToTasksDB(self.url, self.res, self.type, self.size, self.name)
        win.UpdateDownloads()
        self.RetryButton.set_sensitive(True)
        return

    def Retry(self, *args):
        Thread(target = self.RetryF, daemon = True).start()
        return


class AboutDialog(Gtk.AboutDialog):
    def __init__(self, parent):
        Gtk.AboutDialog.__init__(self)
        self.props.program_name = 'Mushroom'
        self.props.version = "0.1.0"
        self.props.authors = ['Abdalrahman Azab']
        self.props.copyright = '2022 Abdalrahman Azab'
        self.props.logo_icon_name = APPID
        self.props.modal = True
        self.set_transient_for(parent)
        self.present()



@Gtk.Template(resource_path='/com/github/azab246/mushroom/gtk/preferences.ui')
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'PreferencesWindow'

    DefaultLocEntry = Gtk.Template.Child()
    VContainerBox = Gtk.Template.Child()
    AContainerBox = Gtk.Template.Child()
    PreferencesSaveButton = Gtk.Template.Child()

    def __init__(self, parent):
        super().__init__()
        global DefaultLocPATH
        global DefaultVContainer
        global DefaultAContainer

        self.VContainerList = Gtk.ListStore(str)
        self.AContainerList = Gtk.ListStore(str)
        for E in list(VCOPT.keys()):
            self.VContainerList.append([f'{E.upper()}'])
        for E in list(ACOPT.keys()):
            self.AContainerList.append([f'{E.upper()}'])

        self.conf = self.Update_Preferences(True)

        self.VContainerBox.set_model(self.VContainerList)
        renderer_text = Gtk.CellRendererText.new()
        self.VContainerBox.pack_start(renderer_text, True)
        self.VContainerBox.add_attribute(renderer_text, "text", 0)
        self.VContainerBox.set_active(VCOPT[DefaultVContainer])

        self.AContainerBox.set_model(self.AContainerList)
        renderer_text = Gtk.CellRendererText.new()
        self.AContainerBox.pack_start(renderer_text, True)
        self.AContainerBox.add_attribute(renderer_text, "text", 0)
        self.AContainerBox.set_active(ACOPT[DefaultAContainer])

        self.set_transient_for(parent)

        self.VContainerBox.set_active(VCOPT[DefaultVContainer])
        self.AContainerBox.set_active(ACOPT[DefaultAContainer])

        self.buffer = Gtk.EntryBuffer()
        self.buffer.connect("inserted-text", self.CssFix)
        self.buffer.connect("deleted-text", self.CssFix)
        self.DefaultLocEntry.set_buffer(self.buffer)

        if len(DefaultLocPATH) > 50:
            self.DefaultLocEntry.set_placeholder_text(DefaultLocPATH[:50]+"...")
        else:
            self.DefaultLocEntry.set_placeholder_text(DefaultLocPATH)
        self.present()


    def Update_Preferences(printflag, *args):
        global DefaultLocPATH
        global DefaultVContainer
        global DefaultAContainer

        with open(ConfigFileDir, 'r') as f:
            conf = f.read().splitlines()
            DefaultLocPATH = conf[0]
            DefaultVContainer = conf[1]
            DefaultAContainer = conf[2]
        if printflag:
            print("Location For New Downloads Is : " + DefaultLocPATH)
            print("Default Container For Video Downloads Is : " + DefaultVContainer)
            print("Default Container For Audio Downloads Is : " + DefaultAContainer)
        f.close()
        return conf


    def When_Invalid_Path(self, message, *args):
        self.DefaultLocEntry.set_css_classes(['error'])
        self.DefaultLocEntry.props.secondary_icon_name = 'dialog-warning-symbolic'
        self.DefaultLocEntry.set_icon_tooltip_text(1, message)

        self.PreferencesSaveButton.set_css_classes(['Cancel-Button', 'pill'])
        sleep(0.6)
        self.PreferencesSaveButton.set_css_classes(['Accept-Button', 'pill'])


    def CssFix(self, *args):
        self.DefaultLocEntry.set_css_classes([])
        self.DefaultLocEntry.props.secondary_icon_name = ''


    @Gtk.Template.Callback()
    def on_DefaultLoc_Save(self, *args):
        global DefaultLocPATH
        global DefaultVContainer
        global DefaultAContainer

        path = self.DefaultLocEntry.get_text()
        if not path:
            path = self.conf[0]
        if path[0] != '/':
            path = '/' + path
        if path[len(path)-1] != '/':
            path = path + '/'
        if os.path.isdir(path):
            if f'/home/{GLib.get_user_name()}/' in path[0:len(GLib.get_user_name())+7]:
                with open(ConfigFileDir, 'w') as f:
                    f.write(path + '\n' + list(VCOPT.keys())[self.VContainerBox.get_active()] 
                                + '\n' + list(ACOPT.keys())[self.AContainerBox.get_active()])
                DefaultLocPATH = path
                DefaultVContainer = list(VCOPT.keys())[self.VContainerBox.get_active()]
                DefaultAContainer = list(ACOPT.keys())[self.AContainerBox.get_active()]
                self.close()
                if DefaultLocPATH != self.conf[0]:
                    print("Successfully Set Path To " + DefaultLocPATH)
                if DefaultVContainer != self.conf[1]:
                    print("Successfully Set VContainer To " + DefaultVContainer)
                if DefaultAContainer != self.conf[2]:
                    print("Successfully Set AContainer To " + DefaultAContainer)
            else:
                Thread(target = self.When_Invalid_Path, args = ["Non-Home Directory"], daemon = True).start()
        else:
            Thread(target = self.When_Invalid_Path, args = ["Invalid Directory"], daemon = True).start()



class MushroomApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id= APPID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("shutdown", self.quitF)
        self.create_action('quit', self.QB, ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('PreferencesWindow', self.on_Preferences_action)


    def do_activate(self):
        global win
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = MushroomWindow(application=self)
        win.present()

        style_provider = Gtk.CssProvider()
        style_provider.load_from_resource('/com/github/azab246/mushroom/res/style.css')

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = AboutDialog(self.props.active_window)

    def quitF(self, *args):
        print("Cleaning Up...")
        if not win.Download_Rows:
            print("No Downloads")
        else:
            for D in list(win.Download_Rows.keys()):
                win.Download_Rows[D].killffmpeg()
                print("Ending #" + str(D))


    def QB(self, *args):
        self.quit()
    

    def on_Preferences_action(self, widget, _):
        """Callback For app.PreferencesWindow action."""
        self.PreferencesWindow = PreferencesWindow(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    app = MushroomApplication()
    return app.run(sys.argv)
