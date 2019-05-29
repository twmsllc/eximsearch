#!/opt/imh-python/bin/python
#/usr/bin/python

import urwid, datetime, os, subprocess, sys, json, re, shlex, gzip, time, logging, collections, socket, threading
from multiprocessing import Pool, Queue, current_process
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta
os.nice(20)
FORMAT = '%(lineno)d :: %(funcName)s :: %(message)s'
logging.basicConfig(format=FORMAT,filename='log',filemode='a', level=logging.DEBUG)
ACTIVE = 'active'
PREV = 'prev'
BODY = 'body'
HEADER = 'header'
FOOTER = 'footer'


info = logging.info
debug = logging.debug
warning = logging.warning

"""
SETTINGS / DEFAULT VALUE CLASSES
"""

class GlobalSettings(): 
    def __init__(self):
        """This class contains general settings / default variables for the application
        """
        self.dt = DateTimeSettings()
        self.lf = LogFileSettings()
        self.rl = ResultListSettings()
        self.df = DisplayFrameSettings()
        self.menus = Menus()
        self.hostname = socket.gethostname()
        self.menuEnabled = True
        self.divChars = 1
        self.filterGuide = (
            "You can have multiple filters per filter type (ie. multiple senders, multiple recipients, etc) "
            "and these will be filtered as OR. \nEx: Two sender filters of user1@domain.com and user2@domain.com, will show all "
            "query results that were sent by user1@domain.com OR user2@domain.com.\nFilters of different types are filtered as AND."
            "Ex: Sender filter user1@domain.com and Date filter of 2019-05-24, will show all query results that were sent by "
            "user1@domain.com on the date 2019-05-24\nAcceptable Date-time Formats:MM-DD-YYYY or MM-DD-YYYY_HH:MM:SS\n"
            "Date Range formats: Start date,End date with NO SPACES. Ex: 2019-05-01,2019-05-31\nMessage Type Options: Incoming, Outgoing, Local"
                )
        self.filterTypes = [
            'sender',
            'recipient',
            'date',
            'type'
        ]
    def unhandled_input(self,key):
        if type(key) == str:
            if key in ('q', 'N'):   
                views.activate('quit_loop',focus_position=BODY)
            if key in ('N', 'n'):
                views.activate('new_search', focus_position=BODY)
            if key in ('S', 's'):
                views.activate('coming_soon', focus_position=FOOTER)
            if key in 'tab':
                if frame.focus_position == 'footer':
                    frame.focus_position = 'body'
                else:
                    if self.menuEnabled:
                        frame.focus_position = 'footer'
            if key in 'f5':
                debug('Current View: %s', state.get_view_name(ACTIVE))
            if key in 'f6' and state.get_view(PREV):
                debug('Previous View: %s', state.get_view_name(PREV))
            #if state.get_view(ACTIVE) == 'single_entry':
            #    if key in ('B', 'b'):
            #        views.activate('result_list',focus_position=BODY)
            #if state.get_view(ACTIVE) == 'result_list':
            #    if key in ('F', 'f'):
            #        views.activate('add_remove_filters', focus_position=BODY)
            #if s.activeView == 'filter_results':
            #    if key in ('A', 'a'):
            #        search.apply_current_filters()
class DateTimeSettings():
    def __init__(self):
        """Settings for DateTime functions / formatting
        """
        self.logDateFormat ="%Y-%m-%d"
        self.displayDateFormat = "%m-%d-%Y"
        self.stringToDateFormat = "%Y-%m-%d"
        self.logDateTimeFormat = "%Y-%m-%d_%H:%M:%S.%f"
        self.displayDateTimeFormat = "%m-%d-%Y_%H:%M:%S"
    def stringToDate(self,newFilter):
        try:
            datetime.strptime(newFilter, self.displayDateTimeFormat)
        except ValueError:
            try:
                datetime.strptime(newFilter, self.displayDateFormat)
            except:
                return False
            else:
                return datetime.strptime(newFilter, self.displayDateFormat)
        else:
            return datetime.strptime(newFilter, self.displayDateTimeFormat)
class DisplayFrameSettings():
    def __init__(self):
        """Settings & Defaults for the Applications Interface
        """
        self.mainTitle = 'Exim Search Utility'
        self.mainSubTitle = 'If you can do it better, then do it'
        self.palette = [
            # Name  , foreground,  background 
            ('header',  'black',    'light gray'),
            ('footer',  'black',    'light gray'),
            ('body',    'white',    'default'),
            ('bold',    'dark green, bold' , 'black')
        ]
class Menus():
        def __init__(self):
            self.choose_logs = [
                ['(Q)uit','quit_loop']]

            self.home = [
                ['(N)ew Search', 'new_search'],
                ['Add / Remove (F)ilters','add_remove_filters'],
                ['(S)tats Summary','coming_soon'],
                ['(T)est Mailer','coming_soon'],
                ['(Q)uit','quit_loop']]
            self.new_search = self.home
            self.search_progress = self.home
        
            self.results_list = [
                ['(N)ew Search', 'new_search'],
                ['(F)ilter Current Results','add_remove_filters'],
                ['(C)lear Applied Filters','clear_applied_filters'],
                ['(H)ome','home'],
                ['(Q)uit','quit_loop']]
            self.results_summary = self.results_list

            self.single_entry = [
                ['(N)ew Search','new_search'],
                ['(S)how Related Entries','show_related_entries'],
                ['(B)ack To Result List','result_list'],
                ['(H)ome','home'],
                ['(Q)uit','quit_loop']]
            self.add_remove_filters = [
                ['(N)ew Search','new_search'],
                ['(A)pply Current Results','apply_filters'],
                ['(B)ack To Result List','result_list'],
                ['(H)ome','home'],
                ['(Q)uit','quit_loop']]
            self.quit_loop = []
class LogFileSettings():
    def __init__(self):
        """Settings for the LogFile class / objects
        """
        self.dir = '/var/log/'
        self.mainLogName = 'exim_mainlog'
        self.mainLogPath = os.path.join(self.dir, self.mainLogName)
        self.selectedLogs = []
class ResultListSettings():
    def __init__(self):
        """Settings specific to the ResultList view
        """
        self.ButtonColWidth = 7
        self.divChars = 1
        self.resultOverflow = False
s = GlobalSettings()
"""
CUSTOM WIDGET CLASSES
"""
class ButtonLabel(urwid.SelectableIcon):
    def __init__(self, text):
        """Subclassing for urwid.Button's labeling
           This customization removes the cursor from
           the active button
           This should only need to be called by the 
           FixedButton class.
        
        Arguments:
            urwid {class} -- urwid base class
            text {str} -- Button Label
        """
        curs_pos = len(text) + 1 
        urwid.SelectableIcon.__init__(self, 
            text, cursor_position=curs_pos)
