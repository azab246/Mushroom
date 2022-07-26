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

from sre_constants import FAILURE
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
    VidRequest = 0
    ListRequest = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        global DefaultLocFileDir
        global DefaultLocPATH
        global cache_dir
        self.isactivetoast = False
        cache_dir = GLib.get_user_cache_dir()
        self.MainBuffer.connect("inserted_text", self.islistq)
        self.MainBuffer.connect("deleted_text", self.islistq)
        self.Download_Rows = {}
        DefaultLocFileDir = GLib.get_user_cache_dir() + "/tmp/DefaultDownloadLoc"
        conn = sqlite3.connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
        db = conn.cursor()
        db.execute('''
          CREATE TABLE IF NOT EXISTS Downloads
          ([url] TEXT, [res] TEXT, [type] TEXT, [location] TEXT, [added_on] TEXT, [size] TEXT, [name] TEXT, [id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL)
          ''')
        conn.commit()
        conn.close()
        try:
            with open(DefaultLocFileDir, 'r') as f:
                DefaultLocPATH = f.read()
                print(DefaultLocPATH)
            f.close
        except FileNotFoundError:
            with open(DefaultLocFileDir, 'x') as f:
                f.close()
            with open(DefaultLocFileDir, 'w') as f:
                f.write(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD))
                DefaultLocPATH = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
                f.close()
        threading.Thread(target = self.UpdateDownloads, daemon = True).start()





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
        cache_dir = GLib.get_user_cache_dir()
        fsize = self.size_format(size)
        dt = d.datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = sqlite3.connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
        self.db = conn.cursor()
        self.db.execute('''
          CREATE TABLE IF NOT EXISTS Downloads
          ([url] TEXT, [res] TEXT, [type] TEXT, [location] TEXT, [added_on] TEXT, [size] TEXT, [name] TEXT, [id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL)
          ''')
        print(res)
        self.db.execute("INSERT INTO Downloads (url, res, type, location, added_on, size, name) VALUES (?, ?, ?, ?, ?, ?, ?)", (url, str(res), dtype, MushroomApplication.Update_Download_Path(MushroomApplication), dt, fsize, name))
        conn.commit()
        conn.close()
        threading.Thread(target = self.UpdateDownloads, daemon = True).start()




    def UpdateDownloads(self, *args):
        conn = sqlite3.connect(cache_dir + '/tmp/MushroomData.db', check_same_thread=False)
        self.db = conn.cursor()
        queue = self.db.execute("SELECT * FROM Downloads")
        for video in queue:
            #print(video)
            #print(video[7])
            #print(list(self.Download_Rows.keys()))
            if str(video[7]) not in list(self.Download_Rows.keys()):
                print("Adding To Downloads List : " + video[6] + f"  ( {video[2]} )")
                self.Download_Rows[str(video[7])] = DownloadsRow(video[0], video[1], video[2], video[3], video[4], video[5], video[6], video[7])
                self.Downloads_List.prepend(self.Download_Rows[str(video[7])])
                self.TaskManagerPage.set_needs_attention(True)
        conn.close()




    #def UpdateHistory():



    def Video_Data(self, *args):
        if self.connect_func() == False:
                return
        try:
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
            for stream in self.vid.streams.filter(progressive = True, type = "video"):
                self.VidVidRes.append([f"{stream.resolution}"])
                self.ResV.append(f"{stream.resolution}")
                self.SizesV.append(stream.filesize)
                print(stream.resolution)
            for stream in self.vid.streams.filter(type = "audio"):
                self.VidAuidRes.append([f"{stream.abr}"])
                self.ResA.append(f"{stream.abr}")
                self.SizesA.append(stream.filesize)
                print(stream.abr)
            self.VidTypeList.append(['Video'])
            self.VidTypeList.append(['Audio'])
            print('70%')
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
            print('100%')
            # finishing loading process
            self.loading = 0
            self.loading_revealer.set_reveal_child(False)
            self.vid_revealer.set_reveal_child(True)
            self.Carousel.scroll_to(self.vid_revealer, True)
            self.VidURL = self.link
            return
        except Exception as err:
            if err:
                self.loading = 0
                self.Fail(err)
                return



    def Playlist_Data(self, *args):
        global rows
        if self.connect_func() == False:
            return
        try:
            self.ListRequest = 1
            #func
            self.ListVidRes = Gtk.ListStore(str)
            self.ListAuidRes = Gtk.ListStore(str)
            self.ListTypeList = Gtk.ListStore(str)
            self.link = self.MainBuffer.get_text()
            self.plist = pytube.Playlist(self.link)
            self.l = len(self.plist.videos)
            rows = [0]*self.l
            self.LResV = []
            self.LResA = []
            print("rows done")
            i = 0
            for video in self.plist.videos:
                #if self.connect_func() == False:
                    #return
                rows[i] = ListRow(self.plist.video_urls[i] , video.title, video.author, self.time_format(video.length), video.views, self.Playlist_Content_Group)
                i += 1
                print(i)
            self.ListNameLabel.set_label(self.plist.title)
            # setting combo boxes data
            for stream in self.plist.videos[0].streams.filter(progressive = True, type = "video"):
                self.ListVidRes.append([f"{stream.resolution}"])
                self.LResV.append(f"{stream.resolution}")
                print(stream.resolution)
            for stream in self.plist.videos[0].streams.filter(type = "audio"):
                self.ListAuidRes.append([f"{stream.abr}"])
                self.LResA.append(stream.abr)
                print(stream.abr)
            self.ListTypeList.append(['Video'])
            self.ListTypeList.append(['Audio'])
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
            self.loading_revealer.set_reveal_child(False)
            self.List_revealer.set_reveal_child(True)
            self.Carousel.scroll_to(self.List_revealer, True)
            print("022f")
            return
        except Exception as err:
            if err:
                self.loading = 0
                self.Fail(err)
                return




    def loading_func(self):
        while self.loading == 1:
            self.LoadingProgressBar.pulse()
            time.sleep(0.25)



    def connect_func(self):
        try:
            host='http://google.com'
            urllib.request.urlopen(host)
            print("Connection Has Been Established")
            return True
        except:
            print("Connection Failed")
            self.Fail("Failed Due To Connection Cut")
            return False



    def islistq(self, *args):
        # if a vid related to a list
        if re.findall(".*youtube\.com/watch\?v\=.{11}&list\=.{34}.*", self.MainBuffer.get_text()) or re.findall(".*youtu\.be/.{11}\?list\=.{34}.*", self.MainBuffer.get_text()):
            self.SubmitButton.set_label("Download Video")
            self.ListSuggestionRevealer.set_reveal_child(True)
            self.SubmitButton.set_sensitive(True)
            print("a vid related to a list")
            return 0
        # if a playlist
        elif re.findall(".*youtube\.com/playlist\?list\=.{34}.*", self.MainBuffer.get_text()):
            self.SubmitButton.set_label("Download Playlist")
            self.ListSuggestionRevealer.set_reveal_child(False)
            self.SubmitButton.set_sensitive(True)
            print("playlist")
            return 1
        # if a plain vid
        elif re.findall(".*youtube\.com/watch\?v\=.{11}.*", self.MainBuffer.get_text()) or re.findall(".*youtu\.be\/.{11}.*", self.MainBuffer.get_text()) and not (re.findall(".*youtube\.com/watch\?v\=.{11}&list\=.{34}.*", self.MainBuffer.get_text()) or re.findall(".*youtu.be/.{11}\?list\=.{34}.*", self.MainBuffer.get_text())):
            self.ListSuggestionRevealer.set_reveal_child(False)
            self.SubmitButton.set_sensitive(True)
            self.SubmitButton.set_label("Download Video")
            print("plain vid")
            return 2
        else:
            self.ListSuggestionRevealer.set_reveal_child(False)
            self.SubmitButton.set_sensitive(False)
            print("invalid url")
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



    def On_Vid_DownloadFunc(self):
        try:
            print("???1")
            if self.VidTypeBox.get_active() == 0:
                VidRes = self.ResV[self.VidResBox.get_active()]
                VidType = "Video"
                VidSize = self.SizesV[self.VidResBox.get_active()]
            else:
                VidRes = self.ResA[self.VidResBox.get_active()]
                VidType = "Audio"
                VidSize = self.SizesA[self.VidResBox.get_active()]
            print("???2")
            self.AddToTasksDB(self.VidURL, VidRes, VidType, VidSize, self.VidName)
            print("???3")
            self.vid_revealer.set_reveal_child(False)
            self.done_revealer.set_reveal_child(True)
            self.Carousel.scroll_to(self.done_revealer, True)
        except Exception as err:
            if err:
                self.loading = 0
                self.Fail(err)
                return



    def On_List_DownloadFunc(self):
        # Check For No Selection
        try:
            unselected = 0
            for row in rows:
                if row.check.get_active() == False:
                    unselected += 1
            NoneToast = Adw.Toast.new("Nothing Have Been Selected!")
            NoneToast.set_timeout(3)
            if unselected == len(rows):
                threading.Thread(target = self.Toast_Handler, args = [NoneToast], daemon = True).start()
                return
            self.List_revealer.set_reveal_child(False)
            self.loading_revealer.set_reveal_child(True)
            self.Carousel.scroll_to(self.loading_revealer, True)
            self.loading = 1
            if self.connect_func() == False:
                    return
            NoneToast.dismiss()
            threading.Thread(target = self.loading_func, daemon = True).start()
            print("???1")
            if self.ListTypeBox.get_active() == 0:
                ListRes = self.LResV[self.ListResBox.get_active()]
                ListType = "Video"
            else:
                ListRes = self.LResA[self.ListResBox.get_active()]
                ListType = "Audio"
            print("Selected: " + str(ListRes) + " " + ListType)
            Sizes = []
            i = 0
            for video in self.plist.videos:
                print("f")
                if rows[i].check.get_active() == True:
                    if ListType == "Video":
                        ListRes = self.LResV[self.ListResBox.get_active()]
                        try:
                            for stream in video.streams.filter(progressive = True, res = ListRes, type = "video"):
                                Sizes.append(stream.filesize)
                                print(str(stream) + str("t1"))
                                break
                            self.AddToTasksDB(rows[i].URL, ListRes, ListType, Sizes[i], rows[i].Title)
                        except IndexError:
                            print("Failed To Get That Res Trying Another..")
                            try:
                                ListRes = self.LResV[self.ListResBox.get_active() + 1]
                                for stream in video.streams.filter(progressive = True, res = ListRes, type = "video"):
                                    Sizes.append(stream.filesize)
                                    print(str(stream) + str("t2"))
                                    break
                                self.AddToTasksDB(rows[i].URL, ListRes, ListType, Sizes[i], rows[i].Title)
                            except IndexError:
                                print("Failed To Get That Res Trying Another..")
                                try:
                                    ListRes = self.LResV[self.ListResBox.get_active() - 1]
                                    for stream in video.streams.filter(progressive = True, res = ListRes, type = "video"):
                                        Sizes.append(stream.filesize)
                                        print(str(stream) + str("t3"))
                                        break
                                    self.AddToTasksDB(rows[i].URL, ListRes, ListType, Sizes[i], rows[i].Title)
                                except IndexError:
                                    print("Passing: " + rows[i].Title + "  (Cant Find Even Near-Specified Res)")
                                    Sizes.append("0")
                                    pass
                    else:
                        try:
                            ListRes = self.LResA[self.ListResBox.get_active()]
                            for stream in video.streams.filter(type = "audio", abr = ListRes):
                                Sizes.append(stream.filesize)
                                break
                            self.AddToTasksDB(rows[i].URL, ListRes, ListType, Sizes[i], rows[i].Title)
                        except IndexError:
                            try:
                                ListRes = self.LResA[self.ListResBox.get_active() + 1]
                                for stream in video.streams.filter(type = "audio", abr = ListRes):
                                    Sizes.append(stream.filesize)
                                    break
                                self.AddToTasksDB(rows[i].URL, ListRes, ListType, Sizes[i], rows[i].Title)
                            except IndexError:
                                try :
                                    ListRes = self.LResA[self.ListResBox.get_active() - 1]
                                    for stream in video.streams.filter(type = "audio", abr = ListRes):
                                        Sizes.append(stream.filesize)
                                        break
                                    self.AddToTasksDB(rows[i].URL, ListRes, ListType, Sizes[i], rows[i].Title)
                                except IndexError:
                                    print("Passing: " + rows[i].Title + "  (Cant Find Even Near-Specified Res)")
                                    Sizes.append("0")
                                    pass
                i += 1
            print("???3")
            self.loading = 0
            self.List_revealer.set_reveal_child(True)
            self.loading_revealer.set_reveal_child(False)
            self.done_revealer.set_reveal_child(True)
            self.Carousel.scroll_to(self.done_revealer, True)
        except Exception as err:
            if err:
                self.loading = 0
                self.Fail(err)
                return




    @Gtk.Template.Callback()
    def Submit_Func(self, button):
        if self.islistq() == 1:
            self.MainRevealer.set_reveal_child(False)
            self.loading_revealer.set_reveal_child(True)
            self.Carousel.scroll_to(self.loading_revealer, True)
            self.loading = 1
            threading.Thread(target = self.loading_func, daemon = True).start()
            threading.Thread(target = self.Playlist_Data, daemon = True).start()
            print("022")
        elif self.islistq() == 2:
            self.MainRevealer.set_reveal_child(False)
            self.loading_revealer.set_reveal_child(True)
            self.Carousel.scroll_to(self.loading_revealer, True)
            self.loading = 1
            threading.Thread(target = self.loading_func, daemon=True).start()
            threading.Thread(target = self.Video_Data, daemon=True).start()
            print("023")

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
            self.ListResLabel.set_label("Resouloution :")
            self.ListResBox.set_active(0)
        else:
            self.ListResBox.set_model(self.ListAuidRes)
            self.ListResLabel.set_label("Bitrate :")
            self.ListResBox.set_active(0)


    @Gtk.Template.Callback()
    def size_label_handler(self, *args):
        if self.VidTypeBox.get_active() == 0:
            self.VidSizeLabel.set_label(f" Size : {self.size_format(self.SizesV[self.VidResBox.get_active()])}")
        else:
            self.VidSizeLabel.set_label(f" Size : {self.size_format(self.SizesA[self.VidResBox.get_active()])}")

    @Gtk.Template.Callback()
    def On_Go_Back(self, button):

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
                rows[i].destroy_row(self.Playlist_Content_Group)
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

    @Gtk.Template.Callback()
    def On_Vid_Download(self, button):
        threading.Thread(target = self.On_Vid_DownloadFunc, daemon = True).start()

    @Gtk.Template.Callback()
    def On_List_Download(self, button):
        threading.Thread(target = self.On_List_DownloadFunc, daemon = True).start()


