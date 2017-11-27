# -*- coding: utf-8 -*-
import time, datetime
import datetime as dt
import xbmc, xbmcgui  

from threading import Timer
from os.path import join

from resources.lib import EPGXML, superfavourites
from resources.lib.EPGCtl import EPGControl, EPGGridView
from resources.lib import strings, settings
from resources.lib.utils import connectEpgDB, strToDatetime

'''
Global class handling EPG Gui.
'''
class XMLWindowEPG(xbmcgui.WindowXMLDialog):
    
    epgDb = epgXml = epgView = None
    is_closing = False
        
    '''
    Class init.
    '''    
    def __init__(self, strXMLname, strFallbackPath):
        xbmcgui.WindowXML.__init__(self, strXMLname, strFallbackPath, default='Default', defaultRes='720p', isMedia=True)
        
    
    '''
    @overrided
    Gui values init.
    '''
    def onInit(self):
        
        # Init EPG Grid global View
        globalControl = self.getControl(EPGControl.GLOBAL_CONTROL)
        
        self.epgView = EPGGridView()
        self.epgView.left, self.epgView.top = globalControl.getPosition()
        self.epgView.right = self.epgView.left + globalControl.getWidth()
        self.epgView.bottom = self.epgView.top + globalControl.getHeight()
        self.epgView.width = globalControl.getWidth()
        self.epgView.cellHeight = globalControl.getHeight() / settings.getDisplayChannelsCount()
        
        start_time = datetime.datetime.now()
        self.epgView.start_time = start_time.replace(minute=(0 if start_time.minute <= 29 else 30))
        
        self.setEPGBackgrounds() 
        self.setTimesLabels(self.epgView.start_time)
        self.setTimeMarker(timer=True)
        
        # Setting current day date.
        labelCurrentDate = self.getControl(EPGControl.label.DATE_TIME_TODAY)
        labelCurrentDate.setLabel(time.strftime("%d/%m/%Y"))
        
        database, cursor = connectEpgDB()
        self.epgDb  = EPGXML.EpgDb(database, cursor)
        self.epgXml = EPGXML.EpgXml(database, cursor, progress_bar=False)
        
        dt_stop = self.epgView.start_time + datetime.timedelta(minutes=settings.getTimelineToDisplay() - 2)
        self.setChannels(self.epgView.start_time, dt_stop)
    
    
    '''
    Set the EPG background with customer settings.
    '''
    def setEPGBackgrounds(self):
        
        bg = self.getControl(EPGControl.image.BACKGROUND)
        custombg = settings.useCustomBackground()
        bg_img = settings.getImageBackgroundCustom() if custombg else settings.getImageBackground()
        bg.setImage(bg_img, useCache=False) 
    
    
    '''
    Set the time marker position
    '''
    def setTimeMarker(self, timer=False):
        
        tm = self.getControl(EPGControl.image.TIME_MARKER)
        dt_now = datetime.datetime.now()
        delta = dt_now - self.epgView.start_time
        tm.setVisible(False) 
        
        if delta.seconds >=  0 and delta.seconds <= settings.getTimelineToDisplay() * 60:
            x = self.epgView.secondsToX(delta.seconds)
            tm.setPosition(int(x), tm.getY())
            tm.setVisible(True)
                 
        if timer and not xbmc.abortRequested and not self.is_closing:
            Timer(1, self.setTimeMarker, {timer: True}).start()   
    
    
    '''
    Return the time turned into EPG style
    '''
    def setTimesLabels(self, working_time):
        

        #Setting date and time controls.
        lTime1 = self.getControl(EPGControl.label.DATE_TIME_QUARTER_ONE)
        lTime2 = self.getControl(EPGControl.label.DATE_TIME_QUARTER_TWO)
        lTime3 = self.getControl(EPGControl.label.DATE_TIME_QUARTER_THREE)
        lTime4 = self.getControl(EPGControl.label.DATE_TIME_QUARTER_FOUR)
        
        lTime1.setLabel(self.__toTimeView(self.epgView.start_time, 0))
        lTime2.setLabel(self.__toTimeView(self.epgView.start_time, 1))
        lTime3.setLabel(self.__toTimeView(self.epgView.start_time, 2))
        lTime4.setLabel(self.__toTimeView(self.epgView.start_time, 3))
            
    
    
    def __toTimeView(self, ctime, multiplier):
        # Defining time for program guide and time labels zone.            
        increment = int(settings.getTimelineToDisplay() / 4) * multiplier
        later = (ctime + dt.timedelta(minutes=increment)).time()
        return str(("%02d:%02d") % (later.hour, later.minute))
        
    
    '''
    Sets first channels lines.
    '''
    def setChannels(self, dt_start, dt_stop):
        
        EPG = self.epgDb.getEpgGrid(dt_start, dt_stop, settings.getDisplayChannelsCount())
        
        noFocusTexture = join(settings.getAddonImagesPath(), 'buttons', 'tvguide-program-grey.png')
        focusTexture = join(settings.getAddonImagesPath(), 'buttons', 'tvguide-program-grey-focus.png')
        
        idx = 0
        for channel in EPG.values():            
            y = self.epgView.top + self.epgView.cellHeight * idx + int((self.epgView.cellHeight / 14))
            pchannel = xbmcgui.ControlLabel(16, y, 180, self.epgView.cellHeight - 2, channel["display_name"])
            self.addControl(pchannel)
            
            # Program details.
            programs = channel["programs"]
            
            if len(programs) == 0:
                nothing = "No data available"
                pbutton = xbmcgui.ControlButton(
                    self.epgView.left, 
                    self.epgView.top + self.epgView.cellHeight * idx, 
                    self.epgView.right - self.epgView.left - 2, 
                    self.epgView.cellHeight - 2, 
                    nothing, focusTexture, noFocusTexture)
                self.addControl(pbutton)
                  
            for program in programs: 
                
                program_start = strToDatetime(program["start"])    
                program_end   = strToDatetime(program["end"])            
                
                deltaStart = program_start - self.epgView.start_time
                deltaStop  = program_end - self.epgView.start_time
                
                y = self.epgView.top + self.epgView.cellHeight * idx
                x = self.epgView.secondsToX(deltaStart.seconds)
                
                if deltaStart.days < 0:
                    x = self.epgView.left
                
                width = self.epgView.secondsToX(deltaStop.seconds) - x
                
                if x + width > self.epgView.right:
                    width = self.epgView.right - x
                
                width -= 2
                
                if width < 28:
                    program["title"] = ""
                
                pbutton = xbmcgui.ControlButton(
                    x,y,
                    width,
                    self.epgView.cellHeight - 2,
                    program["title"],
                    noFocusTexture=noFocusTexture,
                    focusTexture=focusTexture
                )            
                self.addControl(pbutton)                        
            idx += 1
        
    
    '''
    @overrided
    Handle all xbmc action messages.
    '''
    def onAction(self, action):
        
        # Same as normal python Windows.
        if action == xbmcgui.ACTION_PREVIOUS_MENU:
            self.is_closing = True
            self.close()
        
        #if action == xbmcgui.ACTION_MOUSE_LEFT_CLICK or action == xbmcgui.ACTION_SELECT_ITEM:
        #    pass


    '''
    @overrided
    Handle all controls clicks, provide a control ID
    '''
    def onClick(self, controlID):
        pass
        
       
    '''
    @overrided
    Handle focusses changes between controls
    '''
    def onFocus(self, controlID):
        pass    
        