class FixedButton(urwid.Button):
    """SubClass of the urwid.Button class used 
       along with ButtonLabel in order to customize
       the appearance and behavior of buttons.
    
    Arguments:
        urwid {class} -- urwid base class
    
    Returns:
        urwid.Button -- a standard urwid Button
    """
    _selectable = True
    signals = ["click"]
    def __init__(self, thisLabel, on_press=None, user_data=None):
        """Creates a new Button
        
        Arguments:
            thisLabel {text} -- Button Label
        
        Keyword Arguments:
            on_press {callback} -- function to be executed on click (default: {None})
            user_data {tuple} -- tuple (or list) that contains any arguments 
                 or data to be passed to on_ress function  (default: {None})
        """
        self._label = ButtonLabel(thisLabel)
        # you could combine the ButtonLabel object with other widgets here
        self.user_data = user_data
        self.on_press = on_press
        display_widget = self._label 
        urwid.WidgetWrap.__init__(self, 
            urwid.AttrMap(display_widget, 
            None, focus_map="header"))
        self.callback = on_press
    def keypress(self, size, key):
        """Overrides default urwid.Button.keypress method
        
        Arguments:
            size {int} -- size of widget
            key {bytes or unicode} -- [a single keystroke value]
        
        Returns:
            None or Key -- [None if key was handled by this widget or 
                            key (the same value passed) if key was 
                            not handled by this widget]
        """
        if key in ('enter', 'space'):
            if self.user_data != None:
                self.callback(self.user_data)
            else:
                self.callback()
        else:
            return key
        #key = super(FixedButton, self).keypress(size, key)
        #logging.info("keypress super key = %s", key)
    def set_label(self, new_label):
        """Method to allow changing the button's label
        
        Arguments:
            new_label {[str]} -- [New Button Label]
        """
        self._label.set_text(str(new_label))
    def mouse_event(self, size, event, button, col, row, focus):
        """
        handle any mouse events here
        and emit the click signal along with any data 
        """
        pass
    def disable(self):
        """Function to allow the disabling of the button"""
        _selectable = False
    def enable(self):
        """Function to allow the enabling of a disabled button"""
        _selectable = True
class QuestionBox(urwid.Filler):
    def keypress(self, size, key):
        if key != 'enter':
            return super(QuestionBox, self).keypress(size, key)
        entry = self.original_widget.get_edit_text()
        self.original_widget.set_edit_text('')
        debug('%s Entry String: %s', self.original_widget, entry)
        state.set_query(entry)
        views.activate('search_progress',is_threaded=True,on_join=search.new)
class MyWidgets():
    """A collection of functions to simplify creation of
       frequently used widgets """

    def __init__(self):
        self.div = urwid.Divider(' ',top=0,bottom=0)
        self.blankFlow = self.getText('body','','center')
        self.blankBox = urwid.Filler(self.blankFlow)
        self.searchProgress = urwid.ProgressBar('body', 'header', current=0, done=100, satt=None)
    def getButton(self, thisLabel, callingObject, callback, user_data=None, buttonMap='bold', focus_map='header'):
        """Creates and returns a FixedButton object.
        
        Arguments:
            thisLabel {[str]} -- Label of the Button
            callingObject {obj} -- The name of the object that the callback belongs to
            callback {function} -- [function to be executed when button is clicked]
        
        Keyword Arguments:
            user_data {tuple} -- A tuple or list of arguments or data to be passed to 
                                 the callback function (default: {None})
        Returns:
            FixedButton -- A FixedButton object
            FLOW WIDGET
        """

        button = FixedButton(str(thisLabel),
        on_press=getattr(callingObject, callback),
        user_data=user_data)
        button._label.align = 'center'
        buttonMap = urwid.AttrMap(button, buttonMap, focus_map=focus_map)
        return buttonMap
    def getText(self,format,textString, alignment,**kwargs):
        """Creates a basic urwid.Text widget
        
        Arguments:
            format {str} -- Name of a format attribute specified in DisplayFrameSettings.pallette
            textString {str} -- The text string contents of text widget
            alignment {str} -- Text alignment (left, right, center)
        
        Returns:
            urwid.Text -- An urwidText Widget
            FLOW WIDGET
        """
        return urwid.Text((format, textString), align=alignment, wrap='space', **kwargs)
    def getColRow(self,items, **kwargs):
        """Creates a single row of columns
        
        Arguments:
            items {list} -- List of widgets, each item forming one column.
                             Items may be tuples containing width specs
        
        Returns:
            [urwid.Column] -- An urwid.Columns object 
            FLOW / BOX WIDGET
        """
        return urwid.Columns(items,
            dividechars=s.divChars,
            focus_column=None,
            min_width=1,
            box_columns=None)
    def getLineBox(self,contents,title, **kwargs):
        """ Creates a SimpleFocusListWalker using contents as the list,
            adds a centered title, and draws a box around it. If the contents
            are not a list of widgets, then set content_list to False.
            
            The character that is used to draw the border can 
            be adjusted with the following keyword arguments:
                tlcorner,tline,trcorner,blcorner,rline,bline,brcorner
        
        Arguments:
            contents {widget} -- an original_widget, no widget lists -
            title {string} -- Title String
        
        Keyword Arguments:
            content_list -- If true, the value of contents must be a list of widgets
                            If false, the value must be a single widget to be used as
                            original_widget -- default{False}
        
        Returns:
            urwid.LineBox -- urwid.LineBox object
            FLOW / BOX WIDGET
        """
        return urwid.LineBox(contents, title=str(title), title_align='center')
    def getListBox(self,contents):
        """Creates a ListBox using a SimpleFocusListWalker, with the contents
           being a list of widgets
        
        Arguments:
            contents {list} -- list of widgets
        
        Returns:
            list -- [0]: urwid.ListBox
                    [1]: urwid.SimpleFocusListWalker - Access this to make changes to the list
                               which the SimpleFocusListWalker will follow.   
        BOX WIDGET 
        """
        #debug('Started getListBox: %s', contents)
        walker = urwid.SimpleFocusListWalker(contents)
        listBox = urwid.ListBox(walker)
        return [listBox, walker]
    def getCheckBox(self,label,on_state_change=None,user_data=None):
        """gets an individual CheckBox item that executes the specified function 
            with each change of state.
        
        Arguments:
            label {str} -- Checkbox item label
        
        Keyword Arguments:
            on_state_change {list} -- a list of the following [calling object, function] (default: {None})
            user_data {list} -- list of values to be bassed to function as arguments (default: {None})
        
        Returns:
            object -- urwid.CheckBox object
            FLOW WIDGET
        """
        return urwid.CheckBox(label, 
        state=False, 
        has_mixed=False, 
        on_state_change=getattr(on_state_change[0],on_state_change[1]), 
        user_data=user_data)
    def centeredListLineBox(self,contents, title, listHeight, **kwargs):
        filler = urwid.Filler(contents, height=listHeight)
        insideCol = w.getColRow([w.blankBox,('weight',2,filler),w.blankBox])
        #debug('centeredListLineBox filler.sizing(): %s', filler.sizing())
        lineBox = w.getLineBox(insideCol,title)
        #debug('centeredListLineBox listBox: %s', contents)
        outsidefiller = urwid.Filler(lineBox,height=listHeight)
        outsideCol = w.getColRow([w.blankBox,('weight',2,outsidefiller),w.blankBox])
        return urwid.Filler(outsideCol, height=listHeight)
    def getHeaderWidget(self,title=s.df.mainTitle,subtitle=''):
        """Generates a basic header with a title and optional subtitle
           This is meant to be used exclusively by the Headers.new() method
        
        Arguments:
            title {str} -- Title String
        
        Keyword Arguments:
            subtitle {str} -- Optional Sub-Title (default: {''})
        
        Returns:
            object -- urwid.Pile object to be used as the header's widget 
            FLOW WIDGET
        """
        self.title = self.getText('bold',title,'center')
        self.subtitle = self.getText('bold',subtitle,'center')
        titleMap = urwid.AttrMap(self.title, 'bold')
        divMap = urwid.AttrMap(self.div, 'body')
        if subtitle:
            subtitleMap = urwid.AttrMap(self.subtitle, 'bold')
            return urwid.Pile((titleMap, subtitleMap, divMap), focus_item=None)
        else:
            return urwid.Pile((titleMap, divMap), focus_item=None)
    def getFooterWidget(self,view_instance, menuItems):
        """Generates a footer column row containing a list of buttons for a
            basic menu / navigation. This is meant to be used exclusively by
            the Footers.new() method
        
        Arguments:
            menuItems {list} -- List of Menu Items (each item is a list) 
                                in the following format:
                                [
                                    [Label,callback function]
                                    [Label,callback function]
                                ]       
        Returns:
            object -- urwid.menuItems object to be used as the header's widget
            FLOW WIDGET
        """
        menuList = []
        for item in menuItems:
            if len(item) == 3:
                menuList.append(
                    w.getButton(item[0],views,'activate',user_data=(item[1],item[2])))
            else:
                menuList.append(
                    w.getButton(item[0],views, 'activate', user_data=item[1]))
        return urwid.Columns(
            menuList,
            dividechars=1,
            focus_column=None,
            min_width=1, 
            box_columns=None)