class ListRow(Adw.ActionRow):
    def __init__(self, url , title, author, lengthf, views, Playlist_Content_Group):
        super().__init__()
        self.URL = url
        self.Title = title
        self.Author = author
        self.set_title_lines(1)
        self.set_subtitle_lines(1)
        self.check = Gtk.CheckButton()
        self.check.set_active(True)
        self.check.add_css_class("selection-mode")
        self.add_prefix(self.check)
        name = html.escape(title)
        if len(name) > 80:
            name = name[:80]+"..."
        self.set_title(name)
        self.set_subtitle(f"Channel: {html.escape(author)} Length: " + lengthf + " Views: " + f"{views:,}")
        Playlist_Content_Group.add(self)

    def destroy_row(self, Playlist_Content_Group):
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

class DownloadsRow(Adw.ActionRow):
    def __init__(self, DURL, DRes , DType, DLoc, DAddedOn, DSize, DName, DID):
        super().__init__()
        # setting Some Values
        self.add_css_class("card")
        self.Name = DName
        self.URL = DURL
        self.ID = DID
        self.is_paused = False
        self.is_cancelled = False
        # Setting MainBox
        self.MainBox = Gtk.Box()
        self.MainBox.set_hexpand(True)
        self.MainBox.set_margin_bottom(20)
        self.MainBox.set_margin_start(20)
        self.MainBox.set_margin_end(20)
        self.MainBox.set_margin_top(20)
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
        self.Title = Gtk.Label.new(self.Name)
        self.Title.set_ellipsize(3)
        self.Title.set_max_width_chars(25)
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
        self.StopButton = Gtk.Button.new_from_icon_name("media-playback-stop-symbolic")
        self.StopButton.set_css_classes(["Cancel-Button"])
        self.StopButton.connect("clicked", self.Cancel)
        self.PauseButton = Gtk.Button.new_from_icon_name("media-playback-pause-symbolic")
        self.PauseButton.set_sensitive(True)######
        self.PauseButton.set_css_classes(["Pause-Button"])
        self.PauseButton.connect("clicked", self.Pause)
        self.ButtonBox.append(self.StopButton)
        self.ButtonBox.append(self.PauseButton)
        # setting ProgressBar
        self.ProgressBar = Gtk.ProgressBar.new()
        self.ProgressBar.set_hexpand(True)
        self.ProgressBar.set_valign(3)
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


    def Download_Handler(self, *args):
        self.Pause.set_sensitive(False)
        try:
            
            yt = pytube.YouTube(self.URL)
            stream = yt.streams.first()
            filesize = stream.filesize  # get the video size
            with open('', 'wb') as f:
                stream = pytube.request.stream(stream.url) # get an iterable stream
                downloaded = 0
                while True:
                    if self.is_cancelled:
                        # handling cancelation
                        break
                    if not self.is_paused:
                        chunk = next(stream, None) # get next chunk of video
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.ProgressLabel.set_label(f"%{(downloaded / filesize)*100:.2f}")
                        else:
                            # no more data
                            # handling success state
                            break
            print('done')
        except Exception as e:
            print(e)
            # handling FAILURE
        # changing states

    def Pause(self, button, *args):
        if button.get_icon_name() == "media-playback-pause-symbolic":
            button.set_icon_name("media-playback-start-symbolic")
            button.set_css_classes(["Download-Button"])
            self.is_paused = True
            print("Task: " + self.Name + " --Paused")
        else:
            button.set_icon_name("media-playback-pause-symbolic")
            button.set_css_classes(["Pause-Button"])
            self.is_paused = False
            print("Task: " + self.Name + " --Resumed")
        return

    def Cancel(self, button, *args):
        return

    def Fail(self, *args):
        return

    def Done(self, *args):
        return

    def Destroy(self, *args):
        return