''''''''''''''''''''''''''''''
'''    Plugin entry point. '''
''''''''''''''''''''''''''''''

if __name__ == '__main__':    
    # Checking for bad configuration.   
    ok, error_msg = settings.checkMandatorySettings()
    if not ok:
        xbmcgui.Dialog().ok(strings.DIALOG_TITLE, strings.BAD_ADDON_CONFIGURATION, 
                            error_msg, strings.CONFIGURATION_TAKE_TIME_MSG)
        settings.addon.openSettings()
    
    else:      
        database, cursor = connectEpgDB()
        epgDb = EPGXML.EpgDb(database, cursor) 
        # Populate and create tables in case of first start
        if epgDb.firstTimeRuning():
            xbmcgui.Dialog().ok(strings.DIALOG_TITLE, strings.SFX_FIRST_START_DETECTED)
            epgXml = EPGXML.EpgXml(database, cursor, progress_bar=True)
            
            if epgXml.getXMLTV():
                epgDb.setFirstTimeRuning(0)
                epgDb.setUpdateDate()
                xbmc.sleep(1000)
                # Super favourites folder init.
                sf_folder = superfavourites.SuperFavouritesIptvFolder()
                sf_folder.createSubFolders()
                # All is done, restart required
                xbmcgui.Dialog().ok(strings.DIALOG_TITLE, strings.SFX_INIT_OK)
                sf_folder.close()
            
            epgDb.close()
            epgXml.close()
            del epgDb
            del epgXml
                   
        # Else, update epg in a thread
        else:
            # Starting GUI
            EPGgui = XMLWindowEPG('epg.xml', settings.getAddonPath())
            EPGgui.doModal() 
            del EPGgui        
        