class BodyWidgets():
    def get_body_widget(self, view_name, user_args=None, calling_view=None):
        #debug('BodyWidgets.get_body_widget:: view_name: %s :: args: %s', view_name, args)
        widget_getter = getattr(self, 'get_' + view_name)
        return widget_getter(user_args=user_args, calling_view=calling_view)
    def get_choose_logs(self, **kwargs):
        """Page opened on application start to select the 
           logs that will be used in searches / filters
        """
        debug(' kwargs: %s', kwargs)
        logCheckBoxes = [w.div]
        for log in logFiles.availableLogs:
            logCheckBoxes.append(
                w.getCheckBox(log,
                    on_state_change=[logFiles,'update'], 
                    user_data=[log])
                    )
        logCheckBoxes.append(w.div)
        logCheckBoxes.append(w.getButton('Continue', views, 'activate', user_data='home'))
        listBox = w.getListBox(logCheckBoxes)[0]
        chooseLogsBox = w.centeredListLineBox(
            listBox, 
            'Choose Your Logs to Search',
            len(logCheckBoxes) + 3)
        return chooseLogsBox
    def get_home(self, **kwargs):
        """Page displayed as Home Page for the application
        """
        debug(' kwargs : %s', kwargs)
        homeText = w.getText('body', 'Welcome to the best Exim Search Utility ever created.\nSelect an option below to begin.','center')
        if not s.lf.selectedLogs:
            debug(' No logs selected, returning to choose_logs ')
            return self.get_choose_logs()
        else:
            return urwid.Filler(homeText, 'middle')
    def get_new_search(self, **kwargs):
        """Page opened when starting an entirely new
           search. Not used for revising or filtering 
           previous searches
        """
        debug(' kwargs : %s', kwargs)
        selectQuery = urwid.Edit('Enter your query below\n',align='center')
        selectFiller = QuestionBox(selectQuery, 'middle')
        return w.centeredListLineBox(selectFiller, 'New Search Query', 5)
    def get_search_progress(self, **kwargs):
        debug(' kwargs : %s', kwargs)
        searchingStatus = urwid.Pile([
            w.getText('body', 'Searching Logs Now. Please wait....', 'center'),
            w.searchProgress
            ])
        statusFiller = urwid.Filler(searchingStatus, 'middle')
        return w.centeredListLineBox(statusFiller, '',10)
    def get_results_summary(self, **kwargs):
        debug(' kwargs : %s', kwargs)
        query = state.get_query(ACTIVE)
        result_list = kwargs['user_args']
        if s.rl.resultOverflow:
            if state.get_query:
                summaryRows = [w.getText('header', ' for ' + query, 'center')]
            else:
                summaryRows = []
            summaryRows.extend([
                w.div,
                w.getText('bold',' There are too many Results \n Only showing the first ' 
                    + str(result_list.count) + 
                    ' Results \nConsider applying filters to narrow down results ', 'center'),
                w.div
            ])
            s.rl.resultOverflow = False
        else:
            if query:
                summaryRows = [w.getText('header', ' for ' + query, 'center')]
            else:
                summaryRows = []
            summaryRows = [
                w.div,
                w.getText('bold','There are ' + str(result_list.count) + ' results', 'center'),
                w.div
            ]
        activeFilters = state.get_active_filters()
        if activeFilters:
            summaryRows.append(w.getText('bold', 'Currently Active Filters:', 'center'))
            for activeFilter in activeFilters:
                summaryRows.append(w.getText('body', activeFilter, 'center'))
        summaryRows.append(w.div)
        summaryRows.append(w.getButton('Show Results', views,'activate', user_data='results_list'))
        summary = urwid.SimpleFocusListWalker(summaryRows)
        summaryList = urwid.ListBox(summary)
        return w.centeredListLineBox(summaryList, 'Search Results', len(summaryRows) + 5)
    def get_results_list(self, **kwargs):
        debug(' kwargs : %s', kwargs)
        result_list = state.get_result_list(ACTIVE)
        calling_view = kwargs['calling_view']
        x = 1
        listDisplayCols = []
        for result in result_list.contents:
            listDisplayCols.append(w.getColRow(
                [
                    (5, w.getButton(
                        str(x),
                        views,
                        'activate',
                        user_data=['single_entry', 
                            result_list.contents.index(result), 
                            result_list])),
                    w.getText('body',result,'left')
                ]
            ))
            x += 1
        resultListWalker = urwid.SimpleFocusListWalker(listDisplayCols)
        resultListBox = urwid.ListBox(resultListWalker)
        #resultListFiller = urwid.Filler(resultListBox)
        return resultListBox
    def get_add_remove_filters(self, **kwargs):
        debug(' kwargs : %s', kwargs)
    def get_clear_applied_filters(self, **kwargs):
        debug(' kwargs : %s', kwargs)
    def get_quit_loop(self, **kwargs):
        """Page opened upon a request to quit, and 
            asks for confirmation of quiting
        """
        debug(' kwargs : %s', kwargs)
        if state.get_view(ACTIVE) == 'choose_logs':
            noButton = w.getButton('No', views, 'choose_logs')
        else:
            noButton = w.getButton('No', views, 'exit')
        quitList = [
            w.div,
            w.getColRow([
                w.getButton('Yes', views, 'exit'),
                noButton]),
            w.div]
        quitBox = w.getListBox(quitList)[0]
        return w.centeredListLineBox(
            quitBox, 
            'Are You Sure You Want to Quit?',
            len(quitList) + 2)
    def get_coming_soon(self, **kwargs):
        debug(' kwargs : %s', kwargs)
    def get_single_entry(self, **kwargs):
        debug(' kwargs : %s', kwargs)
        entryNo = kwargs['user_args'][0]
        result_list = kwargs['user_args'][1]
        single_entry = getattr(result_list,'entry-' + str(entryNo))
        state.set_entry_on_screen(single_entry)
        entry_fields = single_entry.get_entry_fields()
        entry_fields.sort()
        entry_field_col_rows = [w.div]
        for field in entry_fields:
            entry_field_col_rows.append(w.getColRow([
                (30,w.getButton(field[2],search,'new',user_data=field[3], buttonMap='body')),
                ('weight',4,w.getText('body', field[3], 'left'))
            ]))
        entry_walker = urwid.SimpleFocusListWalker(entry_field_col_rows)
        return urwid.ListBox(entry_walker)
        #singleEntryFiller = urwid.Filler(singleEntryList)
        #s.menus.single_entry[2] = [
        #    '(B)ack To Result List',
        #    'resultList'
        #    ]
        #footers.update('singleEntryMenu', s.df.singleEntryMenu)
        #self.show(footers.singleEntryMenu, frame, 'footer')
        #self.show(singleEntryList,frame,'body')