class AboutDialog(Gtk.AboutDialog):

    def __init__(self, parent):
        Gtk.AboutDialog.__init__(self)
        self.props.program_name = 'Mushroom'
        self.props.version = "0.1.0"
        self.props.authors = ['Abdalrahman Azab']
        self.props.copyright = '2022 Abdalrahman Azab'
        self.props.logo_icon_name = 'com.github.azab246.mushroom'
        self.props.modal = True
        self.set_transient_for(parent)



class MushroomApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='com.github.azab246.mushroom',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.create_action('quit', self.quit, ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('DefaultLocation', self.on_DefaultLoc_action)


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
        about.present()

    def on_DefaultLoc_action(self, widget, _):
        # Setting The Dialog
        self.DefaultLocation = Gtk.MessageDialog(parent = self.props.active_window, message_type = 4)
        self.DefaultLocation.props.text = 'Edit Default Download Path'
        self.DefaultLocation.props.secondary_text = "Enter A Default Folder Path To Be Used In The Future Downloads"
        # Setting Dialog Widgets
        self.DefaultLocEntry = Gtk.Entry()
        self.DefaultLocEntry.set_margin_top(15)
        DefaultLocPATH = self.Update_Download_Path()
        if len(DefaultLocPATH) > 52:
            self.DefaultLocEntry.set_placeholder_text(DefaultLocPATH[:52]+"...")
        else:
            self.DefaultLocEntry.set_placeholder_text(DefaultLocPATH)
        self.DefaultLocButtonBox = Gtk.Box.new(0, 40)
        self.DefaultCancel = Gtk.Button.new_with_label("Cancel")
        self.DefaultCancel.connect("clicked", self.on_DefaultLoc_Cancel)
        self.DefaultCancel.set_css_classes(["Cancel-Button", "pill"])
        self.DefaultSave = Gtk.Button.new_with_label("  Save  ")
        self.DefaultSave.connect("clicked", self.on_DefaultLoc_Save)
        self.DefaultSave.set_css_classes(["Accept-Button","pill"])
        self.DefaultLocButtonBox.append(self.DefaultCancel)
        self.DefaultLocButtonBox.append(self.DefaultSave)
        self.DefaultLocButtonBox.set_halign(3)
        self.DefaultLocation.props.message_area.set_margin_top(20)
        self.DefaultLocation.props.message_area.set_margin_bottom(20)
        self.DefaultLocation.props.message_area.set_spacing(20)
        self.DefaultLocation.props.modal = True
        self.DefaultLocation.set_transient_for(self.props.active_window)
        self.Invalid_Path_Label = Gtk.Label.new("Invalid Directory!")
        self.Invalid_Path_Label.add_css_class("heading")
        self.Invalid_Path_Revealer = Gtk.Revealer()
        self.Invalid_Path_Revealer.set_transition_duration(150)
        self.Invalid_Path_Revealer.set_transition_type(5)
        self.Invalid_Path_Revealer.set_child(self.Invalid_Path_Label)
        self.DefaultLocation.props.message_area.append(self.DefaultLocEntry)
        self.DefaultLocation.props.message_area.append(self.Invalid_Path_Revealer)
        self.DefaultLocation.props.message_area.append(self.DefaultLocButtonBox)
        self.DefaultLocation.present()

    def on_DefaultLoc_Cancel(self, *args):
        self.DefaultLocation.close()

    def Update_Download_Path(self, *args):
        with open(DefaultLocFileDir, 'r') as f:
            DefaultLocPATH = f.read()
        print(DefaultLocPATH)
        f.close()
        return DefaultLocPATH

    def on_DefaultLoc_Save(self, *args):
        if os.path.isdir(self.DefaultLocEntry.get_text()):
            with open(DefaultLocFileDir, 'w') as f:
                f.write(self.DefaultLocEntry.get_text())
            DefaultLocPATH = self.DefaultLocEntry.get_text()
            self.DefaultLocation.close()
            print("Successfully Set To " + DefaultLocPATH)
        else:
            threading.Thread(target = self.When_Invalid_Path, daemon = True).start()

    def When_Invalid_Path(self, *args):
        if self.Invalid_Path_Revealer.get_reveal_child() == False:
            print("Invalid Directory")
            self.Invalid_Path_Revealer.set_reveal_child(True)
            time.sleep(2)
            self.Invalid_Path_Revealer.set_reveal_child(False)

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

