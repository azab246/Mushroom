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

from concurrent.futures import process
from curses.ascii import isalpha, isdigit
import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import GObject, Gtk, Adw, Pango, Gdk, Gio, GLib
import pytube
import re
import sqlite3
import threading
import time
import datetime as d
import html
import urllib
import os
import subprocess
import tarfile
from shutil import rmtree, move

global APPID
APPID = 'com.github.azab246.mushroom'


@Gtk.Template(resource_path='/com/github/azab246/mushroom/gtk/window.ui')
class MushroomWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'MushroomWindow'

    MainBuffer = Gtk.Template.Child()
    MainEntry = Gtk.Template.Child()
    MainRevealer = Gtk.Template.Child()
    ListSuggestionRevealer = Gtk.Template.Child()
    SubmitButton = Gtk.Template.Child()
    List_revealer = Gtk.Template.Child()
    loading_revealer = Gtk.Template.Child()
    vid_revealer = Gtk.Template.Child()
    done_revealer = Gtk.Template.Child()
    fail_revealer = Gtk.Template.Child()
    Playlist_Content_Group = Gtk.Template.Child()
    Carousel = Gtk.Template.Child()
    LoadingAdwPage = Gtk.Template.Child()
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
    Downloads_List = Gtk.Template.Child()
    MainToastOverlay = Gtk.Template.Child()
    TaskManagerPage = Gtk.Template.Child()
    GlobalRevealer = Gtk.Template.Child()
    Nothing_D_Revealer = Gtk.Template.Child()
    Fail_Button = Gtk.Template.Child()
    ListGlobalSwitch = Gtk.Template.Child()
    TMLable = Gtk.Template.Child()
    H_D_Carousel = Gtk.Template.Child()
    Downloads_Revealer = Gtk.Template.Child()
    History_Revealer = Gtk.Template.Child()
    History_List = Gtk.Template.Child()
    Nothing_H_Revealer = Gtk.Template.Child()
    ClearHistory_Revealer = Gtk.Template.Child()
    ClearHistory_Button = Gtk.Template.Child()
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
        VCOPT = {'mp4' : 0, 'mkv' : 1, 'webm' : 2, 'mov' : 3, 'flv' : 4}
        ACOPT = {'mp3' : 0, 'aac' : 1, 'ogg' : 2, 'wav' : 3, 'flac' : 4}
        self.isactivetoast = False
        cache_dir = GLib.get_user_cache_dir()
        data_dir = GLib.get_user_data_dir()
        ConfigFileDir = GLib.get_user_cache_dir() + "/tmp/config"
        ffmpeg = f'{data_dir}/ffmpeg'
        DownloadCacheDir = cache_dir + '/DownloadsCache/'
        # Database + DLoc File
        conn = sqlite3.connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
        db = conn.cursor()
        db.execute('''
          CREATE TABLE IF NOT EXISTS Downloads
          ([url] TEXT, [res] TEXT, [type] TEXT, [location] TEXT, [added_on] TEXT, [size] TEXT, [name] TEXT,[ext] TEXT , [id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL)
          ''')
        db.execute('''
          CREATE TABLE IF NOT EXISTS History
          ([len] TEXT, [res] TEXT, [type] TEXT, [location] TEXT, [Finished_on] TEXT, [name] TEXT, [id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL)
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
        self.Download_Rows = {}
        threading.Thread(target = self.AppData_Initialization, daemon = True).start()
        threading.Thread(target = self.UpdateDownloads, daemon = True).start()
        threading.Thread(target = self.UpdateHistory, daemon = True).start()
        
        print("All New Downloads Will Be Exported At : " + DefaultLocPATH)
        print("New Video Files Will Be Exported As : " + DefaultVContainer)
        print("New Audio Files Will Be Exported As : " + DefaultAContainer)
        


    def AppData_Initialization(self, *args):
        # Download cache Folder on /chache
        if not os.path.isdir(cache_dir + '/DownloadsCache'):
            os.mkdir(cache_dir + '/DownloadsCache')
        else:
            #if path exists cleaning it
            for file in os.scandir(cache_dir + '/DownloadsCache'):
                os.remove(file.path)


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
            urllib.request.urlretrieve(URL, f"{data_dir}/ffmpeg.download")
            os.rename(f"{data_dir}/ffmpeg.download", f"{data_dir}/ffmpeg.tar.xz")  
            downloaded = tarfile.open(f"{data_dir}/ffmpeg.tar.xz")
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
        print(DefaultVContainer + "  " + DefaultLocPATH)
        fsize = self.size_format(size)
        dt = d.datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = sqlite3.connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
        self.db = conn.cursor()
        self.db.execute('''CREATE TABLE IF NOT EXISTS Downloads ([url] TEXT, [res] TEXT, [type] TEXT, [location] TEXT, [added_on] TEXT, [size] TEXT, [name] TEXT, [ext] TEXT, [id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL)''')
        self.db.execute('''INSERT INTO Downloads (url, res, type, location, added_on, size, name, ext) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (url, str(res), dtype, DefaultLocPATH, dt, fsize, name, Ext))
        conn.commit()
        conn.close()


    def AddToHistoryDB(self, ID):
        return


    def UpdateDownloads(self, *args):
        if os.path.isfile(ffmpeg):
            conn = sqlite3.connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
            self.db = conn.cursor()
            queue = self.db.execute("SELECT * FROM Downloads")
            for video in queue:
                if str(video[8]) not in list(self.Download_Rows.keys()):
                    print("Adding To Downloads List : " + video[6] + f"  ( {video[2]} )")
                    self.Download_Rows[str(video[7])] = DownloadsRow(video[0], video[1], video[2], video[3], video[4], video[5], video[6], video[7], video[8])
                    self.Downloads_List.prepend(self.Download_Rows[str(video[7])])
                    self.TaskManagerPage.set_needs_attention(True)
            if len(list(self.Download_Rows.keys())) == 0:
                self.Nothing_D_Revealer.set_reveal_child(True)
                self.Downloads_Revealer.set_valign(3)
            else:
                self.Nothing_D_Revealer.set_reveal_child(False)
                self.Downloads_Revealer.set_valign(1)
            conn.close()

    # TODO: Make Clear History Button not to be Sensitive in Case that there
    #       Ist A Data In  History To Clear 
    def UpdateHistory(self, *args):
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
            self.vid = pytube.YouTube(self.link)
            self.VidDetails.set_title(html.escape(self.vid.title))
            self.VidName = self.vid.title
            self.VidDetails.set_description(f"Channel: {html.escape(self.vid.author)}  Length: " + f"{self.time_format(self.vid.length)}" + "   Views: " + f"{self.vid.views:,}")
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
                    print(stream.resolution)
            for stream in self.vid.streams.filter(type = "audio", file_extension='webm'):
                print(stream.bitrate)
                if f"{stream.abr}" not in self.ResA:
                    self.VidAuidRes.append([f"{stream.abr}"])
                    self.ResA.append(f"{stream.abr}")
                    self.SizesA.append(stream.filesize)
                    print(stream.abr)
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
            self.plist = pytube.Playlist(self.link)
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

    
    def loading_func(self, RevealerFrom, RevealerTo):
        self.loading_revealer.set_reveal_child(True)
        self.Carousel.scroll_to(self.loading_revealer, True)
        RevealerFrom.set_reveal_child(False)

        self.loading = 1

        while self.loading == 1:
            self.LoadingProgressBar.pulse()
            time.sleep(0.25)

        RevealerTo.set_reveal_child(True)
        self.Carousel.scroll_to(RevealerTo, True)
        self.loading_revealer.set_reveal_child(False)



    def connect_func(self):
        try:
            host='http://google.com'
            urllib.request.urlopen(host)
            print("Connection Has Been Established")
            return True
        except:
            print("Connection Failed")
            self.Fail("Failed Due To Connection Error")
            return False



    def islistq(self, printT, *args):
        if os.path.isfile(ffmpeg):
            # if a vid related to a list
            if re.findall(".*youtube\.com/watch\?v\=.{11}&list\=.{34}.*", self.MainBuffer.get_text()) or re.findall(".*youtu\.be/.{11}\?list\=.{34}.*", self.MainBuffer.get_text()):
                self.SubmitButton.set_label("Download Video")
                self.ListSuggestionRevealer.set_reveal_child(True)
                self.SubmitButton.set_sensitive(True)
                if printT:
                    print("URL Type: ( List Related Video )")
                return 0
            # if a playlist
            elif re.findall(".*youtube\.com/playlist\?list\=.{34}.*", self.MainBuffer.get_text()):
                self.SubmitButton.set_label("Download Playlist")
                self.ListSuggestionRevealer.set_reveal_child(False)
                self.SubmitButton.set_sensitive(True)
                if printT:
                    print("URL Type: ( Playlist )")
                return 1
            # if a plain vid
            elif re.findall(".*youtube\.com/watch\?v\=.{11}.*", self.MainBuffer.get_text()) or re.findall(".*youtu\.be\/.{11}.*", self.MainBuffer.get_text()) and not (re.findall(".*youtube\.com/watch\?v\=.{11}&list\=.{34}.*", self.MainBuffer.get_text()) or re.findall(".*youtu.be/.{11}\?list\=.{34}.*", self.MainBuffer.get_text())):
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
        self.MainRevealer.set_reveal_child(False)
        self.SubmitButton.set_sensitive(False)
        self.SuggestionCheck.set_active(False)
        self.List_revealer.set_reveal_child(False)
        self.vid_revealer.set_reveal_child(False)
        self.done_revealer.set_reveal_child(False)
        self.fail_revealer.set_reveal_child(True)
        self.Carousel.scroll_to(self.fail_revealer, True)



    def Toast_Handler(self, Toast):
        if self.isactivetoast == False:
            self.isactivetoast = True
            self.MainToastOverlay.add_toast(Toast)
            time.sleep(3)
            self.isactivetoast = False



    def On_Vid_DownloadFunc(self, button):
        button.set_sensitive(False)
        try:
            print("Adding A Task")
            #print(1)
            if self.VidTypeBox.get_active() == 0:
                VidRes = self.ResV[self.VidResBox.get_active()]
                VidType = "Video"
                VidSize = self.SizesV[self.VidResBox.get_active()]
            else:
                VidRes = self.ResA[self.VidResBox.get_active()]
                VidType = "Audio"
                VidSize = self.SizesA[self.VidResBox.get_active()]
            print(2)
            self.AddToTasksDB(self.VidURL, VidRes, VidType, VidSize, self.VidName)
            self.UpdateDownloads()
            print(3)
            self.vid_revealer.set_reveal_child(False)
            self.done_revealer.set_reveal_child(True)
            self.Carousel.scroll_to(self.done_revealer, True)
        except Exception as err:
            if err:
                self.loading = 0
                self.Fail(err)
        button.set_sensitive(True)


    def On_List_DownloadFunc(self, button): # <----------- Waiting For Test
        button.set_sensitive(False)
        try:
            # Some Checks
            unselected = 0
            for row in rows:
                if row.check.get_active() == False:
                    unselected += 1
            NoneToast = Adw.Toast.new("Nothing Have Been Selected!")
            NoneToast.set_timeout(3)
            if unselected == len(rows):
                threading.Thread(target = self.Toast_Handler, args = [NoneToast], daemon = True).start()
                button.set_sensitive(True)
                return
            if self.connect_func() == False:
                self.Fail("Connection Error")
                button.set_sensitive(True)
                return
            NoneToast.dismiss()
            # Setting Loading 
            self.loading = 1
            threading.Thread(target = self.loading_func, args = [self.List_revealer, self.done_revealer], daemon = True).start()
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
            for videoO in self.plist.videos:
                if rows[i].check.get_active() == True:
                    if ListType == "Video":
                        if self.ListGlobalSwitch.get_state() == True:
                            ListRes = self.LResV[self.ListResBox.get_active()]  
                        else:
                            ListRes = list(rows[i].RListV.keys())[rows[i].CellRBox.get_active()]
                        Size = videoO.streams.filter(progressive = False, only_video = True, type = "video", res = ListRes, file_extension='mp4').first().filesize + videoO.streams.filter(progressive = False, only_audio = True, file_extension='webm').last().filesize
                    else:
                        if self.ListGlobalSwitch.get_state() == True:
                            ListRes = self.LResA[self.ListResBox.get_active()]
                        else:
                            ListRes = list(rows[i].RListA.keys())[rows[i].CellRBox.get_active()]
                        Size = videoO.streams.filter(type = "audio", abr = ListRes , file_extension = "webm").first().filesize
                    self.AddToTasksDB(rows[i].URL, ListRes, ListType, Size, rows[i].Title)
                i += 1
            self.UpdateDownloads()
            self.loading = 0
        except Exception as err:
            if err:
                self.loading = 0
                self.Fail(err)
                button.set_sensitive(True)
        button.set_sensitive(True)

    @Gtk.Template.Callback()
    def Submit_Func(self, button):
        button.set_sensitive(False)
        x = self.islistq(printT = False)
        if os.path.isfile(ffmpeg):
            if x == 1:
                threading.Thread(target = self.loading_func, args = [self.MainRevealer, self.List_revealer], daemon = True).start()
                threading.Thread(target = self.Playlist_Data, daemon = True).start()
                print("Submitted A Playlist Downloading Request")
            elif x == 2:
                threading.Thread(target = self.loading_func, args = [self.MainRevealer, self.vid_revealer], daemon=True).start()
                threading.Thread(target = self.Video_Data, daemon=True).start()
                print("Submitted A Video Downloading Request")
            elif x == 3:
                return
            elif x == 0:
                if self.SuggestionCheck.get_active():
                    threading.Thread(target = self.loading_func, args = [self.MainRevealer, self.List_revealer], daemon = True).start()
                    threading.Thread(target = self.Playlist_Data, daemon = True).start()
                    print("Submitted A Playlist Downloading Request")
                    self.ListSuggestionRevealer.set_reveal_child(False)
                    self.SuggestionCheck.set_active(False)
                else:
                    threading.Thread(target = self.loading_func, args = [self.MainRevealer, self.vid_revealer], daemon=True).start()
                    threading.Thread(target = self.Video_Data, daemon=True).start()
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
        self.MainRevealer.set_reveal_child(True)
        self.SubmitButton.set_sensitive(False)
        self.SuggestionCheck.set_active(False)
        self.ListSuggestionRevealer.set_reveal_child(False)
        self.Carousel.scroll_to(self.MainRevealer, True)
        self.List_revealer.set_reveal_child(False)
        self.vid_revealer.set_reveal_child(False)
        self.done_revealer.set_reveal_child(False)
        self.fail_revealer.set_reveal_child(False)
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
        threading.Thread(target = self.On_Vid_DownloadFunc, args = [button], daemon = True).start()


    @Gtk.Template.Callback()
    def On_List_Download(self, button):
        threading.Thread(target = self.On_List_DownloadFunc, args = [button], daemon = True).start()


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
            self.TMLable.set_label("History")
            button.set_tooltip_text("View Downloads")
            self.Downloads_Revealer.set_reveal_child(False)
            self.H_D_Carousel.scroll_to(self.History_Revealer, True)
            self.History_Revealer.set_reveal_child(True)
            self.ClearHistory_Revealer.set_reveal_child(True)
        else:
            button.set_icon_name('preferences-system-time-symbolic')
            self.TMLable.set_label("Downloads")
            button.set_tooltip_text("View History")
            self.Downloads_Revealer.set_reveal_child(True)
            self.History_Revealer.set_reveal_child(False)
            self.H_D_Carousel.scroll_to(self.Downloads_Revealer, True)
            self.ClearHistory_Revealer.set_reveal_child(False)


    @Gtk.Template.Callback()
    def Clear_History(self, button, *args):
        return


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
        name = html.escape(title)
        if len(name) > 60:
            name = name[:60]+"..."
        self.set_title(name)
        self.set_subtitle(f"Channel: {html.escape(author)} Length: " + lengthf + " Views: " + f"{views:,}")
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
    def __init__(self, DURL, DRes , DType, DLoc, DAddedOn, DSize, DName, DEXT, DID):
        super().__init__()
        # setting Some Values
        self.ext = DEXT
        print(self.ext)
        self.ispulse = False
        self.add_css_class("card")
        self.Name = DName
        self.URL = DURL
        self.ID = DID
        self.Type = DType
        self.Loc = DLoc
        self.Res = DRes
        self.is_paused = False
        self.is_cancelled = False
        # Setting MainBox
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
        self.set_child(self.MainBox)
        threading.Thread(target = self.Download_Handler, daemon = True).start()

    # TODO: ADD The Pause POWER To FFMPEG process
    # TODO: Finalize The Controlling Buttons Stuff And Add Some UI Tweaks
    # TODO: Make Da qieuing Stuff For Both Of FFMPEG and Downloading Processes
    # TODO: Make Da History

    def Download_Handler(self, *args): # <------- Need Some Final Touches
        try:
            if os.path.isfile(data_dir + '/ffmpeg'):
                for i in range(len(self.Name)):
                    if not isalpha(self.Name[i]) and not isdigit(self.Name[i]):
                        self.Name = self.Name[0:i] + '_' + self.Name[i+1:len(self.Name)]
                yt = pytube.YouTube(self.URL)
                NIR = f'{self.Name}_{self.ID}_{self.Res}'
                if self.Type == "Video":
                    stream = yt.streams.filter(progressive = False, only_video = True, type = "video", file_extension='mp4', res= self.Res).first()
                    sa = yt.streams.filter(only_audio = True, file_extension = "webm").last().filesize
                    size = stream.filesize + sa
                    CHUNK = 1024*500
                    self.downloaded = 0
                    with open(f'{DownloadCacheDir}{NIR}_VF.download', 'wb') as f:
                        response = urllib.request.urlopen(stream.url) # get an iterable stream
                        self.ProgressLabel.set_label("%0")
                        self.chunk_handler(size, response, f, CHUNK)
                        f.close()
                    if self.is_cancelled:
                        os.remove(f'{DownloadCacheDir}{NIR}_VF.download')
                        self.ProgressLabel.set_label("Canceled")
                        return
                    else:
                        with open(f'{DownloadCacheDir}{NIR}_AF.download', 'wb') as f:
                            stream = yt.streams.filter(only_audio = True, file_extension = "webm").last()
                            response = urllib.request.urlopen(stream.url)
                            self.chunk_handler(size, response, f, CHUNK)
                            f.close()
                        if self.is_cancelled:
                            os.remove(f'{DownloadCacheDir}{NIR}_AF.download')
                            self.ProgressLabel.set_label("Canceled")
                        else:
                            self.ProgressLabel.set_label("Almost Done")
                            threading.Thread(target = self.Progressbar_pulse_handler, daemon = True).start()
                            AFname = f"{DownloadCacheDir}{NIR}_AF.webm"
                            VFname = f"{DownloadCacheDir}{NIR}_VF.mp4"
                            Fname = f"{DownloadCacheDir}{NIR}.{self.ext}"
                            os.rename(f"{DownloadCacheDir}{NIR}_AF.download", AFname)
                            os.rename(f"{DownloadCacheDir}{NIR}_VF.download", VFname)
                            cmd = f'{ffmpeg} -i {VFname} -i {AFname} -c:v copy -c:a aac {Fname}'
                            ####################################################################
                            self.ffmpegRun = True
                            self.ffmpegProcess = subprocess.Popen(cmd, shell = True)
                            self.ffmpegProcess.wait()
                            self.ffmpegRun = False
                            #######################################
                            os.remove(AFname)
                            os.remove(VFname)
                            if not self.is_cancelled:
                                move(Fname, f"{self.Loc}{NIR}.{self.ext}")
                                self.ProgressLabel.set_label("Done")
                            else:
                                os.remove(Fname)
                                self.ProgressLabel.set_label("Canceled")
                            self.ispulse = False
                            self.ProgressBar.set_fraction(1)
                            self.Done()
                            ##################################################################
                else:
                    stream = yt.streams.filter(type = "audio", abr = self.Res, file_extension = "webm").first()
                    size = stream.filesize
                    CHUNK = 1024*500
                    self.downloaded = 0
                    with open(f'{DownloadCacheDir}{NIR}.download', 'wb') as f:
                        response = urllib.request.urlopen(stream.url) # get an iterable stream
                        self.ProgressLabel.set_label("%0")
                        self.chunk_handler(size, response, f, CHUNK)
                        f.close()
                    if self.is_cancelled:
                        os.remove(f'{DownloadCacheDir}{NIR}.download')
                        self.ProgressLabel.set_label("Canceled")
                        return
                    else:
                        self.ProgressLabel.set_label("Almost Done")
                        threading.Thread(target = self.Progressbar_pulse_handler, daemon = True).start()
                        Fname = f'{DownloadCacheDir}{NIR}.webm'
                        os.rename(f'{DownloadCacheDir}{NIR}.download', Fname)
                        cmd = f'{ffmpeg} -i {Fname} -ab {self.Res[0:-3]} -f {self.ext} {Fname[0 : -4]}{self.ext}'
                        #########################################################################################
                        self.ffmpegRun = True
                        self.ffmpegProcess = subprocess.Popen(cmd, shell = True)
                        self.ffmpegProcess.wait()
                        self.ffmpegRun = False
                        ##########################################################
                        os.remove(Fname)
                        if not self.is_cancelled:
                            move(f'{Fname[0 : -4]}{self.ext}', f'{self.Loc}{NIR}.{self.ext}')
                            self.ProgressLabel.set_label("Done")
                        else:
                            os.remove(f'{Fname[0 : -4]}{self.ext}')
                            self.ProgressLabel.set_label("Canceled")
                        self.ispulse = False
                        self.ProgressBar.set_fraction(1)
                        self.Done()
                print(f'Task #{self.ID}: Done')
                ##############################################################################################################
                return
            else:
                self.ProgressLabel.set_label("  Unable to find ffmpeg")
                time.sleep(5)
                threading.Thread(target = self.Download_Handler, daemon = True).start()
                return
                #self.Cancel()
        except Exception as e:
            print(e)
            self.ProgressLabel.set_label("Failed")
            self.ProgressBar.set_css_classes(['Cancel-Button'])
            time.sleep(1)
            self.ProgressLabel.set_label("  Moving To History")
            time.sleep(4)
            #handle moving to history and call cancel function
        # changing states


    def Progressbar_pulse_handler(self, *args):
        self.ispulse = True
        while self.ispulse == True:
            self.ProgressBar.pulse()
            time.sleep(0.25)


    def chunk_handler(self, size, response, f, CHUNK):
        # writing chunk and checking if we can use larger 
        # chunk size based on the connection speed
        while True:
            if self.is_cancelled:
                self.ProgressLabel.set_label("Canceled")
                break
            elif not self.is_paused:
                start = (time.time_ns() + 500000) // 1000000
                chunk = response.read(CHUNK) # get next chunk of the stream
                end = (time.time_ns() + 500000) // 1000000
                if chunk:
                    f.write(chunk)
                    self.downloaded += CHUNK
                    self.ProgressLabel.set_label(f"%{(self.downloaded / (size))*100:.2f}")
                    self.ProgressBar.set_fraction(self.downloaded / (size))
                    CHUNKTIME = (end - start) / 1000
                    if CHUNKTIME == 0:
                        CHUNKTIME = 1
                    if CHUNK == 0:
                        CHUNK = 1024*500
                    if int(CHUNK / CHUNKTIME) > 20*1024*1024:
                        CHUNK = 20*1024*1024
                    else:
                        CHUNK = int(CHUNK / CHUNKTIME)
                    print(str(CHUNK) + " " + str(CHUNKTIME))
                else:
                    # no more data
                    break
                


    def Pause(self, button, *args):
        if button.get_icon_name() == "media-playback-pause-symbolic":
            button.set_icon_name("media-playback-start-symbolic")
            button.set_css_classes(["Download-Button"])
            self.is_paused = True
            print(f"Task #{self.ID}: {self.Name} --Paused")
        else:
            button.set_icon_name("media-playback-pause-symbolic")
            button.set_css_classes(["Pause-Button"])
            self.is_paused = False
            print(f"Task #{self.ID}: {self.Name} --Resumed")
        return


    def Cancel(self, button, *args):
        self.is_cancelled = True
        if self.ffmpegRun:
            self.ffmpegProcess.send_signal(subprocess.signal.SIGINT)
        return


    def Fail(self, *args):
        return


    def Done(self, *args):
        return


    def Destroy(self, *args):
        return


class HistoryRow(Adw.ActionRow):
    def __init__(self, VID):
        super().__init__()

    def Destroy(self, *args):
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
        time.sleep(0.6)
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
                threading.Thread(target = self.When_Invalid_Path, args = ["Non-Home Directory"], daemon = True).start()
        else:
            threading.Thread(target = self.When_Invalid_Path, args = ["Invalid Directory"], daemon = True).start()



class MushroomApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id= APPID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.create_action('quit', self.quit, ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('PreferencesWindow', self.on_Preferences_action)


    def do_activate(self):

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