w = MyWidgets()

"""
STATE MANAGEMENT / TRACKING
"""
class State():
    def __init__(self):
        self.active_view = None
        self.previous_view = None
        self.active_result_list = None
        self.previous_result_list = None
        self.active_query = None
        self.previous_query = None
        self.active_filters = None
        self.active_entry_on_screen = None
        self.prev_entry_on_screen = None
        self.searchCounter = 1
    def increment_counter(self):
        self.searchCounter += 1
    def get_new_search_number(self):
        searchCounterStr = 'search' + str(self.searchCounter).zfill(3)
        self.searchCounter += 1
        return searchCounterStr
    def set_view(self, view):
        debug('State.set_view: %s', view.view_name)
        #assign current view to previous view and store view as active_view
        if self.active_view:
            self.prev_view = self.active_view
        else:
            self.prev_view = None
        self.active_view = view

        #store view names in easily accessible attributes

        self.active_view_name = self.active_view.view_name
        if self.prev_view:
            self.prev_view_name = self.prev_view.view_name
        else:
            self.prev_view_name = None

        #store status of active and prev view as to whether or not it was a result list or single entry
        self.is_active_view_result_list = self.active_view.is_view_result_list
        self.is_active_view_single_entry = self.active_view.is_view_single_entry
        self.is_active_view_add_filters = self.active_view.is_view_add_filters
        if self.prev_view:
            self.is_prev_view_result_list = self.prev_view.is_view_result_list
            self.is_prev_view__single_entry = self.prev_view.is_view_single_entry
            self.is_prev_view__add_filters = self.prev_view.is_view_add_filters
    def get_view(self, active_prev):
        #debug('State.get_view: %s', active_prev)
        if active_prev == 'active':
            return self.active_view
        if active_prev == 'prev':
            return self.prev_view
        else:
            warning('State.get_view() active_prev parameter is invalid.')
            sys.exit('State.get_view() active_prev parameter is invalid.')
    def get_view_name(self,active_prev):
        #debug('State.get_view_name: %s', active_prev)
        if active_prev == 'active':
            return self.active_view.view_name
        if active_prev == 'prev':
            return self.prev_view.view_name
        else:
            warning('State.get_view_name() active_prev parameter is invalid.')
            sys.exit('State.get_view_name() active_prev parameter is invalid.')
    def set_result_list(self,result_list):
        debug('State.set_result_list: %s', result_list)
        #assign current result_list to previous result_list and store result_list as active_result_list
        if self.active_result_list:
            self.prev_result_list = self.active_result_list
        else:
            self.prev_result_list = None
        self.active_result_list = result_list

        #store result_list names in easily accessible attributes
        self.active_result_list_name = self.active_result_list.listNumber
        if self.prev_result_list:
            self.prev_result_list_name = self.prev_result_list.listNumber
        else:
            self.prev_result_list_name = None
        #store status of result_list as filtered or not.
        self.is_active_result_list_filtered = self.active_result_list.is_filtered
        if self.prev_result_list:
            self.is_prev_result_list_filtered = self.prev_result_list.is_filtered
        else:
            self.prev_result_list_filtered = None
    def get_result_list(self,active_prev):
        #debug('State.get_result_list: %s', active_prev)
        if active_prev == 'active':
            return self.active_result_list
        if active_prev == 'prev':
            return self.prev_result_list
        else:
            warning('State.get_result_list() active_prev parameter is invalid.')
            sys.exit('State.get_result_list() active_prev parameter is invalid.')
    def get_result_list_name(self,active_prev):
        #debug('State.get_result_list_name: %s', active_prev)
        if active_prev == 'active':
            return self.active_result_list.list_name
        if active_prev == 'prev':
            return self.prev_result_list.list_name
        else:
            warning('State.get_result_list_name() active_prev parameter is invalid.')
            sys.exit('State.get_result_list_name() active_prev parameter is invalid.')
    def set_query(self,query):
        debug('State.set_query: %s', query)
        self.prev_query = self.active_query
        self.active_query = query
    def get_query(self, active_prev):
        #debug('State.get_query: %s', active_prev)
        if active_prev == 'active':
            return self.active_query
        if active_prev == 'prev':
            return self.prev_query
        else:
            warning('State.get_query() active_prev parameter is invalid.')
            sys.exit('State.get_query() active_prev parameter is invalid.')

    def set_active_filters(self, active_filters):
        debug('State.set_active_filters: %s', active_filters)
        self.active_filters = active_filters
    def get_active_filters(self):
        debug('State.get_active_filters: %s', self.active_filters)
        return self.active_filters

    def set_entry_on_screen(self,entry_on_screen):
        debug('State.set_entry_on_screen: %s', entry_on_screen)
        self.prev_entry_on_screen = self.active_entry_on_screen
        self.active_entry_on_screen = entry_on_screen
    def get_entry_on_screen(self,active_prev):
        debug('State.get_entry_on_scareen: %s', active_prev)
        if active_prev == 'active':
            return self.active_entry_on_screen
        if active_prev == 'prev':
            return self.prev_entry_on_screen
        else:
            warning('State.entry_on_screen() active_prev parameter is invalid.')
            sys.exit('State.entry_on_screen() active_prev parameter is invalid.')
    def get_entry_on_screen_name(self,active_prev):
        debug('State.get_entry_on_screen_name: %s', active_prev)
        if active_prev == 'active':
            return self.active_entry_on_screen.entry_name
        if active_prev == 'prev':
            return self.prev_entry_on_screen.entry_name
        else:
            warning('State.entry_on_screen() active_prev parameter is invalid.')
            sys.exit('State.entry_on_screen() active_prev parameter is invalid.')
class View():
    def __init__(self, view_name,
        default_view_focus,
        header_title=s.df.mainTitle,
        header_subtitle=s.df.mainSubTitle,
        is_view_result_list=False,
        is_view_single_entry=False,
        is_view_add_filters=False):
        self.default_view_focus = default_view_focus
        self.view_name = view_name
        self.header_title = header_title
        self.header_subtitle = header_subtitle
        self.is_view_result_list = is_view_result_list
        self.is_view_single_entry = is_view_single_entry
        self.is_view_add_filters = is_view_add_filters
    def start(self, previous_view, focus_position=None, user_args=None):
        debug('view.start view_name: %s', self.view_name)
        self.header = w.getHeaderWidget(self.header_title,subtitle=self.header_subtitle)
        self.previous_view = previous_view
        menuItems = getattr(s.menus,self.view_name)
        self.footer = w.getFooterWidget(self, menuItems)
        self.body = body.get_body_widget(self.view_name, user_args=user_args, calling_view=self)
        self.show_header()
        self.show_body()
        self.show_footer()
        if focus_position:
            frame.focus_position = focus_position
        else:
            frame.focus_position = self.default_view_focus
        state.set_view(self)
    def show_header(self):
        frame.contents.__setitem__('header', [self.header, None])
    def show_body(self):
        frame.contents.__setitem__('body', [self.body, None])
    def show_footer(self):
        frame.contents.__setitem__('footer', [self.footer, None])
    def draw_screen(self,loop):
        loop.draw_screen()
    def set_focus(self,target_frame, focus_position):
        target_frame.focus_position = focus_position
class ViewSets():
    def __init__(self):
        self.quit_loop = View('quit_loop', BODY)
        self.choose_logs = View('choose_logs',BODY)
        self.home = View('home',FOOTER)
        self.new_search = View('new_search', BODY)
        self.search_progress = View('search_progress', BODY)
        self.results_summary = View('results_summary', BODY)
        self.results_list = View('results_list', BODY, is_view_result_list=True)
        self.add_remove_filters = View('add_remove_filters', BODY, is_view_add_filters=True)
        self.apply_current_filters = View('apply_current_filters',BODY)
        self.clear_applied_filters = View('clear_applied_filters', BODY)
        self.coming_soon = View('coming_soon', FOOTER)
        self.single_entry = View('single_entry', BODY, is_view_single_entry=True)
    def get_view(self, view_name):
        return getattr(self,view_name)
    def activate(self,view_name,
        focus_position=None, user_args=[], 
        is_threaded=False,on_join=None):
        debug('views.activate args: %s', view_name)
        current_view = state.get_view(ACTIVE)
        if type(view_name) == list:
            activating_view = getattr(views, view_name[0])
            passed_args = view_name[1:]
        else:
            activating_view = getattr(views, view_name)
            passed_args = user_args
        if is_threaded:
            debug('view.activate is threaded')
            updateThread = threading.Thread(
                target=activating_view.start(current_view,
                    focus_position=focus_position, 
                    user_args=passed_args))
            updateThread.start()
            updateThread.join()
            on_join()
        else:
            activating_view.start(current_view,focus_position=focus_position, user_args=passed_args)
    def exit(self):
        debug
        raise urwid.ExitMainLoop()
state = State()

"""
LOG CLASSES
"""
class LogFiles():
    def __init__(self):
        """This Class handles obtaining and updating
           lists of log files including the currently
           available logs, and the logss currently 
           selected for searching.
        """
        self.availableLogs = self.getListofAvailableLogs()
        self.sortLogs(self.availableLogs)
    def sortLogs(self, logsToBeSorted):
        """Sorts list of log files with the primary file first
            and the gzipped files next, sorted by date in decending
            order.
        
        Arguments:
            logsToBeSorted {list} -- the logfile list that will be sorted
        """
        logsToBeSorted.sort(reverse=True)
        for log in logsToBeSorted:
            if log == s.lf.mainLogPath:
                logsToBeSorted.insert(0, logsToBeSorted.pop(logsToBeSorted.index(s.lf.mainLogPath)))
    def update(self, *args):
        """updates an item in the selectedLogs list by either adding or removing the item
        
        Arguments:
            itemsToUpdate {list} -- list of items to update. if only updating one item, it must still be contained in a list
        
        Raises:
            TypeError: raised if itemsToUpdate is not a list
        
        Returns:
            dict -- Dictionary of items added or removed in this call.
        """
        #debug('LogFiles update args: %s', type(args[0]))
        updates = {'removed':[],'added':[]}
        if type(args[0]) == urwid.wimp.CheckBox:
            itemsToUpdate = args[2]
            isLogSelected = args[1]
            
            if type(itemsToUpdate) != list:
                raise TypeError('{} provided where list is required', type(itemsToUpdate))   
            if isLogSelected:
                for x in itemsToUpdate:
                    if x not in s.lf.selectedLogs:
                        updates['added'].append(x)
                        s.lf.selectedLogs.append(x)
                        #debug('LogFiles update self.selectedLogs after append: %s', s.lf.selectedLogs)
                        self.sortLogs(s.lf.selectedLogs)
                    else:
                        warning('LogFiles.update: Failed to add log %s : Log already on selectedLogs list', x)
            else:
                for x in itemsToUpdate:
                    if x in s.lf.selectedLogs:
                        updates['removed'].append(x)
                        s.lf.selectedLogs.remove(x)
                        #debug('LogFiles update self.selectedLogs after remove: %s', s.lf.selectedLogs)
                        self.sortLogs(s.lf.selectedLogs)
                    else:
                        warning('LogFiles.update: Failed to remove log %s : Log is not on selectedLogs list', x)
        return updates
    def getListofAvailableLogs(self):
        """Obtains list of log files available in the 
           directory set in LogFileSettings.dir
        Returns:
            list -- list of available log files
        """
        logdir = s.lf.dir
        loglist = []
        for file in os.listdir(logdir):
            if file.startswith("exim_mainlog"):
                loglist.append(os.path.join(logdir, file))
        return loglist


"""
DATA PROCESSING / SEARCH AND RESULT CLASSES
"""
class Search():
    def new(self, *args):
        s.rl.resultOverflow = False
        if args:
            debug('Search Has special arguments: %s', args)
        debug('New Search Object with query: %s', state.get_query(ACTIVE))
        searchNumber = state.get_new_search_number()
        results.new(
            searchNumber,
            'logResults',
            self.filter_logs(),
            original_results=searchNumber
            )
        result_list = results.get_result_list(searchNumber)
        views.activate('results_summary',focus_position=BODY,user_args=result_list)
        #views.show(views.newSearchSummary(searchNumber,query), frame, 'body')
    def filter_results(self,*args):
        global mostRecentSearchNo
        debug("Start Search.filterResults: %s", filters.get())
        currentSearchNo = 'search' + str(searchCounter - 1).zfill(3)
        filteredSearchNo = self.incrementCounter()
        mostRecentSearchNo = filteredSearchNo
        currentResultList = results.getRawResultList(currentSearchNo)
        self.currentFilters = filters.get()
        filteredResults = []
        originalQuery = currentResultList.query
        #originalInput = currentResultList
        entryList = currentResultList.getListOfEntries()
        entryList.sort()
        debug('filterResults entryList: %s', entryList)
        filteredResults = self.filterInput('sendAddr', input=entryList)
        filteredResults = self.filterInput('recipient', input=filteredResults)
        filteredResults = self.filterInput('date', input=filteredResults)
        filteredResults = self.filterInput('msgType', input=filteredResults)
        debug("Filtered Results Count: %s", len(filteredResults))
        if currentResultList.isFiltered:
            original_results = currentResultList.original_results
        else:
            original_results = currentSearchNo
        results.new(filteredSearchNo, 'filteredResults', originalQuery, filteredResults, original_results=original_results, isFiltered=True)
        views.show(views.newSearchSummary(filteredSearchNo,originalQuery), frame, 'body')
    def filter_input(self, filterType, input=None):
        if not self.currentFilters[filterType]:
            return input
        else:
            filteredResults = []
            filterSet = self.currentFilters[filterType]
            #debug('filterInput filters: %s', filterSet)
            for item in input[:]:
                x = getattr(item,filterType)
                #debug('filterInput x.filterType: %s', x)
                for filters in filterSet:
                    for filter in filters:
                        #debug('filterInput filter: %s', filter)
                        if filter in x:
                            filteredResults.append(item)
            return filteredResults
    def filter_logs(self):
        starttime = datetime.now()
        #debug(":filterLogs :: Current Thread:: %s", threading.current_thread().getName())
        #debug('filterLogs filter: %s', query)
        #for log in self.selectedLogs:
        logPoolArgs = []
        query = state.get_query(ACTIVE)
        for log in s.lf.selectedLogs:
            logPoolArgs.append([query,log])
        queryLogProcessPool = ThreadPool()
        searchedLogs = queryLogProcessPool.map(queryLogProcess, logPoolArgs)
        results = []
        for resultList in searchedLogs:
            results.extend(resultList)
        logging.info('QT = %s : filteredLog Pool Result Count: %s',datetime.now() - starttime, len(results))
        return results

class Results():
    def __init__(self):
        self.currentFilters = {
            'Type': [],
            'Sender': [],
            'Recipient': [],
            'Date': [],
        }
        self.entries = {}
        self.filterEntryEditText = ''
    def new(self, name, resultType,
        resultContents, original_results='',
        isFiltered=False,filters_applied=[]):
        """Class of Result Lists
        
        Arguments:
            name {str} -- name of this result instance
            resultType {str} -- the origin source of this result list (logResults,FilteredResults, etc)
            resultContents {list} -- a list of results. each list item must be str
        
        Raises:
            TypeError: raised if resultContents is not a list
            TypeError: raised if the first item in resultContents is not a str
        """
        debug('New Result List created: %s', name)
        if resultType == 'logResults':
            if type(resultContents) != list:
                raise TypeError('{} provided :: resultContents must be a list of strings'.format(type(resultContents)))
            try:
                type(resultContents[0])
            except:
                pass
            else:
                if type(resultContents[0]) != str:
                    raise TypeError('{} provided :: resultContents must be a list of strings'.format(type(resultContents[0])))
            count = len(resultContents)
            if hasattr(self, name):
                raise Exception('A result list by the name of {} already exists'.format(name))
            else:
                setattr(self,name,ResultLists(
                    name, resultType,
                    resultContents, count,
                    original_results,
                    isFiltered, filters_applied))
                state.set_result_list(getattr(self,name))
        else:
            count = len(resultContents)
            setattr(self,name,ResultLists(
                name, resultType,
                resultContents, count,
                original_results,
                isFiltered, filters_applied))
            state.set_result_list(resultContents)
    def get_single_entry(self,entryNo,searchNo):
        debug('Started Results.getSingleEntry: %s, %s', entryNo, searchNo)
        entryId = 'entry-' + str(entryNo)
        resultList = getattr(self, searchNo)
        debug('resultList : %s', resultList)
        entry = getattr(resultList, entryId)
        return entry.getEntryFields()
    def get_active_filter_strings(self):
        activeFilterStringList = []
        for filterType, activeFilter in self.currentFilters.items():
            if activeFilter:
                activeFilterStringList.append('Message ' + filterType + ' = ' + ', '.join(activeFilter))
        return activeFilterStringList
    def get_count(self,searchNo):
        resultList = getattr(self,searchNo)
        return resultList.count
    def get_result_list(self, searchNo):
        return getattr(self,searchNo)
    def check_for_add_filter_entry(self, *args):
        debug('Results.checkForAddFilterEntry args: %s', args)
        #if self.filterEntryEditText:
        #    newFilter = self.filterEntryEditText
        #    self.filterEntryEditText = ''
        #    self.currentFilters[filterType].append(newFilter)
    def add_filters(self, *args):
        debug('Results.addFilters args: %s', args)
class ResultLists():
    def __init__(self,
        listNumber,resultType,resultContents,
        count,original_results='',
        isFiltered=False, filters_applied=[]):
        self.listNumber = listNumber
        self.is_filtered = isFiltered
        self.query = state.get_query(ACTIVE)
        self.original_results = original_results
        self.filteredApplied = filters_applied
        self.count = count
        if resultType == 'logResults':
            self.contents = resultContents
            self.parseEntries()
        else:
            resultContents.sort(key=lambda x: str(x.getTimeOrd()), reverse=False)
            i = 0
            self.contents = []
            for entry in resultContents:
                name = 'entry-' + str(i)
                setattr(self,name,entry)
                self.contents.append(entry.fullEntryText[2])
                i += 1
        #debug('List of Attr in new ResultList: %s', dir(self))
    def parseEntries(self):
        i = 0
        for result in self.contents:
            name = 'entry-' + str(i)
            if hasattr(self, name):
                raise Exception('Entry number {} has already been parsed'.format(name))
            else:
                setattr(self,name,Entries(result))
            i += 1
    def getListOfEntries(self):
        listOfEntries = []
        for attr in dir(self):
            if 'entry-' in attr:
                listOfEntries.append(getattr(self,attr))
        return listOfEntries
class Entries():
    def __init__(self, fullEntryText):
        """This class is used to create single-view Entry Objects
        """
        self.msgType = []
        self.date = []
        self.time = []
        self.sendAddr = []
        self.recipient = []
        self.fullEntryText = fullEntryText
        #debug('Init Entries: %s', self.fullEntryText)
        try:
            shlex.split(self.fullEntryText)
        except:
            m = self.fullEntryText.split()
            self.parseError = [15, 'Parsing Error: ', str(Exception)]
            x = 0
            while x <= len(m):
                if x == 0:
                    self.date = [10, 'Date: ', m[x]]
                if x == 1:
                    self.time = [11, 'Time: ', m[x]]
                if x == 2:
                    self.pid = [12, 'Process ID: ', m[x]]
                if x == 3:
                    self.id = [13, 'Message ID: ', m[x]]
                x += 1
            self.fullEntryText = [14, 'Full Entry: ', self.fullEntryText]        
        else:
            m = shlex.split(self.fullEntryText)
            x = 0
            while x < len(m):
                if x == 0:
                    self.date = [10, 'Date: ', m[x]]
                if x == 1:
                    self.time = [11, 'Time: ', m[x]]
                if x == 2:
                    self.pid = [12, 'Process ID: ', m[x]]
                if x == 3:
                    self.id = [13, 'Message ID: ', m[x]]
                if x == 4:
                    if len(m[x]) == 2:
                        self.entryType = [22, 'Entry Type Symbol: ', m[x]]
                #debug('parseEntries self.fullEntryText: %s', self.fullEntryText)
                if 'H=' in m[x]:
                    if len(m) > x + 1:
                        if m[x+1][0] == '(':
                            self.host = [16,'Host: ', m[x][2:] + ' ' + m[x+1]]
                            self.hostIp = [17, 'Host IP: ', m[x+2].split(':')[0]]
                            if s.hostname in self.host:
                                self.msgType = [15, 'Type: ', 'relay']
                        else:
                            self.host = [16, 'Host: ', m[x][2:]]
                            self.hostIp = [17, 'Host IP: ', m[x+1].split(':')[0]]
                            if s.hostname in self.host:
                                self.msgType = [15, 'Type: ', 'relay']
                if m[x] == 'SMTP':
                    self.smtpError = [22, 'Failure Message: ', " ".join(m[x:])]
                if 'S=' in m[x] and m[x][0] != 'M':
                    self.size = [22, 'Size: ', m[x][2:]]
                if 'I=' in m[x] and m[x][0] != 'S':
                    self.interface = [22, 'Receiving Interface: ', m[x].split(':')[0][2:]]
                if 'R=' in m[x]:
                    self.bounceId = [22, 'Bounce ID: ', m[x][2:]]
                if 'U=' in m[x]:
                    self.mta = [22, 'MTA / User: ', m[x][2:]]
                if 'id=' in m[x]:
                    self.remoteId = [22, 'Sending Server Message ID: ', m[x][3:]]
                if 'F=<' in m[x]:
                    self.sendAddr = [18, 'Sender: ', m[x][2:]]
                    if not self.sendAddr[1] == '<>':
                        self.sendAddr = [18, 'Sender: ', m[x][3:-1]]
                    self.fr = self.sendAddr
                if 'C=' in m[x]:
                    self.delStatus = [22, 'Delivery Status: ', m[x][2:]]
                if 'QT=' in m[x]:
                    self.timeInQueue = [22, 'Time Spent in Queue: ', m[x][3:]]
                if 'DT=' in m[x]:
                    self.deliveryTime = [22, 'Time Spent being Delivered: ', m[x][3:]]
                if 'RT=' in m[x]:
                    self.deliveryTime = [22, 'Time Spent being Delivered: ', m[x][3:]]
                if ' <= ' in fullEntryText:
                    self.msgType = [15, 'Message Type: ', 'incoming']
                    if 'A=' in m[x]:
                        self.smtpAuth = [22, 'Auth. Method: ', m[x][2:]]
                        if 'dovecot' in m[x]:
                            self.msgType = [15, 'Type: ', 'relay']
                    if x == 5:
                        self.sendAddr = [18, 'Sender', m[x]]
                    if 'P=' in m[x]:
                        self.protocol = [22, 'Protocol: ', m[x][2:]]
                        if 'local' in self.protocol[1]:
                            self.msgtype = [15, 'Type: ', 'local']
                    if 'T=' in m[x] and m[x][0] != 'R':
                        self.topic = [21, 'Subject: ', m[x][2:]]
                    if m[x] == 'from':
                        if len(m) > x +1:
                            if m[x+1] == '<>':
                                self.fr = [18, 'Sender: ', m[x+1]]
                                self.msgType = [15, 'Type: ', 'bounce']
                            else:
                                self.fr = [18, 'Sender: ', m[x+1][1:-1]]
                    if m[x] == 'for':
                        self.receipient = [19, 'Recipient: ', m[x+1]]
                    x += 1
                else:
                    if x == 5:
                        if '@' in m[x]:
                            self.receipient = [19, 'Recipient: ', m[x]]
                        else:
                            if len(m) > x + 1:
                                if '@' in m[x + 1]:
                                    self.receipient = [19, 'Recipient: ', m[x] + m[x+1]]
                    if 'P=' in m[x]:
                        self.returnPath = [20, 'Return Path: ', m[x][3:-1]]
                    if 'T=' in m[x] and m[x][0] != 'D' and m[x][0] != 'Q':
                        self.mta = [22, 'MTA: ', m[x][2:]]
                        if 'dovecot' in self.mta[1]:
                            self.msgType = [15, 'Type: ', 'local']
                    if ' => ' in fullEntryText:
                        self.msgType = [15, 'Message Type: ', 'outgoing']
                    x += 1
            
            self.fullEntryText = [14, 'Full Entry: ', self.fullEntryText]
    def getTimeOrd(self):
        x = str(self.date[2]) + '_' + str(self.time[2])
        x = datetime.strptime(x, s.dt.logDateTimeFormat)
        return x.toordinal()
    def get_entry_fields(self):

        fieldList = [a for a in dir(self) if not a.startswith('__') and not callable(getattr(self,a))]
        fields = []
        for field in fieldList:
            x = getattr(self,field)
            if x:
                fields.append([
                    x[0],
                    field,
                    x[1],
                    x[2]
                ])
        return fields
class Testing():
    def set_get_views(self):
        state.set_view(View('Test A', 'Test A Header', 'Test A Header', 'Test A Body'))
        current_view = state.get_view('active')
        debug('Current View: %s', current_view)
        current_view_name = state.get_view_name('active')
        debug('Current View Name: %s', current_view_name)
        state.set_view(View('Test B', 'Test B Header', 'Test B Header', 'Test B Body'))
        current_view = state.get_view('active')
        current_view_name = state.get_view_name('active')
        prev_view = state.get_view('prev')
        prev_view_name = state.get_view_name('prev')
        debug('Current View: %s', current_view)
        debug('Current View Name: %s', current_view_name)
        debug('Previous View: %s', prev_view)
        debug('Previous View Name: %s', prev_view_name)
    def set_get_result_lists(self):
        state.set_result_list(ResultList('Test List A', ['entry1','entry2','entry3','entry4']))
        current_result_list = state.get_result_list('active')
        current_result_list_name = state.get_result_list_name('active')
        debug('\nCurrent Result List Name: %s', current_result_list_name)
        debug('Current Result LIst: %s\n', current_result_list)
        state.set_result_list(ResultList('Test List B', ['entry5','entry6','entry7','entry8']))
        current_result_list = state.get_result_list('active')
        current_result_list_name = state.get_result_list_name('active')
        prev_result_list = state.get_result_list('prev')
        prev_result_list_name = state.get_result_list_name('prev')
        debug('Current result list: %s', current_result_list)
        debug('Current result List Name: %s', current_result_list_name)
        debug('Previous result list: %s', prev_result_list)
        debug('Previous result list Name: %s', prev_result_list_name)
    def set_get_query(self):
        state.set_query('Test Query 1')
        current_query = state.get_query('active')
        debug('Current Query:: %s', current_query)
        state.set_query('Test Query 2')
        current_query = state.get_query('active')
        prev_query = state.get_query('prev')
        debug('Current Query:: %s', current_query)
        debug('Previous Query:: %s', prev_query)
    def set_get_active_filters(self):
        state.set_active_filters('Test Filters 1')
        current_filters = state.get_active_filters()
        debug('Current filters:: %s', current_filters)

def queryLogProcess(poolArgs):
    os.nice(20)
    query,log = poolArgs
    #debug('Log = %s, filters = %s', log, query)
    rawEntries = []
    if log[-2:] != 'gz':
        with open(log,mode='r') as f:
            for i, line in enumerate(f):
                pass
            #debug('Lines in file: %s', i)
            totalLines = i
        
        #logPoolArgs = []
        with open(log,mode='r') as p:
            for i, line in enumerate(p):
                if len(rawEntries) == 10000:
                    s.rl.resultOverflow = True
                    debug('ResultOverflow = True')
                    break
                if query in line:
                    if line not in rawEntries:
                        rawEntries.append(line)
                if i % 1000000 == 0:
                    percent = float(i) / float(totalLines)
                    completion = int(percent * 100)
                    #debug('Total Lines in file: %s', totalLines)
                    #debug('Current Line Percent: %s', completion)
                    w.searchProgress.set_completion(completion)
                    loop.draw_screen()
    else:
        with gzip.open(log,mode='r') as f:
            for i, line in enumerate(f):
                pass
            #debug('Lines in file: %s', i)
            totalLines = i
        with gzip.open(log,mode='r') as f:
            for i, line in enumerate(f):
                if len(rawEntries) == 10000:
                    s.rl.resultOverflow = True
                    debug('ResultOverflow = True')
                    break
                if query in line:
                    if line not in rawEntries:
                        rawEntries.append(line)
                if i % 1000000 == 0:
                    percent = float(i) / float(totalLines)
                    completion = int(percent * 100)
                    #debug('Total Lines in file: %s', totalLines)
                    #debug('Current Line Percent: %s', completion)
                    w.searchProgress.set_completion(completion)
                    loop.draw_screen()
    return rawEntries

s = GlobalSettings()
if __name__ == '__main__':
    debug("\n****\nApplication Start!\n****\n")
    #Initialize LogFiles
    logFiles = LogFiles()
    
    #Initiatlize Views and BodyWidgets
    views = ViewSets()
    body = BodyWidgets()

    #Initialize Results and Search Container Objects
    results = Results()
    search = Search()

    #Initialize Frame Widget
    frame = urwid.Frame(urwid.Filler(w.getText('body','Loading...Please Wait', 'center')))
    
    #Activate initial screen 'choose_logs'
    views.activate('choose_logs',BODY)

    #Initialize Loop object
    loop = urwid.MainLoop(frame, s.df.palette, unhandled_input=s.unhandled_input)

    #Run Forest Run.
    loop.run()
    debug("\n****\nApplication Ended Normally!\n****\n")